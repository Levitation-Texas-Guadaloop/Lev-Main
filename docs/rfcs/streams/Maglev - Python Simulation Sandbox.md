# Maglev - Python Simulation Sandbox

*Support doc for [[Levitation Research Claude]] — a staged OSS Python digital-twin plan for building maglev control intuition, from single-actuator to full MIMO pod with swappable controllers.*

---

## Philosophy

The sim is a **layered sandbox**, not a monolithic script. Each layer is independently runnable and testable; each adds fidelity. You build intuition at each layer before adding the next.

The architecture mirrors the real system: the same controller code you tune in simulation will transfer to hardware with minimal changes (replace the plant ODE with hardware I/O).

---

## Stack

All open-source, pip-installable:

| Library | Role |
|---|---|
| `numpy` / `scipy` | Numerics, ODE integration (`solve_ivp`) |
| `python-control` | Transfer functions, Bode plots, LQR design, pole placement |
| `matplotlib` / `plotly` | Static and interactive plots |
| `casadi` | Symbolic math + NLP solver for MPC (IPOPT backend) |
| `sympy` | Symbolic derivation of linearized models |
| `pandas` | Log data, parameter sweeps |
| `dash` (Plotly) | Browser-based real-time dashboard |
| `gymnasium` (optional) | RL environment wrapper for learning layer |

Install:
```bash
pip install numpy scipy matplotlib plotly python-control casadi sympy pandas dash
```

---

## Layer 1 — Single-Actuator Nonlinear Simulation

**Goal:** understand the open-loop instability, verify your force model, tune a simple current-loop.

### Plant Model

```python
import numpy as np
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt

# Physical parameters — from Diagram_1.png, single 1"-deep core
MU0 = 4 * np.pi * 1e-7
A = 6.45e-4     # pole face area [m²]  (1 in²)
N = 250         # turns (loop total)
m = 69.0        # supported mass per core [kg]  (F0 = m*g ≈ 680 N; scale by #cores)
g = 9.81        # gravity [m/s²]
R = 2.0         # coil resistance [Ω]

# Series (non-gap) reluctance — the PM dominates, do NOT neglect it.
# PM is magnetically ~an air gap of its own length (mu_rec ≈ 1.05).
MU_REC = 1.05           # NdFeB recoil permeability
L_PM   = 2 * 0.0254     # total PM length in loop [m] (1" per leg × 2 legs)
MU_R   = 800            # 1018 steel relative permeability (unsaturated)
L_IRON = 0.15           # mean steel path length [m]
R_PM    = L_PM   / (MU0 * MU_REC * A)
R_STEEL = L_IRON / (MU0 * MU_R   * A)
R0      = R_PM + R_STEEL          # x-independent series reluctance (≈ R_PM)

# PM as a Thévenin MMF source (loadline), NOT a fixed flux offset
BR     = 1.3                      # NdFeB N42 remanence [T]
HC     = BR / (MU0 * MU_REC)      # normal-curve coercivity [A/m]
MMF_PM = HC * L_PM                # PM magnetomotive force [A]

def reluctance(x):
    return 2 * x / (MU0 * A) + R0       # two gaps + series (PM + steel)

def phi_bias(x):
    return MMF_PM / reluctance(x)       # PM-only flux at gap x (coil off)

def force(i, x):
    """Attractive force [N] (positive = toward rail, closing the gap)."""
    phi = (N * i + MMF_PM) / reluctance(x)   # total flux through full reluctance
    return phi**2 / (MU0 * A)                # two-gap Maxwell stress force

def plant_ode(t, state, v_coil, x_d_fn):
    """
    state = [x, xdot, i]
    x     = air gap [m] (positive = gap open)
    xdot  = gap rate [m/s]
    i     = coil current [A]
    v_coil = applied coil voltage [V] (control input)
    """
    x, xdot, i = state
    x = max(x, 1e-4)   # prevent singularity at x=0

    F = force(i, x)
    L = N**2 / reluctance(x)       # gap-dependent inductance (full reluctance)

    # Equations of motion — x is the GAP (positive = open), so gravity OPENS the
    # gap and the (attractive) magnet CLOSES it:  m*xddot = m*g - F.
    # (This sign is what makes the plant unstable; F-m*g would be a stable oscillator.)
    xddot = (m * g - F) / m
    # NOTE: omits motional back-EMF (i*dL/dx*xdot and the PM-flux term). These are
    # inner-current-loop disturbances; add them for high-fidelity electrical studies.
    idot = (v_coil - R * i) / L     # coil: V = Ri + L di/dt

    return [xdot, xddot, idot]
```

### Open-Loop Test

```python
# Initial condition: pod at gap x0. With the PM sized to hold mg at x0,
# the equilibrium coil current is ~0 (zero-power point) — perturb the GAP, not i.
x0 = 3e-3       # 3 mm gap
i_eq = 0.0      # solve force(i_eq, x0) = m*g → ≈0 here (PM carries the weight)

state0 = [x0 * 1.01, 0.0, i_eq]   # 1% gap perturbation kicks off the divergence
t_span = (0, 0.5)

def v_const(t):
    return i_eq * R   # constant voltage → constant current (no feedback)

sol = solve_ivp(
    lambda t, s: plant_ode(t, s, v_const(t), None),
    t_span, state0,
    max_step=1e-4, dense_output=True
)

plt.figure(figsize=(10, 4))
plt.subplot(1,2,1); plt.plot(sol.t, sol.y[0]*1000); plt.xlabel('t [s]'); plt.ylabel('gap [mm]')
plt.title('Open-loop gap (diverges → crash)')
plt.subplot(1,2,2); plt.plot(sol.t, sol.y[2]); plt.xlabel('t [s]'); plt.ylabel('current [A]')
plt.tight_layout(); plt.show()
```

You will observe the gap diverging — one side crashes to zero, the other opens. This confirms the unstable RHP pole.

---

## Layer 2 — Inner Current Loop

**Goal:** verify the PI current loop closes cleanly; measure achievable bandwidth.

```python
class PICurrentLoop:
    """Discrete-time PI current controller."""
    def __init__(self, Kp, Ki, dt, i_max=5.0, v_max=24.0):
        self.Kp = Kp
        self.Ki = Ki
        self.dt = dt
        self.i_max = i_max
        self.v_max = v_max
        self.integrator = 0.0

    def update(self, i_ref, i_meas):
        e = np.clip(i_ref, -self.i_max, self.i_max) - i_meas
        self.integrator += e * self.dt
        v = self.Kp * e + self.Ki * self.integrator
        v = np.clip(v, -self.v_max, self.v_max)
        return v
```

Sweep Kp, Ki and plot step responses of current. Measure the −3 dB bandwidth from a frequency sweep. This is your current loop bandwidth — it must exceed 5–10× your mechanical unstable pole.

---

## Layer 3 — SISO Stabilizer (Outer Gap Loop)

**Goal:** stabilize a single actuator with the nested loop; see the design tradeoffs.

```python
import control

# Linearized plant (inner current loop makes i ≈ i_ref, so outer sees F = k_i * i_ref)
# Plant: dZ(s)/I_ref(s) = k_i / (m*s^2 - k_s)
#
# COORDINATE: this linear plant is in up-displacement dz = -(x_gap - s0), NOT the raw
# gap. That is why k_i enters with a + sign here (see PM Bias doc §5). The nonlinear
# sim above integrates the GAP, so when you wrap this controller around it you MUST
# apply the sign flip at the boundary:  dz = s0 - x_gap  on the measurement side.
# Skip it and the feedback polarity inverts -> you command the instability.

# Full-reluctance stiffnesses (see PM Bias doc §4b). Both are scaled by the
# gap-reluctance fraction eta = R_gap/R_total relative to the ideal single-gap forms.
def compute_stiffnesses(s0):
    Rtot = reluctance(s0)
    phi0 = phi_bias(s0)                              # coil-off bias flux at s0
    k_i = 2 * phi0 * N / (MU0 * A * Rtot)            # ≈ 6.8 N/A
    k_s = 4 * phi0**2 / ((MU0 * A)**2 * Rtot)        # magnitude, destabilizing ≈ 5.0e4 N/m
    return k_i, k_s

s0 = 3e-3
k_i, k_s = compute_stiffnesses(s0)

s = control.tf('s')
P = k_i / (m * s**2 - k_s)

# Design: PD + integrator (PID)
Kp, Kd, Ki_pos = 500, 50, 200
C = Kp + Ki_pos/s + Kd*s / (0.001*s + 1)   # filtered derivative

L = C * P   # loop gain

# Check stability
control.bode(L, dB=True, Hz=True)
gm, pm, wcg, wcp = control.margin(L)
print(f"Gain margin: {gm:.1f} dB, Phase margin: {pm:.1f}°")
print(f"Gain crossover: {wcg/(2*np.pi):.1f} Hz, Phase crossover: {wcp/(2*np.pi):.1f} Hz")
```

Then run a closed-loop nonlinear sim with the PID controller and current loop together. Watch stability margins translate to actual transient behavior.

---

## Layer 4 — LQR State-Feedback Stabilizer

**Goal:** design the MIMO-ready LQR and verify it on the single-axis linearized model.

```python
import control

# State: [dz, dzdot] in up-displacement (dz = -(x_gap - s0)), input: i_ref.
# k_s/m and k_i/m both enter positive in this coordinate (see Layer 3 note / PM Bias §5).
# The +k_s/m entry is the RHP pole; the LQR is what moves it into the LHP.
A_mat = np.array([[0, 1], [k_s/m, 0]])
B_mat = np.array([[0], [k_i/m]])
C_mat = np.eye(2)

# LQR weights
Q = np.diag([1e6, 1e2])   # penalize gap error heavily, velocity lightly
R_lqr = np.array([[1.0]])  # penalize current effort

K_lqr, S, E = control.lqr(A_mat, B_mat, Q, R_lqr)
print("LQR gains:", K_lqr)
print("Closed-loop poles:", E)
```

The LQR eigenvalues should all have negative real parts. Then run the nonlinear sim with the LQR controller (gains applied to estimated state from Luenberger/EKF observer).

---

## Layer 5 — 4-Corner Rigid Body (Full MIMO)

**Goal:** model the full pod with z/pitch/roll, add the B matrix and pseudo-inverse allocator.

```python
# State: [z, theta_pitch, phi_roll, zdot, thetadot, phidot]
# Plus 4 currents → total 10-state system (or 6-state + 4 currents separately)

# Geometry
lx = 0.1   # half-width [m]
ly = 0.15  # half-length [m]
Iz = 0.01  # pitch moment of inertia [kg·m²]
Ix = 0.005 # roll moment of inertia [kg·m²]

# B matrix: 3 generalized forces → 4 coil forces
# Arrangement: corners [FL, FR, RL, RR]
B = np.array([
    [ 1,   1,   1,   1 ],   # heave: sum
    [ lx, -lx,  lx, -lx],   # roll moment
    [ ly,  ly, -ly, -ly],   # pitch moment
])
# Pseudo-inverse allocator
B_pinv = np.linalg.pinv(B)   # 4×3 matrix

def allocate(u_gen):
    """Map 3 generalized force commands to 4 coil force commands."""
    f_coils = B_pinv @ u_gen
    return np.clip(f_coils, 0, F_MAX)   # force is always attractive
```

The 6-DOF (or 3-DOF mechanical) state-space model is built similarly to Layer 4 but with the full A, B matrices in modal coordinates.

---

## Layer 6 — EKF Observer

**Goal:** add realistic sensor noise and estimate velocity from noisy gap measurements.

```python
class EKF:
    """Extended Kalman Filter for single-axis maglev."""
    def __init__(self, Q_noise, R_noise, x0, P0):
        self.x = x0.copy()   # [gap, gap_rate, current]
        self.P = P0.copy()
        self.Q = Q_noise      # process noise covariance
        self.R = R_noise      # measurement noise covariance

    def predict(self, f_dynamics, dt):
        # Integrate state (Euler or RK4)
        self.x = self.x + f_dynamics(self.x) * dt
        # Jacobian F_jac = df/dx evaluated at current x
        F_jac = self._jacobian(self.x, dt)
        self.P = F_jac @ self.P @ F_jac.T + self.Q

    def update(self, z_meas):
        # Measurement: gap only (H = [1, 0, 0])
        H = np.array([[1, 0, 0]])
        y = z_meas - H @ self.x
        S = H @ self.P @ H.T + self.R
        K = self.P @ H.T @ np.linalg.inv(S)
        self.x = self.x + K @ y
        self.P = (np.eye(3) - K @ H) @ self.P
        return self.x

    def _jacobian(self, x, dt):
        # Numerical Jacobian (replace with analytical for speed)
        eps = 1e-6
        n = len(x)
        J = np.zeros((n, n))
        f0 = self._f(x)
        for i in range(n):
            xp = x.copy(); xp[i] += eps
            J[:, i] = (self._f(xp) - f0) / eps
        return np.eye(n) + J * dt

    def _f(self, x):
        gap, gdot, i = x
        gap = max(gap, 1e-4)
        F = force(i, gap)
        L = N**2 / reluctance(gap)   # full-reluctance inductance
        xddot = (m * g - F) / m      # gap coord: gravity opens, magnet closes (unstable)
        idot = (0 - R * i) / L   # assumes v_coil known; pass as param in real impl
        return np.array([gdot, xddot, idot])
```

Add Gaussian noise to gap measurements in the sim and verify the EKF tracks the true state. Plot true vs. estimated velocity to see the filtering effect.

---

## Layer 7 — Dashboard for Real-Time Visualization

**Goal:** interactive Plotly Dash app that shows the sim state in real time, lets you change gains, and plots Bode/root-locus alongside the time response.

```python
from dash import Dash, dcc, html, Input, Output
import plotly.graph_objects as go

app = Dash(__name__)
app.layout = html.Div([
    html.H2("Maglev Control Sandbox"),
    dcc.Slider(id='Kp-slider', min=0, max=2000, step=50, value=500),
    dcc.Graph(id='gap-plot'),
    dcc.Graph(id='bode-plot'),
    dcc.Interval(id='interval', interval=100)
])

@app.callback(Output('gap-plot', 'figure'), Input('Kp-slider', 'value'), ...)
def update_gap_plot(Kp):
    # Run sim with new Kp, return figure
    ...

if __name__ == '__main__':
    app.run(debug=True)
```

This gives you an interactive browser-based interface: slide gains and watch stability/performance change in real time.

---

## Layer 8 — MPC (Optional, Once Stable)

**Goal:** replace the LQR with a CasADi-based NMPC for constraint handling.

```python
import casadi as ca

# Decision variables
N_horizon = 20
dt = 1e-3

opti = ca.Opti()
X = opti.variable(2, N_horizon + 1)   # [gap, gap_rate]
I_ref = opti.variable(1, N_horizon)    # current reference

# Dynamics constraints
for k in range(N_horizon):
    x_next = X[:, k] + dt * ca.vertcat(
        X[1, k],
        k_s/m * X[0, k] + k_i/m * I_ref[0, k]
    )
    opti.subject_to(X[:, k+1] == x_next)

# Cost
Q_mpc = ca.diag([1e4, 1e2])
R_mpc = 1.0
cost = 0
for k in range(N_horizon):
    cost += ca.mtimes([(X[:, k] - x_ref).T, Q_mpc, (X[:, k] - x_ref)])
    cost += R_mpc * I_ref[0, k]**2
opti.minimize(cost)

# Constraints
opti.subject_to(opti.bounded(1e-3, X[0, :], 10e-3))   # gap limits
opti.subject_to(opti.bounded(-5, I_ref, 5))             # current limits

opti.solver('ipopt', {'ipopt.print_level': 0, 'print_time': 0})

def mpc_step(x_current, x_target):
    x_ref = ca.vertcat(x_target, 0)
    opti.set_initial(X, ca.repmat(x_ref, 1, N_horizon+1))
    opti.set_value(opti.parameter(), x_current)
    sol = opti.solve()
    return float(sol.value(I_ref[0, 0]))   # return first optimal current
```

---

## Folder Structure

```
maglev_sim/
├── plant/
│   ├── single_actuator.py    # Layers 1-2
│   └── four_corner.py        # Layer 5 (MIMO)
├── controllers/
│   ├── pid.py
│   ├── lqr.py
│   ├── adrc.py
│   └── mpc.py
├── observers/
│   └── ekf.py                # Layer 6
├── utils/
│   ├── bode_tools.py
│   └── allocation.py         # B matrix, pseudo-inverse
├── dashboard/
│   └── app.py                # Layer 7 (Dash)
├── experiments/
│   └── gain_sweep.py         # Parameter studies
└── notebooks/
    └── tutorial.ipynb        # Step-by-step walkthrough
```

---

## Recommended Build Order

1. **Layer 1:** Open-loop crash — verify your force model parameters match observed behavior.
2. **Layer 2:** Current loop — verify bandwidth, tune PI gains.
3. **Layer 3:** PID outer loop — verify stabilization, get a feel for gain margins.
4. **Layer 4:** LQR — compare with PID; see improved transient behavior.
5. **Layer 6:** Add EKF — add sensor noise and see why velocity estimation matters.
6. **Layer 5:** 4-corner MIMO — extend everything to the full pod.
7. **Layer 7:** Dashboard — make it interactive.
8. **Layer 8:** MPC — once everything else works.

Each layer should take 1–2 sessions to build and validate. The total sim accurately represents your hardware and serves as the test bed for all controller designs before deployment.

---

*See also:*
- *[[Maglev - PM Bias and Force Linearization]] — the force model this sim uses*
- *[[Maglev - Coupling and Geometry]] — the B matrix and 4→3 allocation in Layer 5*
- *[[Maglev - Control Theory Fundamentals]] — theory behind LQR, backstepping, and nested loop*
- *[[Maglev - Hardware and Implementation]] — the hardware this sim targets*

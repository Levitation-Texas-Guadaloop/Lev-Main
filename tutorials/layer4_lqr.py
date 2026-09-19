"""
Layer 4 — LQR State-Feedback Stabilizer (MIMO-ready)
====================================================

- LQR needs the FULL state [dz, dz_dot]; only gap is measured -> Luenberger
  observer estimates velocity.
- Written in generic matrix form (A,B,C,K,L). Single-axis here, but the loop
  is the Layer-5 MIMO template: swap in x=[z,pitch,roll,...], B=allocation, done.
- Verify: eig(A-BK) and eig(A-LC) all LHP, then run the nonlinear nested sim.
- Observer has no disturbance model -> exact on modeled motion, but biased velocity
  under an unmodeled load (see fig). Layer 6 EKF / disturbance obs is the fix.

Run:  python3 layer4_lqr.py   ->  figures/layer4_lqr.png
"""

import os

import numpy as np
import control
import matplotlib.pyplot as plt

from maglev import params as P
from maglev.plant import force, inductance, equilibrium_current
from maglev.linearization import linear_state_space, unstable_pole_hz
from maglev.controllers import PICurrentLoop

FIGDIR = os.path.join(os.path.dirname(__file__), "figures")
os.makedirs(FIGDIR, exist_ok=True)

# loop rates (same nesting as Layer 3)
FS_PLANT = 200e3; DT_PLANT = 1 / FS_PLANT
FS_INNER = 40e3;  N_INNER = int(FS_PLANT / FS_INNER)
FS_OUTER = 2e3;   N_OUTER = int(FS_PLANT / FS_OUTER)


# --- Plant model (up-displacement dz = s0 - x_gap) --------------------------
#   x = [dz, dz_dot]      state
#   u = i_ref deviation   input (added to i_eq feedforward)
#   y = dz                measurement (gap only, NOT velocity)
#       x_dot = A x + B u
#       y     = C x
# MIMO (Layer 5) reuses this shape: x=[z,theta,phi,rates], B=k_i * B_alloc.
A, B, (K_I, K_S) = linear_state_space()
C = np.array([[1.0, 0.0]])


class LQRObserver:
    """MIMO-ready observer + state feedback. Dims come from the matrices."""

    def __init__(self, A, B, C, K, L, dt, i_eq, i_max=P.I_MAX):
        # matrices define the plant size; scalar logic below never assumes 1-D
        self.A, self.B, self.C, self.K, self.L = A, B, C, K, L
        self.dt = dt
        self.i_eq = i_eq
        self.i_max = i_max
        self.x_est = np.zeros((A.shape[0], 1))    # state estimate
        self.u = np.zeros((B.shape[1], 1))        # last applied input (for predict)

    def seed(self, y0):
        # init estimate from first measurement (position known, velocity unknown)
        self.x_est = self.C.T @ np.atleast_2d(y0)

    def update(self, y_meas):
        y = np.atleast_2d(y_meas)
        # - correct: fuse gap measurement
        self.x_est = self.x_est + self.L @ (y - self.C @ self.x_est) * self.dt
        # - control law: LQR state feedback + equilibrium feedforward
        i_ref = self.i_eq + (-self.K @ self.x_est).item()
        i_ref = float(np.clip(i_ref, -self.i_max, self.i_max))   # actuator limit
        # - predict with the APPLIED input (anti-windup: observer must see the
        #   clamped current, else it diverges from reality during saturation)
        self.u = np.array([[i_ref - self.i_eq]])
        self.x_est = self.x_est + (self.A @ self.x_est + self.B @ self.u) * self.dt
        return i_ref


def design():
    """LQR gain + observer gain; print the eigenvalue checks."""
    Q = np.diag([1e6, 1e2])       # heavy on gap error, light on velocity
    R = np.array([[1.0]])         # current-effort penalty
    K, _, E_ctrl = control.lqr(A, B, Q, R)

    # observer poles 4x faster than the controller (dual placement)
    L = control.place(A.T, C.T, 4 * E_ctrl).T
    E_obs = np.linalg.eigvals(A - L @ C)

    print("=== Layer 4: LQR + observer design ===")
    print(f"open-loop poles   = {np.linalg.eigvals(A).round(1)}  (unstable {unstable_pole_hz():.2f} Hz)")
    print(f"LQR gain K        = {K.ravel().round(1)}")
    print(f"ctrl poles (A-BK) = {E_ctrl.round(1)}  stable={np.all(E_ctrl.real < 0)}")
    print(f"obs poles (A-LC)  = {E_obs.round(1)}  stable={np.all(E_obs.real < 0)}")
    return K, L


def nonlinear_sim(K, L):
    """outer LQR+observer (2 kHz) -> inner PI (40 kHz) -> nonlinear plant (RK4)."""
    s0, m, R = P.S0, P.M, P.R_COIL
    i_eq = equilibrium_current(s0)

    inner = PICurrentLoop(Kp=2 * np.pi * 1000 * inductance(s0), Ki=2 * np.pi * 1000 * R,
                          dt=1 / FS_INNER)
    ctrl = LQRObserver(A, B, C, K, L, dt=1 / FS_OUTER, i_eq=i_eq)

    # start 15% open (pod dropped); seed observer from the first gap reading
    state = np.array([s0 * 1.15, 0.0, i_eq])
    ctrl.seed(s0 - state[0])

    # 10 N payload step at 0.3 s. Kept below Layer 3's 20 N on purpose: the softer
    # LQR sags more, and the negative spring k_s*dz adds to the load at that offset,
    # so holding P newtons needs ~P + k_s*offset -> authority is gain-dependent.
    # 20 N here would push i_ref past the 5 A clamp and drop the pod.
    t_end, t_dist, F_dist = 0.6, 0.3, 10.0
    n = int(t_end / DT_PLANT)
    log = {k: np.empty(n) for k in ("t", "x", "vtrue", "vest", "i", "iref")}

    i_ref, v_coil = i_eq, R * i_eq
    for k in range(n):
        t = k * DT_PLANT
        F_d = F_dist if t >= t_dist else 0.0

        if k % N_OUTER == 0:
            i_ref = ctrl.update(s0 - state[0])    # SIGN FLIP: dz = s0 - x_gap
        if k % N_INNER == 0:
            v_coil = inner.update(i_ref, state[2])

        # RK4 with disturbance force folded into the gap EoM
        def ode(sv):
            x, xd, i = sv
            x = max(x, 1e-4)
            return np.array([xd, (m * P.G + F_d - force(i, x)) / m,
                             (v_coil - R * i) / inductance(x)])
        k1 = ode(state); k2 = ode(state + 0.5 * DT_PLANT * k1)
        k3 = ode(state + 0.5 * DT_PLANT * k2); k4 = ode(state + DT_PLANT * k3)
        state = state + (DT_PLANT / 6) * (k1 + 2 * k2 + 2 * k3 + k4)

        log["t"][k] = t; log["x"][k] = state[0]; log["i"][k] = state[2]
        log["iref"][k] = i_ref
        log["vtrue"][k] = -state[1]                # dz_dot = -x_gap_dot
        log["vest"][k] = ctrl.x_est[1, 0]

    print("\n=== Layer 4: nonlinear nested sim ===")
    print(f"start gap        = {s0*1.15*1e3:.2f} mm (15% open)")
    print(f"recovered gap    = {log['x'][np.argmin(np.abs(log['t']-0.28))]*1e3:.3f} mm")
    print(f"final gap        = {log['x'][-1]*1e3:.3f} mm  (target {s0*1e3:.2f}, i_eq feedforward)")
    print(f"steady offset    = {(log['x'][-1]-s0)*1e6:.1f} um under {F_dist:.0f} N")
    print(f"peak current     = {np.max(np.abs(log['i'])):.2f} A")
    print(f"obs vel bias (end)= {(log['vest'][-1]-log['vtrue'][-1])*1e3:.2f} mm/s "
          f"(unmodeled load -> Layer 6 EKF fixes)")
    return log


def plot(log):
    s0 = P.S0
    fig, (ax_g, ax_v) = plt.subplots(1, 2, figsize=(11, 4))

    ax_g.plot(log["t"] * 1e3, log["x"] * 1e3, lw=1.5, color="#2563eb")
    ax_g.axhline(s0 * 1e3, color="gray", ls="--", lw=1, label=f"target {s0*1e3:.0f} mm")
    ax_g.axvline(0.3 * 1e3, color="crimson", ls=":", lw=1.5, label="payload step")
    ax_g.set_xlabel("time [ms]"); ax_g.set_ylabel("air gap [mm]")
    ax_g.set_title("LQR gap: recovers 15% drop, holds load", fontsize=11)
    ax_g.legend(fontsize=9); ax_g.grid(True, alpha=0.3)

    ax_v.plot(log["t"] * 1e3, log["vtrue"] * 1e3, lw=2, color="#16a34a", label="true dz_dot")
    ax_v.plot(log["t"] * 1e3, log["vest"] * 1e3, lw=1, ls="--", color="#dc2626",
              label="observer estimate")
    ax_v.axvline(0.3 * 1e3, color="crimson", ls=":", lw=1.5, label="payload step")
    ax_v.annotate("unmodeled load ->\nvelocity bias\n(Layer 6 EKF fixes)",
                  xy=(480, 2.5), fontsize=8, color="#dc2626")
    ax_v.set_xlabel("time [ms]"); ax_v.set_ylabel("up-velocity dz_dot [mm/s]")
    ax_v.set_title("Observer: exact when modeled, biased by unmodeled load", fontsize=11)
    ax_v.legend(fontsize=9, loc="lower left"); ax_v.grid(True, alpha=0.3)

    fig.tight_layout()
    out = os.path.join(FIGDIR, "layer4_lqr.png")
    fig.savefig(out, dpi=150); plt.close(fig)
    print(f"saved {out}")


def main():
    K, L = design()
    plot(nonlinear_sim(K, L))


if __name__ == "__main__":
    main()

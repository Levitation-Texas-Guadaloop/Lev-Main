# Maglev - LQR and State Feedback

*Support doc for [[Levitation Research Claude]] — deeper loop on **how LQR actually works** via a toy model (inverted pendulum), and **how LQR tuning differs from PID**. Companion to [[Maglev - Control Theory Fundamentals]] (loop shaping / Lyapunov / backstepping) and [[Maglev - Control Allocation and MIMO]] (where LQR lands in the architecture: Layer 2, modal MIMO stabilizer). Sim realization = **Layer 4** in [[Maglev - Python Simulation Sandbox]].*

---

## 1. LQR in One Paragraph

- **Full-state feedback** law `u = −Kx`. You feed *every* state back, not just the error signal.
- You don't pick `K` directly. You pick a **cost** you want minimized; LQR solves for the `K` that minimizes it.
- Cost is quadratic: `J = ∫₀^∞ (xᵀQx + uᵀRu) dt`.
  - `Q ⪰ 0` — penalty on state deviation (how much you *care* about each state being off-target).
  - `R ≻ 0` — penalty on control effort (how much actuation "costs" — current, voltage, heat).
- Optimal gain: `K = R⁻¹BᵀP`, where `P` solves the **Continuous Algebraic Riccati Equation (CARE)**:
  `AᵀP + PA − PBR⁻¹BᵀP + Q = 0`.
- Guarantees, *if `(A,B)` controllable and `(A,√Q)` observable*:
  - Closed loop `A − BK` is **Hurwitz** (stable) — even for an open-loop RHP plant like ours.
  - Classical robustness: **≥ 6 dB gain margin, ≥ 60° phase margin** per input (SISO LQR). Free, by construction.

---

## 2. Why State Feedback At All (vs. output/error feedback)

- PID sees **one scalar**: the tracking error `e = r − y`. It reconstructs "velocity" via the D-term (noisy) and "accumulated error" via the I-term.
- LQR sees the **whole state vector** `x` and weights each component knowingly. For a plant with hidden fast modes or coupling, that's the difference between reacting to a symptom and directly damping the mode.
- Caveat: you must *have* the state. Not measured → estimate it (Luenberger observer / Kalman → **LQG**). For us: gap + current measured, velocity + flux estimated. See [[Maglev - Sensing and Flux Feedback]].

---

## 3. Toy Model — Inverted Pendulum (the RHP-pole cousin of our plant)

Chosen deliberately: the inverted pendulum has an **unstable (RHP) pole**, exactly like the maglev heave plant. Same disease, simpler anatomy.

### 3a. Model (pendulum on a cart, linearized upright)

- States: `x = [p, ṗ, θ, θ̇]ᵀ` — cart position, cart velocity, pole angle from vertical, angular rate.
- Input: `u` = horizontal force on cart.
- Linearize about upright (`θ=0`). With cart mass `M`, pole mass `m`, length `l`, gravity `g`:

```
      ⎡0   1        0        0⎤        ⎡  0    ⎤
A  =  ⎢0   0     −mg/M      0 ⎥  B =   ⎢ 1/M   ⎥
      ⎢0   0        0        1⎥        ⎢  0    ⎥
      ⎣0   0   (M+m)g/(Ml)   0⎦        ⎣−1/(Ml)⎦
```

- The `(M+m)g/(Ml)` term in row 4 is the **positive (destabilizing) coefficient** — this is the RHP pole. Directly analogous to `k_s/m` in our plant.

### 3b. Even simpler — the 2-state "bare pendulum" = our maglev heave plant

Strip the cart; torque-driven pole (or equivalently our single-actuator heave):

- `x = [δz, δż]ᵀ`, `ẋ = Ax + Bu` with
  `A = [[0, 1], [k_s/m, 0]]`, `B = [0, k_i/m]ᵀ`.
- Open-loop eigenvalues: `±√(k_s/m)` → the RHP one is `+4.3 Hz` (our number, see [[Maglev - PM Bias and Force Linearization]] §4b and the `x_eq` equivalent-gap form).
- This IS the maglev plant. The inverted pendulum is not an analogy here — it's the same 2×2 structure. Whatever LQR does to the pendulum, it does to the pod's heave mode.

### 3c. What LQR does to it (mechanics, step by step)

1. Pick `Q = diag(q_z, q_ż)`, `R = [r]`. Say `q_z` large (care about position), `q_ż` modest, `r` small (cheap actuation).
2. Solve CARE `AᵀP + PA − PBR⁻¹BᵀP + Q = 0` for symmetric `P ≻ 0`. (2×2 → solvable by hand; in general `scipy.linalg.solve_continuous_are` / `control.lqr`.)
3. `K = R⁻¹BᵀP = [k₁, k₂]`. Physically: `k₁` = position stiffness, `k₂` = velocity damping the controller *synthesizes*.
4. Closed loop: `ẋ = (A − BK)x`. Eigenvalues now **both LHP** — the RHP pole has been pulled into the left half plane. Pod hovers.
5. Turn `r` down → gains rise → poles pushed further left → faster, stiffer, more current. Turn `r` up → gentler, less effort, poles closer to imaginary axis. **That single ratio is the whole tuning experience** (see §4).

### 3d. Minimal numeric demo (one actual run — sim has never been executed)

```python
import numpy as np, control as ct
ks, ki, m = 2*9.81*0.11/0.003, ..., 69.0   # pull real k_s,k_i from char doc / PM-Bias
A = np.array([[0,1],[ks/m,0]])
B = np.array([[0],[ki/m]])
Q = np.diag([100.0, 1.0]); R = np.array([[1.0]])
K, P, E = ct.lqr(A, B, Q, R)      # E = closed-loop eigenvalues (should be LHP)
print(K, E)
```

- Good candidate for the **first real run of Sim Layer 1+4** — see [[Maglev - Python Simulation Sandbox]]. Confirms the RHP eigenvalue flips sign, gives concrete `[k₁, k₂]` to sanity-check against hand-tuned PID.
- **Caveat that matters:** `K` is a direct function of `k_s, k_i, m`. Those are exactly the parameters still provisional pending real `L(x)` data (see [[Maglev Actuator Characterization]] and the empirical-inductance inconsistency). **Garbage params → garbage gains.** LQR does not rescue a wrong plant model; it optimizes *for* the model you hand it.

---

## 4. LQR Tuning vs. PID Tuning — The Real Difference

The headline: **PID, you tune the gains directly. LQR, you tune what you care about and it computes the gains.** The knob moves up an abstraction level.

| | **PID** | **LQR** |
|---|---|---|
| What you set | `Kp, Ki, Kd` (the gains themselves) | `Q, R` (penalties on state error vs. effort) |
| What that means | "How hard do I react to error, its integral, its rate" | "How much do I care about each state deviation vs. how much does actuation cost" |
| Who computes gains | You (by hand / Ziegler–Nichols / trial) | The Riccati solver, optimally |
| Model needed? | No (can tune on hardware blind) | **Yes** — needs `A, B` (hence the char doc matters) |
| SISO vs MIMO | One loop per output; **coupling handled ad hoc** | **Native MIMO** — one `K` coordinates all inputs/outputs at once |
| Uses which signals | Error `e` only (+ its I and D) | **Full state** `x` (measured or estimated) |
| Stability guarantee | None a priori; you verify margins after | `A−BK` **provably** stable + built-in ≥6 dB/≥60° margins |
| Failure mode of tuning | Chase 3 numbers, they interact, easy to get lost | Pick 2 matrices; intuitive but Q/R still needs iteration |

### 4a. The conceptual shift

- **PID is behavioral.** You describe the *reaction*: proportional push, integral memory, derivative anticipation. You're sculpting the controller directly.
- **LQR is declarative.** You describe the *objective*: "keep `δz` tight, don't burn current." The optimal reaction is *derived*. You never say "add more damping" — you say "care more about velocity" (raise `q_ż`) and damping appears.

### 4b. The Q/R knob, concretely

- Only the **ratio** `Q/R` matters (scaling both by the same factor leaves `K` unchanged).
- **Raise Q (or lower R):** tighter regulation, faster poles, higher gains, more actuator effort/current/heat.
- **Lower Q (or raise R):** gentler, less effort, poles migrate toward the imaginary axis (slower, softer).
- Off-diagonal / relative `Q` entries let you say "I care about pitch 10× more than heave" — one line. In PID that's re-tuning separate loops and praying they don't fight.
- **Bryson's rule** as a starting point: `Q_ii = 1/(max acceptable x_i)²`, `R_jj = 1/(max acceptable u_j)²`. Turns physical tolerances directly into weights. Then iterate.

### 4c. Where each wins for *this* project

- **PID / lead:** fine for a **single** stabilized SISO loop; no model needed to start; what the current Arduino rig attempts. Breaks down at 4 coupled corners (see [[Maglev - Coupling and Geometry]]).
- **LQR:** the **whole reason** the architecture is centralized-MIMO. It stabilizes the 4→3 coupled corner set on modal coordinates (`z, θ, φ`) with one coordinated `K`, and the coupling is handled *by construction*, not patched. This is Layer 2 in [[Maglev - Control Allocation and MIMO]] (§8, `M q̈ = K_s q + u`).
- Note: **LQR still can't cheat the RHP pole.** Closed-loop bandwidth is still floored by `√(k_s/m)` ≈ 4.3 Hz — same hard lower bound loop-shaping gave in [[Maglev - Control Theory Fundamentals]] §1. LQR *chooses gains well*; it doesn't repeal the plant physics.

---

## 5. Practical Extensions (flag now, build later)

- **Integral action → LQI.** Bare LQR is a *regulator* (drives state → 0); it has no integrator, so a constant disturbance (gravity offset, PM drift) leaves steady-state error. Augment state with `∫(z − z_ref)` and run LQR on the augmented system → zero steady-state offset. This is the LQR analogue of PID's I-term.
- **Discrete LQR (`dlqr`).** Real controller runs at ~1 kHz. Design on the discretized `(A_d, B_d)` via `control.dlqr` / `scipy` — don't hand a continuous `K` to a sampled loop and hope.
- **LQG.** LQR assumes full state known. Pair with a Kalman filter to estimate `δż` and flux from gap+current measurements → LQG. **Warning:** LQG loses LQR's guaranteed margins (Doyle's "*Guaranteed Margins for LQG Regulators*" — none). Recover with loop-transfer recovery (LTR) or just verify margins numerically.
- **Then:** ADRC / SMC for robustness to the still-uncertain `η`, `k_s`; MPC as an outer learning layer once stable hover exists. Ordering per [[Levitation Research Claude]].

---

*See also:*
- *[[Maglev - Control Theory Fundamentals]] — loop shaping (the RHP-pole bandwidth floor LQR also obeys), Lyapunov, backstepping, nested loops*
- *[[Maglev - Control Allocation and MIMO]] — where LQR lives: Layer-2 modal stabilizer, `B⁺` allocation, §8 modal EoM*
- *[[Maglev - PM Bias and Force Linearization]] — source of `k_i, k_s` (the LQR plant's `A, B`) and the 4.3 Hz RHP pole*
- *[[Maglev Actuator Characterization]] — pins the params LQR's `K` depends on; provisional until real `L(x)` measured*
- *[[Maglev - Python Simulation Sandbox]] — Sim Layer 4 = `control.lqr()`; §3d demo is a candidate first run*
- *[[Maglev - Sensing and Flux Feedback]] — state estimation for the states LQR feeds back*

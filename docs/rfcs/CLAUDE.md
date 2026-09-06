# Maglev Research Project — Claude Code Handoff

## Project in One Sentence
Building a MIMO-stabilized, PM-biased hybrid maglev pod (4 corner electromagnets on one rigid body) and developing the control theory, simulation, and hardware foundation to do it properly.

## Current State
All foundational research and question-answering is complete. The immediate next action is **building the Python simulation sandbox** (Layer 1 of `Maglev - Python Simulation Sandbox.md`). Hardware is currently Arduino-based with PWM H-bridges; that is a known bottleneck.

## File Inventory

| File | What It Contains |
|---|---|
| `Levitation Research Claude.md` | **Master doc** — full research report with inline `==questions==` linked to support docs via `[[wikilinks]]`. Read this first for full context. |
| `Maglev - PM Bias and Force Linearization.md` | First-principles derivation of F=k(i/x)², how PM bias linearizes, k_i and k_s stiffness coefficients with worked numbers. |
| `Maglev - Coupling and Geometry.md` | Why 4 separate actuators on 1 rigid body create a statically-indeterminate (4→3) coupling problem. Analysis of 1-rear + 2-front-corner yoke alternative. |
| `Maglev - Control Allocation and MIMO.md` | Deep dive on `f = B⁺u + f_null`: pseudo-inverse derivation, null-space (twist mode) uses, weighted/constrained QP allocation, saturation recovery, force→current inversion, modal SISO-vs-MIMO decoupling. Expands Coupling §2. |
| `Maglev - Control Theory Fundamentals.md` | Loop shaping for RHP-pole plants, Lyapunov stability (numerical), backstepping mechanics, and the nested-loop architecture (why inner/outer don't conflict). |
| `Maglev - LQR and State Feedback.md` | How LQR works via a toy inverted-pendulum (same 2×2 RHP structure as heave): cost `J`, CARE, `K=R⁻¹BᵀP`, closed-loop pole flip. Q/R-vs-PID-gains tuning contrast (declarative vs behavioral). LQI/dLQR/LQG extensions. §3d = candidate first sim run. |
| `Maglev - Sensing and Flux Feedback.md` | Why flux sensing adds beyond current+gap: PM thermal drift, hysteresis, saturation. Hall sensor placement guidance. |
| `Maglev - Hardware and Implementation.md` | Linear transconductance amp (Howland pump, OPA549), FPGA/MCU options under $500, Arduino limitations table. |
| `Maglev - Python Simulation Sandbox.md` | **8-layer OSS Python digital-twin plan** with code scaffolding for each layer. This is the next thing to build. |
| `Maglev - Experimental Controller Iteration.md` | Design-for-test rig + how to iterate the controller (PID/LQR/cost/ML) from logged gap+current(+Hall) data. Tuning ladder, log-derived cost, sim recalibration. Idea-level. |
| `Maglev Actuator Characterization.md` | Robust experimental methods to extract `L(x)`, `R`, `ℛ₀`, `A_eff`, eddy corner, saturation. Swept-sine impedance (primary), step/L–R, PWM ripple in-situ, λ–i loop, resonance. Why single LCR reading is insufficient; fit `ℛ(x)=2x/μ₀A+ℛ₀` → `μ_r` sign test. |

## Key Physics (Do Not Re-Derive)

- Force law: `F = -μ₀AN²i² / (4x²)` — always attractive, nonlinear
- Linearized about bias point (I_b, s₀): `δF = k_i·δi + k_s·δx`
- `k_i = μ₀AN²I_b / (2s₀²)` — positive, controllable stiffness
- `k_s = μ₀AN²I_b² / (2s₀³)` — positive value but *destabilizing* (negative spring)
- Unstable pole: `s = ±√(k_s/m)` — the RHP pole that must be stabilized
- Identity: `k_s/k_i = I_b/s₀`
- **Series-reluctance correction:** the forms above are the single-gap limit. The PM (μ_rec≈1.05) adds a large series reluctance; both stiffnesses scale by the gap-reluctance fraction `η = ℛ_gap/ℛ_total`. For the actual yoke (1" PM per leg) `η ≈ 0.11`, so `k_i→η·k_i`, `k_s→η·k_s`, and the unstable pole `√(2gη/s₀) ≈ 4.3 Hz` (not ~13 Hz). See `Maglev - PM Bias and Force Linearization.md §4b`.

## Hardware Context

- **Current setup:** Arduino + PWM H-bridges, per-corner SISO control
- **Known issues:** Arduino too slow for inner current loop + outer MIMO simultaneously; no hardware ADC-PWM sync; SISO had limited success
- **Recommended upgrade path:** Teensy 4.1 (near-term, ~$30, familiar ecosystem) → TI C2000 F28379D (production-quality, ~$45) → FPGA (Arty A7 or DE10-Nano) for current-loop offload
- **Current sensing:** add per-coil (ACS711/ACS712); **flux sensing:** add Hall (Allegro A1324) per yoke

## Architecture Decision (Settled)

Centralized MIMO, not per-corner SISO. Layered:
1. Inner current loop per coil (1–10 kHz, FPGA or fast MCU)
2. MIMO stabilizer on z/pitch/roll modal coordinates (~1 kHz, LQR → ADRC/SMC)
3. Control allocation (pseudo-inverse B⁺, 3 generalized forces → 4 coil commands)
4. Optional outer learning/MPC layer (later, after stable hover)

## Open Geometry Question
Whether to use 4-corner or 1-rear + 2-front-corner layout. The 3-actuator layout eliminates the statically-indeterminate problem (no allocation needed, B is square) but loses fault tolerance. See `Maglev - Coupling and Geometry.md §4`.

## Immediate Next Tasks (Prioritized)

1. **Build Sim Layer 1** — single-actuator nonlinear ODE, open-loop crash verification (`scipy.integrate.solve_ivp`). Code scaffold in `Maglev - Python Simulation Sandbox.md`.
2. **Build Sim Layer 2** — discrete PI current loop, verify bandwidth vs. PWM frequency.
3. **Build Sim Layer 3** — PID outer gap loop on linearized plant; use `python-control` for Bode + margin check.
4. **Build Sim Layer 4** — LQR state-feedback; `python-control.lqr()`.
5. **Hardware:** order Teensy 4.1 + ACS711 current sensors + Allegro A1324 Hall sensors.

## Conventions Used in Docs

- Gap `x` is positive when open (pod below rail)
- Force is positive upward (opposing gravity) — note this is the **−x** direction, so gap and "up" are antiparallel
- **Signed model for control:** the nonlinear EoM in the gap is `m·ẍ_g = mg − F(i,x_g)` (unstable). Controllers are designed in up-displacement `δz = −(x_g − s₀)`, giving `δZ/δI = +k_i/(ms²−k_s)`; apply the sign flip `δz = s₀ − x_g` at the sim↔controller boundary. See `Maglev - PM Bias and Force Linearization.md §5`.
- Modal coordinates: `z` = heave, `θ` = pitch, `φ` = roll
- Corner labeling: FL, FR, RL, RR (front-left, front-right, rear-left, rear-right)
- Obsidian `[[wikilinks]]` throughout — open vault in Obsidian for graph view

## Python Stack for Simulation

```
numpy, scipy, matplotlib, python-control, casadi, sympy, pandas, dash
pip install numpy scipy matplotlib plotly python-control casadi sympy pandas dash
```

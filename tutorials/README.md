# Matam Maglev — Simulation Sandbox

Staged digital twin for a PM-biased hybrid maglev core, built to develop and
validate control designs before they touch hardware. This repo implements
**Layers 1–3** of the plan in the research vault
(`Maglev - Python Simulation Sandbox.md`).

The sandbox is a single-actuator SISO plant — the `k_i / (m·s² − k_s)` building
block that later gets assembled into the full 4-corner / 3-yoke MIMO pod.

## Physics in one paragraph

Force is always-attractive two-gap Maxwell stress, `F = φ²/(μ₀A)`, with the PM
modeled as a constant-MMF (Thévenin) source in series with the working gaps.
The PM reluctance **dominates** the loop (gap ≈ 11% of total, `η ≈ 0.11`), which
scales both the current stiffness `k_i` and the destabilizing gap stiffness `k_s`
down from their naive single-gap values and puts the open-loop unstable pole at
**≈ 4.3 Hz**, not ~13 Hz. The gap coordinate `x` is positive when open, so the
equation of motion `m·ẍ = m·g − F` is genuinely unstable; controllers are
designed in up-displacement `δz = s₀ − x` with the sign flip applied only at the
sim↔controller boundary.

> Parameter values (`s₀ = 3 mm`, single 1"-deep core) are **illustrative**. The
> model *formulation* is the deliverable, not the numbers — swap them freely in
> `maglev/params.py`.

## Layout

```
maglev/                     shared core (single source of truth)
  params.py                 all physical constants
  plant.py                  reluctance / force / nonlinear ODE + RK4 step
  linearization.py          k_i, k_s, TF and state-space builders
  controllers.py            PICurrentLoop (inner), PIDPositionLoop (outer)
layer1_openloop.py          Layer 1: open-loop crash, confirms the RHP pole
layer2_current_loop.py      Layer 2: inner PI current loop, bandwidth vs. pole
layer3_siso_stabilizer.py   Layer 3: PID outer loop, Bode/margins + nested sim
layer4_lqr.py               Layer 4: LQR state feedback + observer (MIMO-ready)
bode_poles/                 prior standalone study: the RHP-pole bandwidth limit
```

## Run

```bash
pip install -r requirements.txt
python3 layer1_openloop.py        # -> figures/layer1_*.png
python3 layer2_current_loop.py    # -> figures/layer2_*.png
python3 layer3_siso_stabilizer.py # -> figures/layer3_*.png
python3 layer4_lqr.py             # -> figures/layer4_lqr.png
```

Each script is standalone, prints its key diagnostics to stdout, and writes its
figures to `figures/`.

## Build order (from the vault plan)

1. **Layer 1** — verify the open-loop instability and the force model.
2. **Layer 2** — close the inner current loop; confirm its bandwidth exceeds
   5–10× the ~4.3 Hz mechanical pole.
3. **Layer 3** — wrap the PID outer gap loop; read the stability margins off the
   Bode plot, then confirm them on the full nonlinear nested-loop sim.
4. **Layer 4** — LQR state feedback in generic matrix form (the MIMO template),
   with a Luenberger observer supplying the unmeasured velocity.

Next (not in this repo yet): Layer 5 four-corner MIMO, Layer 6 EKF.

# Maglev - Experimental Controller Iteration

*Support doc for [[Levitation Research Claude]] — how to iterate the controller on a physical rig from logged data (gap + current, later Hall). Idea-level / design-for-test, not a deep dive. Assumes a rig exists: 1, 3, or 4 actuators.*

---

## 0. Premise

- Sim gets you into the *neighborhood* of a working gain set — not to one. Expect a sim2real gap on the first flash.
- Real rig adds what the model omits: loop/compute delay, eddy-current flux lag, sensor noise, PM/thermal drift, tether/friction, geometry & magnet tolerances, PWM quantization.
- So flip the roles: **the rig is the real optimizer; the sim becomes a pre-screen + safety net, continuously recalibrated from rig data.**
- Everything below serves one goal: a tight, safe, *logged* **iterate → measure → update** loop.

---

## 1. Design-for-test — build these in on day 1

The single biggest determinant of how fast you can iterate. Cheap to add up front, painful to retrofit.

- **Logging.** Timestamped, synchronized streams of {gap, current/coil, command, setpoint, (Hall later)} at loop rate. Ring buffer + dump-on-event (dump the seconds around a crash).
- **Time sync & timing logs.** One clock; ADC↔PWM sync; log actual loop period/jitter. Jitter silently eats phase margin on an RHP-pole plant — measure it, don't assume it.
- **Internal observability.** Log controller *internals* too: integrator state, estimated velocity, allocator outputs, saturation flags — not just I/O. Most "why did it diverge" answers live here.
- **Perturbation injection.** Built-in way to inject steps / chirps / PRBS / impulses into setpoint or command. This same hook is your ID stimulus *and* your tuning stimulus.
- **Parameter hot-swap.** Change gains/weights without reflashing — ideally live over serial. **Stamp every gain set with a version and tie it to the log.** No orphan logs.
- **Mechanical safety.** Hard stops / catch / end-stop foam at min gap so a divergence embarrasses you instead of destroying the rig. Start tethered / over-damped.
- **Electrical envelope.** Soft current/voltage limits, watchdog that drops to a safe state, brownout handling. Reversible by default.
- **Start simplest.** Single actuator, **1-DOF constrained** (vertical rod / linear bearing) before a free rigid body. Kills coupling while you learn the loop; add DOFs deliberately.

---

## 2. Step 0 — Identify the real plant *before* tuning anything

Highest-value first move. Don't tune blind against a model you already know is wrong.

- **What to pin down:** real k_i, k_s, unstable pole, loop delay, R/L, sensor noise floor, saturation knee, (hysteresis/eddy lag if flux-instrumented).
- **Methods, cheap → rich:**
  - *Divergence rate* — tethered / near-a-stop bumps, watch how fast it runs away → estimates k_s/m directly.
  - *Closed-loop freq response* — once marginally stable, inject chirp/PRBS on setpoint, fit the transfer function, overlay on the model Bode. The gap between them *is* your sim2real error, quantified.
  - *Static force map* — clamp the gap, sweep current, measure force (load cell) → real k_i(x), saturation, any hysteresis width.
  - *Electrical* — voltage step, watch current rise → L/R and transport delay.
- **Output:** a calibrated model. Re-derive gains from it. **This step alone usually closes most of the gap** — before any fancy tuning.

---

## 3. The tuning / iteration ladder

Climb only as high as you need. Each rung assumes the one below works.

- **Rung 1 — structured hand tuning.** Start from model-based gains (LQR / lead-lag), nudge the classic knobs while watching logged step responses. One change → log → compare. Keep a changelog bound to log IDs. Gets you surprisingly far.
- **Rung 2 — systematic auto-tuning:**
  - *Relay / Åström–Hägglund* — find loop gain/phase at crossover automatically.
  - *Iterative Feedback Tuning (IFT)* — closed-loop experiments estimate the cost gradient wrt gains; step, repeat. Model-light.
  - *Extremum seeking* — online, model-free; dithers gains to slide down a measured cost. Good for a *few* parameters.
- **Rung 3 — optimize over an explicit cost:**
  - Define a scalar cost from logs (§4).
  - *Bayesian optimization / surrogate* — each rig run = one expensive sample; BO picks the next gain set. Ideal for a handful of parameters (PID gains, LQR Q/R diagonal, MPC weights). Sample-efficient → **the sweet spot for hardware.**
- **Rung 4 — data-driven model refresh + redesign.** Periodically re-ID from operating data (grey-box, or DMDc/Koopman for near-linear), recompute LQR/MPC. Handles drift and payload changes.
- **Rung 5 — learning layers (only *outside* a working stabilizer):**
  - RL / residual policy that *trims* a stabilizing baseline — never bootstraps stability on bare hardware.
  - Learn the **sim2real residual** (GP/NN on model error) → feed MPC (GP-MPC) or correct feedforward.
  - Safe-RL / control-barrier-function / envelope so exploration physically can't leave the safe set.

> Rule of thumb: most maglev rigs get to good hover at Rung 1–3. Rungs 4–5 are for drift, robustness, and squeezing performance — not for first light.

---

## 4. Iterating the *objective* (what "better" means)

You'll tune the cost function about as often as the controller. All computable from logs:

- **Stability proxies:** gain/phase margin from an injected chirp; sensitivity peak; divergence headroom.
- **Transient:** settling time, overshoot, RMS gap error to a step.
- **Regulation:** RMS gap under disturbance; position-noise RMS at steady hover.
- **Effort / health:** RMS & peak current, coil power/heating, control chatter (actuator activity).
- **Robustness:** spread of the above across payloads / gaps / temperatures.

Notes:
- It's inherently **multi-objective**: performance vs. effort vs. robustness. Either roll into a weighted scalar cost (and tune the weights) or sweep a Pareto front.
- For LQR this literally *is* Q/R selection; for MPC it's the stage-cost weights. So "cost tuning" and "controller tuning" are the same optimization — hand the log-derived cost straight to the Rung 2–3 optimizers.

---

## 5. The sim's role once the rig exists

Don't retire the sim — **recalibrate it**.

- Feed identified params + the learned residual back into the digital twin ([[Maglev - Python Simulation Sandbox]]).
- Uses:
  - **Pre-screen** risky gain sets / new controllers before they touch hardware.
  - **Regression test** — confirm a change doesn't destabilize, in sim, before flashing.
  - **Warm-start** BO / RL with sim-good initial guesses.
  - **Hardware-in-the-loop** — run the real controller board against the simulated plant to shake out code + timing bugs with zero rig risk.
- Track the **sim2real gap itself as a metric** that shrinks each iteration — it's your model-quality scoreboard.

---

## 6. Suggested end-to-end workflow

1. Build the DFT rig (§1), single actuator, 1-DOF constrained.
2. ID the real plant (§2) → calibrated model.
3. Model-based gains → verify stable, logged hover.
4. Systematic tune: BO / IFT on a log-derived cost (§3–4).
5. Add DOFs / coupling → re-ID → add control allocation ([[Maglev - Control Allocation and MIMO]]).
6. (Optional) learning layer outside the stabilizer (§3 Rung 5).
7. Recalibrate the sim throughout; keep the gap metric falling.

---

*See also:*
- *[[Maglev - Python Simulation Sandbox]] — the digital twin you recalibrate against rig data*
- *[[Maglev - Control Theory Fundamentals]] — the loop-shaping / LQR that generates the baseline gains*
- *[[Maglev - Control Allocation and MIMO]] — what changes when you go 1-DOF → multi-actuator*
- *[[Maglev - Sensing and Flux Feedback]] — the signals you're logging and their trust regimes*
- *[[Levitation Research Claude]] Key Finding 5 — why learning layers stay outside a stabilizing controller*

# Maglev - Cytron MD25HV Motor Driver

*Candidate OTS H-bridge for [[Maglev - Hardware and Implementation]] §1. [Product page](https://www.cytron.io/c-motor-and-motor-driver/c-motor-driver/p-25amp-7v-58v-high-voltage-dc-motor-driver) · datasheet: `datasheets/Cytron_MD25HV_Sheet.pdf`.*

## Spec Summary

| Parameter | Value |
|---|---|
| Input voltage | 7–58 V |
| Continuous / peak current | 25 A / 60 A |
| PWM **input** frequency (command) | DC–40 kHz |
| PWM **output** (switching) frequency | **16 kHz fixed**, independent of input frequency |
| Logic input high level | 3–30 V (5V/3.3V MCU compatible) |
| Control modes | PWM+DIR, or POT+switch |

## Concerns — Input/Output Frequency

- **Output switching frequency is fixed at 16 kHz and explicitly decoupled from the input command frequency** ("Output frequency is independent of input frequency," datasheet §2). You cannot raise switching frequency to buy more current-loop bandwidth or lower ripple — 16 kHz is a hard ceiling set inside the board, not by the MCU's PWM peripheral.
- That decoupling implies an internal resample/regeneration stage between the commanded duty cycle and the actual 16 kHz output. The datasheet gives no propagation delay or phase spec for it — an unquantified latency sitting inside the current loop.
- **No ADC-PWM sync output.** The 16 kHz switching clock is internal and not exposed, so the MCU can't trigger current-sense ADC sampling at the switching midpoint (the trick C2000/H7 use to reject switching noise). This reintroduces the "ADC sampling during PWM transitions" problem already flagged in [[Maglev - Hardware and Implementation]] §2.
- Driving the input command above 16 kHz buys nothing (output is pinned) and risks beat-frequency interaction with the internal 16 kHz switcher — command at ≤16 kHz, ideally an integer fraction of it.
- On raw bandwidth: 16 kHz switching → ~800 Hz–2.4 kHz achievable current-loop bandwidth (5–15% rule, per main doc), comfortably above the ≥21.5–43 Hz needed (5–10× the 4.3 Hz unstable pole). **Frequency headroom is not the risk here — sync/latency/jitter is.**

## Other Mismatch (non-frequency)

- Rated 25 A cont / 60 A peak vs. an expected ~1–3 A coil current is a >10× oversizing. At the resulting very low duty cycles, high-current MOSFET gate drive/dead-time can produce a current deadband near the bias point — worth bench-verifying before committing, since the PM-bias linearization scheme depends on clean small-signal δi around I_b.
- "Brake" state (PWM low, DIR don't-care) hard-shorts both motor terminals — confirm this is a clean freewheel path for an inductive coil load, not just motor-tuned behavior.

## Characterization

Goal: turn the unknowns in the Concerns section (internal resample latency, ripple, deadband) into numbers, so Kp/Ki and the PI loop rate are set from measured driver+coil behavior instead of the idealized RL model. This is a driver-specific instance of the "Electrical" plant-ID bullet in [[Maglev - Experimental Controller Iteration]] §2 — same philosophy (identify before tuning), applied to this board.

### What to identify

- **Command→output transport delay** — time from a PWM/DIR command edge to the actual switch transition at the motor terminals. This is the unquantified resample latency flagged above; it eats phase margin and caps achievable crossover.
- **DC gain and deadband** — average coil current vs. commanded duty, especially at low duty near the bias point (25 A-rated FETs driving a ~1–3 A load is where a deadband would show up).
- **Electrical time constant** — effective L/R of coil + driver output stage, from current rise on a duty step.
- **Ripple** — amplitude and frequency content of steady-state current at a fixed duty (should show a 16 kHz component); sets the current-sensor bandwidth/anti-alias requirement and a noise floor that bounds usable Ki.
- **Current-limit interaction** — where the driver's own active current limiting (§6, temperature-dependent) engages relative to the PI's intended operating range, so the two loops don't fight.

### Test sequence (bench, cheap → rich)

1. **Static duty sweep** (open-loop, no PI): step commanded duty in fine increments across the expected operating range, log steady-state current at each point. Reveals DC gain curve and any deadband/stair-stepping near low duty.
2. **Duty-step response**: from a fixed bias duty, apply a small step (±5–10%) and capture current at high sample rate (scope + shunt, or fast Hall probe — not just the onboard sense, which won't out-resolve the effect being measured). Fit the rise to get τ = L/R_eff, and scope the motor-terminal voltage on the same trigger to directly measure the command→switch transport delay.
3. **Steady-state ripple capture**: at a representative bias current, log current at ≥5× the 16 kHz switching rate; confirm ripple frequency/amplitude and check it against the current sensor's bandwidth.
4. **Chirp/PRBS ID**: inject a small-signal PRBS or swept-sine on duty around the bias point, log current, compute the empirical duty→current frequency response (FFT-based transfer function estimate). This is the highest-value single test — it captures DC gain, electrical pole, transport delay, and any driver-internal dynamics in one measured Bode plot, rather than three separate curve-fits.
5. **Current-limit boundary check**: command a large step toward the datasheet's peak rating, confirm the OC LED / active limiting behavior matches expectations and doesn't ring or oscillate against the PI's own saturation handling.

### From data to Kp/Ki

- Fit the PRBS/step data to a first-order-plus-delay model: `G(s) = K_dc / (τ_e s + 1) · e^(−sT_d)`.
- Pole-cancellation starting point: set `Ki/Kp = R/L` (i.e., `1/τ_e`) to cancel the electrical pole, then pick `Kp` for the desired crossover — capped by `T_d` and by the 16 kHz switching (Nyquist-style: don't target crossover near 16 kHz/2).
- Alternative: IMC tuning rule (`Kp = τ_e / (K_dc·(T_d + λ))`, `Ki = Kp/τ_e`) with `λ ≈ T_d` for a robust starting point — less brittle than pole cancellation if the delay estimate is noisy.
- **Validate against the measured Bode, not just the fitted model** — the driver's internal resample stage may deviate from a clean first-order+delay shape at higher frequency; the PRBS-derived frequency response is ground truth, the analytic fit is only for picking a starting gain set.
- Hand the result to Rung 1 (structured hand tuning) in [[Maglev - Experimental Controller Iteration]] §3 for closed-loop refinement — characterization gets you a good starting point, not final gains.

### Loop-rate selection

- Two distinct rates: the MCU's PI compute/update rate, and the driver's fixed 16 kHz physical switching rate. The output can't respond faster than the latter regardless of how fast the PI computes.
- Pick the compute rate as a clean sub-multiple of 16 kHz (e.g., 4 kHz or 2 kHz) so the command↔switch phase relationship stays deterministic, informed by the measured transport delay (step 2) rather than assumed.
- Since there's no ADC-PWM sync (see Concerns), oversample the current-sense ADC relative to the compute rate and average, or add an anti-alias filter ahead of it, to keep 16 kHz ripple from aliasing into the feedback signal.
- Target current-loop crossover well below 16 kHz/2 (practically, keep it near the ~800 Hz–2.4 kHz bandwidth estimate from the Concerns section) — the identified `T_d` and ripple data from above will tell you how close to that ceiling is actually usable before phase margin erodes.

## Status

OTS H-bridge is the preferred route; a custom PCB is only in scope if we go the linear transconductance/VCCS amplifier path (deprioritized for now — see [[Maglev - Hardware and Implementation]] §1). This board is a candidate pending the Characterization bench sequence above.

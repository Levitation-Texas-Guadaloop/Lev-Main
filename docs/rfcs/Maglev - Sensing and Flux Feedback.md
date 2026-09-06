# Maglev - Sensing and Flux Feedback

*Support doc for [[Levitation Research Claude]] — answers Section H question: what does flux feedback add, and why care about it if power and gap already govern the controller?*

---

## 1. The Argument Against Flux Feedback (Steelmanned)

Your question is essentially:

> *I know the voltage I'm applying (power) and I know the gap (position). Force is F = k(i/x)². Current is what I control. Gap is what I measure. Why do I need to also measure flux?*

This is a reasonable position. In the ideal model:
- Gap x is measured directly.
- Current i is set by the inner loop.
- Force F = k_i · i follows immediately.

If the model were perfect and the current loop were perfect, flux measurement would add nothing — it's a redundant encoding of information you already have.

---

## 2. The Three Failure Modes of "Current + Gap Is Enough"

### Failure 1: Current ≠ Flux (Hysteresis)

Steel is a nonlinear magnetic material. The B-H curve of your yoke steel has *hysteresis*: the flux density B for a given magnetizing field H (proportional to current NI/ℓ_iron) depends on the *history* of prior magnetization, not just the present current.

This means two coils with identical current and identical gap can have different flux — and therefore different force — depending on how they were driven before. This effect is especially significant in soft ferrites or grain-oriented electrical steel, less so in high-permeability alloys, but non-negligible in any real yoke.

Measuring flux directly (Hall sensor in the air gap) tells you the actual B, bypassing the hysteresis uncertainty entirely.

### Failure 2: PM Bias Drifts With Temperature

Your yoke has a permanent magnet providing the bias flux Φ_b. N52 neodymium magnets have a temperature coefficient of remanence of about **−0.12%/°C**. Over a 30°C rise (not unusual near a coil that's been energized for minutes), the PM's contribution drops by ~3.6%.

The linearized force model uses k_i = f(Φ_b). If Φ_b drifts, k_i drifts — and your outer loop was tuned assuming a fixed k_i. The result is a slow change in the effective plant gain that the controller doesn't know about. With pure current sensing, you cannot distinguish "PM weakened" from "coil operating normally."

A Hall sensor in the gap sees the *total* flux (PM + coil), which reflects the actual PM state. If the PM has weakened, the sensor reading drops and the observer can compensate.

### Failure 3: Flux Saturation Is Invisible to a Current Sensor

Force saturates when the steel saturates — above the knee of the B-H curve, adding more current adds little more flux and therefore little more force. But the current sensor reads the same rising current while force has plateaued.

A flux sensor tells you directly when you're near saturation. Above saturation, the linear model F = k_i · i completely breaks down, and a controller relying on it will either over-command or oscillate.

---

## 3. The Physics: Force Is a Function of Flux, Not Current

This is the fundamental reason. Going back to first principles (from [[Maglev - PM Bias and Force Linearization]]):

$$F = \frac{\Phi^2}{2\mu_0 A}$$

where Φ is the *total* flux through the air gap. Force depends on flux squared — not on current directly. Current produces flux via Ampere's law (NI = Hℓ → B = μH → Φ = BA), but the relationship NI → Φ is mediated by the steel's permeability, which is nonlinear, temperature-dependent, and history-dependent.

When you sense current and assume Φ = NI/ℛ, you are trusting that:
1. ℛ (reluctance) is well-known and constant.
2. The PM adds exactly Φ_b to this.
3. The steel is linear (not saturated, no hysteresis).

All three assumptions fail to some degree. Flux sensing bypasses all three.

---

## 4. What Flux Feedback Actually Provides

### For the Inner Loop

Replace the current-controlled inner loop with a **flux-controlled inner loop**: the reference is Φ_ref instead of i_ref. The control law drives Φ (measured by Hall sensor) to Φ_ref.

This inner loop is now:
- Insensitive to coil resistance variation (R changes with temperature → current changes for fixed voltage, but flux tracks the reference directly)
- Insensitive to PM drift (the PM's contribution is automatically included in the measured flux; the coil only needs to add the remainder)
- Naturally saturating-aware (the loop won't command more voltage once the Hall sensor says Φ has reached its limit)

### For the Observer

An EKF estimating the state (x, ẋ, Φ) has much lower model uncertainty than one estimating (x, ẋ, i):
- The flux Φ is the direct physical cause of force.
- Substituting Φ_measured for Φ_estimated removes a major source of estimation error.

The observer's job becomes: estimate velocity ẋ from noisy gap measurements. The force is no longer estimated — it's computed from the Hall sensor.

### For the MIMO Outer Loop

The outer (stabilizer) loop computes desired forces → desired fluxes → flux references for each coil's inner loop. The mapping from flux to force (F = Φ²/2μ₀A) is much better-conditioned than the mapping from current to force (F = k(i/x)², which depends on the gap).

---

## 5. Is It Redundancy or Complementary?

Both, but in different senses:

**Redundancy:** current + Hall together are two measurements of the magnetic state. If one sensor fails, the other gives partial information. This improves reliability.

**Complementary:** they fail in different ways.
- Current sensing fails at detecting hysteresis and PM drift.
- Hall sensing can have its own calibration drift and is sensitive to stray fields from adjacent coils.
- Gap sensing is excellent for low-frequency absolute position but noisy at high frequency.

The recommended IMU + gap + current + Hall fusion (via EKF) uses each sensor in the frequency/condition regime where it's most reliable:

| Sensor | Good for | Poor for |
|---|---|---|
| Gap (inductive) | Absolute position, DC | High-freq noise, common-mode interference |
| IMU (accel/gyro) | High-freq motion, tilts | Drift, absolute position |
| Current | Control actuation, fast dynamics | PM drift, hysteresis, saturation |
| Hall (flux) | PM health, saturation detection, actual B | Stray fields, temperature sensitivity of sensor |

---

## 5b. Primary Gap Sensing (the loop you close first)

Before flux, the *primary* feedback on any maglev/AMB is a **non-contact gap sensor** — it's what stabilizes the RHP pole. The literature is dominated by two technologies:

- **Eddy-current probes** — the AMB/maglev workhorse (Schweitzer–Maslen's standard sensor). A coil induces eddy currents in the conductive/ferrous rail; the gap changes the coil impedance. Non-contact, kHz+ bandwidth, sub-micron resolution, robust to dust/oil. Trade: sensitive to target material and temperature, needs per-rail calibration.
- **Variable-reluctance / inductive gap sensors** — cheaper, used on EMS trains. This is essentially the current setup — and, as expected, the noisier of the two.

Niche for a rail-guided pod: **capacitive** (sub-nm but tiny range, contamination-sensitive → nanopositioning only), **optical/laser triangulation** (high res but dust/reflectivity-sensitive → lab), **self-sensing/sensorless** (infer gap from current-ripple/inductance — no extra hardware, but noisy and model-dependent; not for primary stabilization on an unstable plant).

**Recommendation for this pod:**
- **Primary gap:** eddy-current sensing against the steel rail. Budget route that fits the Teensy/FPGA stack — a **TI LDC1614 / LDC1101 inductance-to-digital converter** with a custom sense coil (cheap, digital, good resolution against steel; a real upgrade over the noisy inductive sensors). Commercial option: Micro-Epsilon eddyNCDT / Kaman if budget allows.
- **Complement** with per-coil current (ACS711), Hall flux per yoke (§6), and IMU for attitude — fused per the §5 table.

Consensus: gap sensor for absolute low-frequency position, current for fast actuation, flux for PM/saturation health, IMU for high-frequency attitude — no single sensor suffices on a RHP-pole plant.

---

## 6. Practical Hall Sensor Placement

Place one Hall sensor per yoke in the air gap, between the pole face and the rail. Specifically:
- **Center of the pole face** gives the average flux, which is what the force integral depends on.
- **Not in the leakage path** (fringe field around the edge of the yoke).
- Oriented with its sensitive axis **perpendicular to the pole face** (i.e., along the force direction).

**Sensor IC selection:** the previous recommendation here (Allegro A1324/A1325, ±50 mT range) is superseded — not because of a range crisis (IRL Gauss-meter testing shows the real pole-face field stays well under the ~1.15 T illustrative bias in [[Maglev - PM Bias and Force Linearization]] §7, even at max coil current), but because faster, lower-noise parts are available at similar cost. See **[[Maglev - Hall Sensor Selection]]** for the full datasheet-verified comparison; current top pick is the **Allegro A1308LLHLX-05-T** (≈±400 mT range, 20 kHz bandwidth), runner-up **TI DRV5055A4** (±169 mT, best-in-class noise floor). Both mount easily on a small PCB glued into the gap, same as originally intended.

---

## 7. Summary

You *can* build a working controller with just current and gap. In fact that's the correct starting point (as the research doc recommends). But "working" has limits:

- PM thermal drift will cause a slow bias error in the gap that the controller compensates by slowly adjusting current — wasteful and potentially leading to saturation if the PM has significantly weakened.
- Hysteresis will create small force errors the controller has to continuously correct.
- You will not know when you're near saturation until the controller starts oscillating.

Adding Hall flux sensors (per yoke) is low cost (~$2–5 per sensor), easy to implement, and removes these three failure modes. The IEEE study cited in the main doc confirms: the combined flux+current method "rejects the deficiencies" of each alone.

---

*See also:*
- *[[Maglev - PM Bias and Force Linearization]] — derives why force depends on flux, not current*
- *[[Maglev - Control Theory Fundamentals]] — discusses the inner current/flux loop and its role in the nested architecture*
- *[[Maglev - Hall Sensor Selection]] — datasheet-verified Hall IC comparison and selection for the §6 placement above*
- *[[Maglev - Hardware and Implementation]] — practical notes on Hall sensor integration with MCU/FPGA*

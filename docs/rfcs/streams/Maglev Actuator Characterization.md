# Maglev — Actuator Characterization

Robust experimental methods to extract the electromagnetic parameters of the PM-biased actuator — primarily **inductance vs. gap `L(x)`**, plus the parameters that fall out of the same rigs (`R`, `ℛ₀`, effective pole area `A_eff`, eddy-current corner, saturation knee).

Companion to [[Maglev - PM Bias and Force Linearization]] (what the numbers feed), [[Maglev - Sensing and Flux Feedback]], [[Maglev - Hardware and Implementation]] (rig hardware). Motivating result: a single LCR reading (`L≈2mH @ gap=∞`, `R≈1.1Ω`) is inconsistent with `μ_rec=1.05` if read as the iron+PM series path — see the consistency check in [[Maglev - PM Bias and Force Linearization]]. A single number can't tell you *why*; the methods below can.

---

## 0. Why the LCR meter alone is not enough

The LCR meter gives **one complex impedance at one frequency and (usually) zero DC bias**. For this actuator that hides everything that matters:

- **No DC bias.** The PM already sets a steel operating point (`B_b≈1.15T`, near the 1018 knee). Incremental `μ_r` and `μ_rec` at that bias ≠ their small-signal values about `B=0`. LCR at ~0 bias measures the wrong operating point.
- **Single frequency → eddy currents invisible.** Solid 1018 yoke: at the LCR's 1 kHz the flux is already partly excluded from the core interior (skin effect). `L` measured at 1 kHz < `L` at DC, and `R` at 1 kHz > `R_dc`. The number you get depends on the test frequency and you can't see the trend.
- **Lead/contact resistance.** `R≈1.1Ω` is small; 2-wire LCR leads corrupt it. (`L` less affected, `R` badly.)
- **Small-signal only** — no saturation, no hysteresis loop.

Rule: **report `L(x, f, I_bias)`, not `L`.** Anchor with a spectrum, not a point.

---

## 1. Recommended methods (ranked)

### A. Swept-sine impedance spectrum — *primary method*
Drive coil with a sine, sweep `~1 Hz → 10 kHz`, measure complex `Z(jω)=V/I`.

- Rig: function generator → power buffer (or the existing H-bridge in linear/low-duty mode) → coil in series with a **4-wire-sensed** low-inductance resistor `R_s` (metal-foil, ~0.1–1 Ω). Scope both `V_coil` and `V_Rs` (= current). Take magnitude + **phase** at each frequency. A hobby VNA, a sound-card impedance jig (≤ ~20 kHz), or a Bode-plotter DAQ all work.
- Extract per frequency: `R(ω)=Re Z`, `L(ω)=Im Z / ω`.
- **What it reveals directly:**
  - Low-`f` asymptote `Z→R_dc` and `L→L₀` (the "magnetostatic" inductance you actually want for `ℛ(x)`).
  - **Eddy-current corner:** `L(ω)` rolls off and `R(ω)` rises above some `f_e`. That corner *is* the flux-lag pole flagged as a bandwidth risk (see eddy thread in handoff / [[Levitation Research Claude]]). Measure it, don't estimate it.
- Repeat at each gap and at realistic DC bias (see §2). Best single investment.

### B. Step / L–R transient scoping
Apply a voltage (or current) step; scope the current through `R_s`.

- Voltage step: `i(t)=(V/R)(1−e^{−t/τ})`, `τ=L/R` → `L=τR`. Fit the whole curve, not just the knee.
- Cleaner: **current step** via the H-bridge (command a set-point, log current) — removes `R` dependence from the time constant to first order.
- **Solid-steel eddy currents make this multi-exponential**, and that's a *feature*: early time shows a fast, low-apparent-`L` component (eddy shielding excludes flux from the core), late time relaxes to the full `L₀`. Fit a 2-exponential and you get both `L₀` and an eddy time constant — cross-checks method A.
- Freewheel variant: open the drive, let current decay through a known dump resistor/diode; measure the decay `τ`.
- Keep the step small (or centered on the bias point) to stay linear / avoid the saturation knee.
- **Uses hardware you already have** (H-bridge + sense resistor + scope).

### C. PWM current-ripple slope — *in-situ, zero extra hardware*
While the actuator runs under normal PWM, the current ripple within one switching period has slope set by `L`:

- On-time: `di/dt = (V_bus − iR)/L`. Off-time (freewheel): `di/dt = (−iR − V_f)/L`.
- Scope the current ripple, read the two slopes → solve `L` (and `R` as a bonus) **at the true operating gap, bias, and temperature**, live.
- Best method for the *actual* operating-point `L` under closed-loop conditions; noisier than A/B, so average many periods.

### D. Flux-linkage integration (`λ–i` loop) — for nonlinearity/saturation
`λ(t) = ∫(v − iR)\,dt`. Plot `λ` vs `i`.

- Slope `dλ/di` = **incremental** `L`; secant `λ/i` = **apparent** `L`. Loop area = hysteresis.
- Sweep amplitude to map `L(i)` and locate the saturation knee (relevant: `B_b≈1.15T`). Sweep gap for `L(x,i)` surface.
- Needs accurate `R` and a drift-managed integrator (AC excitation + periodic reset, or an analog integrator with leak). This is the honest way to see the `μ_r(B)` breakdown near saturation.

### E. LC resonance — precise spot value
Add a known precision `C`, find `f_res` → `L = 1/((2πf_res)²C)`. Choose `C` so `f_res` sits **below** the eddy corner `f_e` if you want the magnetostatic `L`. Cheap, precise, single-frequency; pairs well with A as a cross-check.

### F. LCR meter, done right
If keeping it: use a **bias-capable** LCR (or external bias tee: DC supply through a large choke, AC through a blocking cap), **4-wire Kelvin** leads, and **sweep its test frequency**. Report `L` at several frequencies. Now it's a coarse version of A.

---

## 2. Controls common to every method (do not skip)

- **Fix the gap mechanically.** Precision **non-magnetic** shims (plastic/brass/aluminum, known thickness) or a micrometer stage between pole faces and target. Verify with feeler gauge. Non-magnetic clamp. Anchor the two ends: **keeper (`x≈0`)** and **`x=∞` (target removed)**.
- **Lock the pod.** PM bias + coil excitation produces force; any motion corrupts `L(x)` and injects motional EMF. Clamp rigidly during characterization.
- **Measure at the real DC bias current**, PM in place. Incremental `L` is what the current loop sees; it differs from zero-bias `L`. Superimpose small AC on the operating DC.
- **4-wire everything.** `R=1.1Ω` is small — Kelvin-sense the coil and the sense resistor.
- **Log coil temperature** (or infer from `R_dc` drift). `μ_r`, `μ_rec`, and PM remanence all drift with temp; a "changed `L`" may just be warm iron/magnet.
- **Separate `R_dc` (4-wire, DC) from `R(ω)`** (from the impedance phase). The gap between them is the eddy/skin signature.

---

## 3. From data to parameters

**`L(x)` → reluctance model.** At low frequency, `ℛ_total(x) = N²/L(x)`, `N=250`. Fit the series-gap model:
```
ℛ_total(x) = 2x/(μ₀ · A_eff) + ℛ₀
```
- Linear regression of `ℛ_total` vs `x`:
  - **slope** = `2/(μ₀ A_eff)` → `A_eff` (checks fringing/leakage vs the 1"×1" geometric face).
  - **intercept** `ℛ₀ = ℛ_pm + ℛ_steel` (the gap-independent part).
- With `μ_rec` fixed, subtract `ℛ_pm = l_pm/(μ₀ μ_rec A_eff)` from `ℛ₀` to get `ℛ_steel` → `μ_r`. **If `ℛ_steel` comes out ≤ 0, the `μ_rec` / "both PMs in series" assumption is falsified** (this is exactly the open question from [[Maglev - PM Bias and Force Linearization]] — the sweep resolves it, the single point can't).
- Watch for **leakage**: at large `x`, measured `L` plateaus above the series-model prediction (flux short-circuits leg-to-leg through the window, bypassing gap and PMs). A plateau ⇒ add a parallel leakage permeance to the network, and treat the `x=∞` point as leakage, not the iron path.

**`dL/dx`** (from the fitted `L(x)`) → motional back-EMF coefficient `i·dL/dx·ẋ` and a cross-check on the force constant (reluctance-actuator identity, PM-modified). Feeds inner-loop fidelity — see the back-EMF thread.

**`L(x, f)`** → eddy corner `f_e` → flux-lag pole; decides laminated vs. solid vs. SMC yoke.

**`λ–i`** → saturation knee, incremental vs. apparent `L`, hysteresis loop area.

| Parameter | Best method | Notes |
|---|---|---|
| `L₀(x)` (magnetostatic) | A (low-`f` asymptote), E | anchor with keeper + `x=∞` |
| `L` at operating point | C (PWM ripple) | live, real bias/temp |
| `R_dc` | 4-wire DC | Kelvin; small value |
| `R(ω)`, eddy corner `f_e` | A, B (multi-exp) | flux-lag pole |
| `A_eff`, `ℛ₀` | fit `ℛ(x)` from A | slope/intercept |
| `μ_r` (given `μ_rec`) | `ℛ₀` − `ℛ_pm` | sign test on `ℛ_steel` |
| saturation / hysteresis | D (`λ–i`) | sweep amplitude |

---

## 4. Minimal first pass (what to actually do)

1. 4-wire `R_dc`.
2. Method A swept-sine at **3–4 gaps** (keeper, ~1 mm, ~3 mm, `x=∞`), at operating DC bias. Get `L(x)` (low-`f`) and `f_e`.
3. Method C ripple check at the nominal operating gap to confirm the live value.
4. Fit `ℛ(x) = 2x/(μ₀A_eff)+ℛ₀`; report `A_eff`, `ℛ₀`, and the `μ_r` sign test.
5. If saturation suspected near bias, one Method-D `λ–i` sweep.

Everything except the swept-sine source you already own (H-bridge, sense resistor, scope).

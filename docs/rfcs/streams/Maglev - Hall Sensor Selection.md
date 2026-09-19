# Maglev - Hall Sensor Selection

*Support doc for [[Levitation Research Claude]] — datasheet-verified Hall-effect IC selection and placement for the per-yoke flux sensor called for in [[Maglev - Sensing and Flux Feedback]] §6.*

---

## 1. Flux vs. Field: What a Hall IC Actually Measures

### 1a. The Hall effect mechanism

A Hall element is a thin current-carrying conductor (or doped semiconductor). Drive a bias current I through it and apply a magnetic field B perpendicular to the current-carrying plane: the Lorentz force `F = qv × B` deflects the moving charge carriers sideways, building up a transverse electric field until it balances the magnetic deflection. The result is a measurable **Hall voltage**:

$$V_H = \frac{I \cdot B}{n\,q\,t}$$

(n = carrier density, q = carrier charge, t = element thickness). For a fixed bias current and a given IC's fixed geometry/doping, `V_H ∝ B` at the physical location of the die — nothing more.

**A Hall IC therefore measures magnetic flux density B (Tesla), a local point quantity, not flux Φ (Weber, the areal integral of B).** Every part surveyed below outputs (or digitizes) a voltage/count proportional to B *at the sensor's silicon*.

### 1b. "Flux sensing" in this vault is actually point-B sensing

[[Maglev - Sensing and Flux Feedback]] uses Φ throughout (`F = Φ²/2μ₀A`, PM bias Φ_b, etc.) because that's the physically correct force variable. But no sensor in this doc — or in typical AMB practice — measures Φ directly. The working approximation is:

$$\Phi \approx B_{\text{sensor}} \cdot A_{\text{pole face}}$$

This holds **only if B is reasonably uniform across the pole face** — reasonable near the center of a 1"×1" pole away from fringing (see [[Maglev - Coupling and Geometry]] for the yoke geometry), but it is an *inferred* areal extrapolation from one point sample, not a true integrated measurement. It will under/over-state Φ if the field sags toward the edges (fringing) or saturates unevenly (steel knee, [[Maglev - PM Bias and Force Linearization]] §4b).

A **true integrated flux measurement** requires either:
- A **search/pickup coil** wound around the flux path, integrating the induced EMF `∫V dt = ΔΦ` (Faraday's law) — gives Φ directly but only *changes* in Φ (AC-coupled; needs a reset/drift-correction scheme for DC bias), or
- A **fluxgate magnetometer**, which also senses B at a point (via saturable-core nonlinearity, not the Hall effect) — still a point sensor, not integrating, despite the name, or
- An **array of Hall points** spatially sampling the pole face and numerically integrating `Φ = ∬ B \, dA`.

For this project, a single well-placed Hall IC at pole-face center giving `Φ ≈ B·A` is the right level of complexity — consistent with the existing §6 placement guidance — but the doc should be explicit that this is an approximation, not a flux measurement in the rigorous sense.

### 1c. Four sensor technology families, contrasted

| Family | What it measures | Typical FS range | Typical BW | Form factor | Fit for this application |
|---|---|---|---|---|---|
| **Linear analog Hall IC** (ratiometric, e.g. Allegro A13xx, TI DRV505x) | Point B, 1-axis | tens–hundreds of mT | 10–20 kHz | SOT23/TO-92, mm-scale | **Good fit** — small, fast, cheap |
| **Digital Hall IC** (I²C/SPI, often 3-axis, e.g. Melexis MLX90393, Infineon TLI493D) | Point B, 1–3 axis, digitized | tens–hundreds of mT, programmable | ~1–6 kHz (ADC/mux-limited) | QFN, mm-scale | **Good fit**, esp. if 3-axis leakage diagnostics wanted; bandwidth-limited vs. analog |
| **Fluxgate sensor** | Point B, via saturable core, not Hall effect | µT to low mT | Hz–kHz | Often larger (mm–cm, coil-wound core) | **Poor fit** — full-scale range is orders of magnitude too small for this application's field levels; built for magnetometry (Earth-field-scale), not actuator bias fields |
| **Closed-loop compensated Hall** (current-transducer style, e.g. LEM/LTS parts) | Point B, nulled via a compensation coil driven to cancel the sensed field | up to several T (current-transducer product lines) | often good (tens of kHz) | **Large** — needs a compensation winding + magnetic core around the sensed conductor/gap | **Poor fit for a point sensor** — these are built to wrap around a current-carrying busbar, not glue into a 3 mm working air gap. The "closed-loop" design is about current-sensing accuracy, not point-field measurement at an actuator pole face. |

Fluxgates are ruled out on **range** (µT–low-mT territory, orders of magnitude short of the mT-to-T territory this application lives in). Closed-loop compensated Hall is ruled out on **footprint and application fit** (designed to encircle a conductor, not to sit as a thin point sensor in a 3 mm gap). A **linear (or digital) Hall IC with a wide-enough full-scale range** is the correct family for this job — the only question is which part.

---

## 3. Candidate Sensors — Datasheet-Verified

All figures below are pulled directly from the manufacturer datasheet indicated (not secondhand summaries); Gauss/mT conversions use the datasheets' own 1 mT = 10 G convention. "FS Range" is the **linear (non-saturating) full-scale range**, computed from the datasheet's own output-swing/sensitivity spec where not published as a headline number (method shown per-row).

| #   | Part                                                     | Output type                                            | FS range                                                                                                                             | Sensitivity                                                                                                                       | Bandwidth / response                                                                                                     | Noise                                                                                                             | Tempco (sensor)                                                                        | Package                                      | ~Unit price                  | Datasheet                                           |
| --- | -------------------------------------------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- | -------------------------------------------- | ---------------------------- | --------------------------------------------------- |
| 1   | **Allegro A1308LLHLX-05-T**                              | Analog, ratiometric, 1-axis                            | **≈±390–400 mT** (calc. from V_CLAMP/Sens, typ.)                                                                                     | 0.43–0.57 mV/G (0.5 typ) = 5 mV/mT                                                                                                | 20 kHz (−3 dB)                                                                                                           | 2.5 mG/√Hz = 0.25 µT/√Hz input-referred                                                                           | 0.08–0.16 %/°C                                                                         | SOT-23W / SIP                                | ~$1.29 (DigiKey, 1-pc)       | A1308-9-DS, Rev. 15, May 28 2026 [1]                |
| 2   | **TI DRV5055A4 / Z4**                                    | Analog, ratiometric, 1-axis                            | **±169 mT** (VCC=5V) / ±176 mT (VCC=3.3V) — datasheet-published `B_L` spec                                                           | 12.5 mV/mT                                                                                                                        | 20 kHz, 10 µs propagation delay                                                                                          | 130 nT/√Hz (VCC=5V) input-referred                                                                                | A4: 0.04–0.2 %/°C (magnet-drift-compensated); Z4: 0 %/°C (uncompensated)               | SOT-23-3                                     | ~$0.86–0.93 (DigiKey)        | SBAS640C, Jan 2018 – rev. Jun 2026 [2]              |
| 3   | **Infineon TLE4997E2**                                   | Analog (DAC), ratiometric, 1-axis, EEPROM-programmable | ±50 / ±100 / **±200 mT** (3 selectable ranges)                                                                                       | ±12.5 to ±300 mV/mT (programmable)                                                                                                | Programmable internal LP filter: 78 Hz – 1.32 kHz in 8 steps (or filter "off," bounded by 16 kHz output update rate)     | 4.68 mV_pp typ. (100 mT range, 60 mV/mT sens., 244 Hz internal + 160 Hz external RC)                              | Calibrated in EEPROM (temp-compensation coefficients TC1/TC2 programmable)             | Small SMD (PG-SSO/similar)                   | not found                    | Data Sheet V2.10, April 2020 [3]                    |
| 4   | **Infineon TLI493D-W2BW / A2B6**                         | Digital I²C, 3-axis (X/Y/Z) + temp                     | **±160 mT** (datasheet headline spec, full-range mode)                                                                               | 5.5–10.5 LSB₁₂/mT (7.7 typ.), 12-bit                                                                                              | Fast mode: up to 5.8 kHz (3-axis+temp) / 7.8 kHz (3-axis only)                                                           | 85 µT rms (X/Y, 1σ, full range); 75 µT rms (Z)                                                                    | −15…+15 % sensitivity drift band (TC0)                                                 | Small QFN, ~1.1×0.9×0.6 mm die-scale package | ~$3–4 (bare IC, JLCPCB ref.) | v01.00 (W2BW); v1.3 (A2B6 variant) [4]              |
| 5   | **Melexis MLX90393**                                     | Digital I²C/SPI, 3-axis, programmable gain/range       | X/Y: ≈±5 mT (max gain) to **≈±105 mT** (min gain); Z: up to **≈±192 mT** (min gain) — calculated from published µT/LSB × 16-bit span | 0.161–3.220 µT/LSB (X/Y), 0.294–5.872 µT/LSB (Z), programmable via GAIN_SEL + RES_XYZ                                             | Conversion time 259 µs–66.6 ms per axis (programmable OSR/DIG_FILT); realistic multi-axis update ~1 kHz at fast settings | ~3–5 µT RMS at fastest (~1 ms) conversion time, <1 µT RMS at slow (~100 ms) settings — explicit noise/speed trade | ±3 % sensitivity thermal drift (uncompensated), on-chip TCMP_EN compensation available | 16-QFN 3×3 mm                                | ~$2.13 (DigiKey, 1-pc)       | Rev. 012, Nov 18 2025 [5]                           |
| 6   | **Honeywell SS495A** (SS490 series)                      | Analog, ratiometric, 1-axis                            | **±60–67 mT** (−600…+600 G min guaranteed, ±670 G typ)                                                                               | 3.00–3.25 mV/G (3.125 typ) = 31.25 mV/mT                                                                                          | Response time 3 µs (implies >100 kHz-class step response)                                                                | Not specified in this datasheet (older, simpler part; no noise-density spec published)                            | **0.01–0.05 %/°C** — best-in-class of all parts surveyed                               | TO-92-style radial-lead                      | low-cost, legacy part        | Honeywell SS490 series datasheet (doc 005843-2) [6] |
| 7   | **Allegro A1391** (of the A1391/2/3/5 micropower family) | Analog, ratiometric, 1-axis, sleep mode                | **≈±112 mT** (calc. from V_OUTH/L, Sens, VCC=VREF=3.0V typ.)                                                                         | 1.25 mV/G = 12.5 mV/mT (widest-range member of the family; A1392/3/5 are 2×/4×/8× more sensitive → proportionally narrower range) | 10 kHz (−3 dB)                                                                                                           | 6–12 mV_pp typ (2 kHz ext. LPF)                                                                                   | not broken out separately from the A1324 family in this datasheet                      | MLP/DFN, 2×2 mm                              | low-cost                     | A1391-DS, Rev. 10, Dec 3 2021 [7]                   |
| 8   | **Allegro A1324/A1325** *(original vault pick, see §2)*  | Analog, ratiometric, 1-axis                            | **≈±44–50 mT** (datasheet-confirmed)                                                                                                 | 5.0 / 3.125 mV/G                                                                                                                  | 17 kHz internal BW                                                                                                       | 1.3 mG/√Hz = 0.13 µT/√Hz                                                                                          | 0–0.03 %/°C (best raw tempco of any linear analog part surveyed)                       | SOT-23W / SIP                                | ~$1–2                        | A1324-DS, Rev. 9, June 16 2022 [8]                  |
| 9   | **AKM EQ-431L**                                          | Analog, ratiometric, 1-axis                            | **≈±22–27 mT** — *flagged misfit*                                                                                                    | 55–75 mV/mT (65 typ.)                                                                                                             | Response time 1–2 µs                                                                                                     | 5 mV_pp                                                                                                           | not broken out                                                                         | small SMD                                    | not found                    | AKM EQ-431L datasheet (akm.com) [9]                 |
| 10  | **AKM EQ-730L**                                          | Analog, ratiometric, 1-axis                            | **≈±11–13 mT** — *flagged misfit*                                                                                                    | 110–150 mV/mT (130 typ.)                                                                                                          | Response time 1–2 µs                                                                                                     | 10 mV_pp                                                                                                          | not broken out                                                                         | small SMD                                    | not found                    | AKM EQ-730L datasheet (akm.com) [9]                 |

**Sources:**
[1] `allegromicro.com/-/media/files/datasheets/a1308-9-datasheet.ashx`, A1308-9-DS Rev. 15
[2] `ti.com/lit/ds/symlink/drv5055.pdf`, SBAS640C
[3] `infineon.com/dgdl/Infineon-TLE4997E2-DataSheet-v02_10-EN.pdf`, V2.10
[4] `infineon.com/dgdl/Infineon-TLI493D-W2BW-DataSheet-v01_00-EN.pdf`; TLI493D-A2B6 datasheet v1.3 (Mouser-hosted mirror)
[5] `melexis.com/-/media/files/documents/datasheets/mlx90393-datasheet-melexis.pdf`, Rev. 012
[6] Honeywell SS490 series datasheet, doc 005843-2, `automation.honeywell.com`
[7] `allegromicro.com/-/media/files/datasheets/a1391-2-3-5-datasheet.ashx`, 1391-DS Rev. 10
[8] `allegromicro.com/-/media/files/datasheets/a1324-5-6-datasheet.pdf`, A1324-DS Rev. 9
[9] `akm.com/content/dam/documents/products/magnetic-sensor/linear-hall-effect-ic/{eq431l,eq730l}/{eq431l,eq730l}-en-datasheet.pdf`

**Misfits — flagged explicitly (do not use for this application):**
- **AKM EQ-431L (±22–27 mT) and EQ-730L (±11–13 mT)** — both are far too narrow for the 50–500 mT target band originally specified; they're built for fine near-zero-field sensing (proximity/position), not actuator bias-flux measurement.
- **Honeywell SS495A (±60–67 mT)** — barely clips the low end of the target band; excellent speed and tempco, but the narrowest range among sensors that were actually in contention. Worth reconsidering only if the measured field on the real hardware turns out to sit comfortably inside ±60 mT.
- **Allegro A1324/A1325 (±44–50 mT)** — the original vault pick; superseded on bandwidth/noise merits, see §2.

---

## 4. Selection Priority and Recommendation

**Stated priority order for this application** (per the sensing doc's rationale — a Hall sensor whose job is to catch fast-changing flux for saturation/PM-health detection, not a slow calibration instrument):

- **(a) HIGH — repeatability/precision under dynamic conditions:** bandwidth, response time, noise density/resolution, output jitter. A slow or noisy sensor smears exactly the fast transients (saturation onset, PM-drift-vs-hysteresis discrimination) that flux feedback exists to catch (see [[Maglev - Sensing and Flux Feedback]] §2).
- **(b) LOWER — sensor's own temperature coefficient.** PM thermal drift is already tracked as a separate, larger failure mode elsewhere in this vault; the Hall IC's own tempco is a secondary concern, correctable in firmware if characterized.
- **(Implicit gating constraint) FS range must not saturate at the expected operating field.** Confirmed non-binding for the real hardware (§2) — the real field sits well inside every candidate's range — but still worth keeping some headroom margin rather than picking the narrowest part that "just barely" fits.

### Top pick: Allegro A1308LLHLX-05-T

Best bandwidth found (**20 kHz**, tied with DRV5055) while staying within 2× of the lowest noise floor surveyed (0.25 µT/√Hz vs. DRV5055's 0.13 µT/√Hz), plus the widest verified full-scale range of any part surveyed (**≈±390–400 mT**) — comfortable headroom over the real (much lower) measured pole-face field, with room to spare if the design changes later. Simple analog ratiometric output — one ADC channel, no I²C bus contention with other per-corner sensors. SOT-23W package mounts easily on the small in-gap PCB the existing §6 placement calls for. Cheap (~$1.29/unit).

### Runner-up: TI DRV5055A4 (or Z4)

Best noise density of any part surveyed (130 nT/√Hz, ~2× better than the A1308-05) and identical 20 kHz bandwidth / fast 10 µs propagation delay, with a datasheet-published (not back-calculated) linear range spec of **±169 mT** — still comfortable headroom for the real measured field. The **A4 variant** additionally includes on-chip compensation matched to typical NdFeB tempco (0.12 %/°C), which happens to track the PM drift already discussed in [[Maglev - Sensing and Flux Feedback]] §2 — an incidental bonus, not the deciding factor per the stated priority order.

### Notable also-rans

- **Infineon TLE4997E2** — field-programmable range (±50/100/200 mT) and gain, but its digital LP filter caps bandwidth at ~1.3 kHz (vs. 20 kHz for the top two) — a real cost against priority (a).
- **Infineon TLI493D / Melexis MLX90393** (3-axis digital) — valuable if 3-axis stray-field diagnostics are wanted (e.g., detecting the cross-yoke magnetic coupling flagged as a possibility in [[Maglev - Coupling and Geometry]] §5), but both are bandwidth-limited relative to the analog parts (5.8 kHz best case for TLI493D fast mode; ~1 kHz realistic for MLX90393) and have a coarser noise floor (tens-of-µT-class vs. sub-µT-class for the analog parts).

---

## 5. Placement and Installation

[[Maglev - Sensing and Flux Feedback]] §6 currently recommends: *center of pole face, in the gap, sensitive axis perpendicular to the pole face.* This section re-examines that against the alternative of mounting on top of the yoke (outside the working air gap), using AMB/maglev practice as backing.

### 5a. What "pole face" and "center" actually mean (per `Diagram_1.png`)

Per `Diagram_1.png`: each leg is a 1"×1" column — PM (1") sandwiched between two 1018 steel sections (0.5" top cap, 0.5" base transition). Per the vault's convention (pod rides *below* the rail, force is attractive-upward), the working ~3 mm air gap sits between the **top face of the steel cap on each leg** and the rail above it. That top face — the 1"×1" area used as `A` throughout [[Maglev - PM Bias and Force Linearization]] — *is* the pole face. It's defined by its role (it bounds the working gap that produces force), not by "top of the assembly" in some generic sense.

**"Center"** means the geometric centroid of that 1"×1" square, as distinct from a point near one of its four edges or corners.
### 5b. Practical mounting/wiring tradeoffs

- **Space constraint.** The nominal working gap is ~3 mm ([[Maglev - PM Bias and Force Linearization]] §7). A SOT-23W-class Hall IC (≈2–3 mm across the package, sub-mm die) glued to a thin PCB fits inside that gap with headroom to spare, consistent with the existing §6 guidance ("mount easily on a small PCB glued into the gap").
- **Mechanical risk.** A gap-mounted sensor sits directly in the path if the gap closes to zero (touchdown, startup before levitation is established, or a control fault) — it can be struck by the rail. This is a real cost of in-gap placement that on-yoke mounting avoids. Mitigate with a thin protective potting/coating over the sensor and PCB, and by budgeting the sensor's physical standoff into the mechanical touchdown-limit design (a landing gear / snubber stop that keeps the minimum gap above the sensor's package height).
- **Contamination/vibration.** The gap is exposed to dust, debris, and the full vibration environment of the rail interface — worse than a sensor mounted on the yoke body. A conformal coating and a robust adhesive bond (not just friction-fit) are worth the modest extra assembly effort.
- **Cabling.** Fine sensor leads (3-pin) can be routed along the yoke body to the PCB/MCU with normal wire-management practice; this is not meaningfully harder for an in-gap sensor than an on-yoke one — the routing distance is nearly identical, only the last few mm differ.

### 5c. Recommendation

**Confirm the existing guidance: center of pole face, in the gap, sensitive axis perpendicular to the pole face.** The physics argument (§5b/5c) is decisive — an on-yoke sensor trades a small, well-understood mechanical risk (touchdown strike) for a much larger, harder-to-characterize signal-quality problem (leakage flux with an uncertain, geometry-dependent relationship to actual gap force). The mechanical risk is also the cheaper one to mitigate (conformal coating + touchdown-limit stop) versus re-deriving a leakage-to-gap-flux calibration for an on-yoke location. No nuance-driven revision to the existing §6 text is needed beyond the sensor part swap in §2 above.

---

*See also:*
- *[[Maglev - Sensing and Flux Feedback]] — why flux feedback matters, and the §6 placement guidance this doc supports*
- *[[Maglev - PM Bias and Force Linearization]] — derives the PM/steel reluctance network and the bias-point formulas referenced in Appendix A*
- *[[Maglev - Hardware and Implementation]] — MCU/ADC integration notes for per-coil current and Hall sensing*

---

## (Addendum) Original Range-Mismatch Analysis (Superseded by IRL Measurement)

*Kept for reference — the concern below assumed the illustrative B_b ≈ 1.15 T figure from [[Maglev - PM Bias and Force Linearization]] §7 was representative of the real hardware. IRL Gauss-meter testing has since shown the actual pole-face field, even at maximum coil current, is well under that figure, so this is no longer a live design constraint. The bias-tuning methodology below (PM length, shims, gap sizing) remains useful if a future design change pushes the operating field back up, or for anyone sanity-checking the reluctance-network model against a different hardware configuration.*

None of the compact point-sensor Hall ICs surveyed in §3 — including the widest, the A1308LLHLX-05-T at ≈±400 mT — would have comfortably covered a **1.15 T** DC bias without saturating. Two ways to close that gap, both preserved here:

1. **Tune the bias down.** [[Maglev - PM Bias and Force Linearization]] §2 already notes the design tension: "large Φ_b buys linearity but also raises k_s... Don't oversize the magnet — set Φ_b to just meet the linearity target." A lower committed bias (e.g., in the 300–500 mT range) would both ease the linearization requirement's PM sizing *and* bring the operating point within reach of the A1308-05/DRV5055-class sensors.

   **What "tune the bias down" means mechanically, given a fixed magnet grade.** B_r and H_c are material constants of the chosen grade — they don't change. But Φ_b (and therefore B_b = Φ_b/A) is not the magnet's B_r; it's the *loadline* operating point set by the whole series reluctance network, $\Phi_b = \mathcal{F}_{pm}/\mathcal{R}_{total}$ (§4b of the PM Bias doc). That network is a geometry choice, so Φ_b is tunable independent of grade:
   - **Shorten l_pm (less magnet length per leg).** Φ_b rises monotonically with l_pm toward an asymptote of B_r·A as l_pm→∞ (longer magnet ⇒ more MMF *and* more of its own series reluctance, net effect still pushes Φ_b up toward saturation — see the PM Bias doc §4 answer). Shortening it pulls Φ_b back down. **Cost:** shrinking R_pm shrinks R_total, so the gap becomes a *larger* fraction of a *smaller* total — η rises back toward the η=1 (idealized, undiluted) case, which per §4b means a **faster, harder-to-stabilize unstable pole** (the 4.3 Hz pole was the *benefit* of a dominant R_pm). This is the same tension §2 of the PM Bias doc already names, stated as a geometry lever.
   - **Insert a non-magnetic shim/spacer in series with the PM** (not in the working control gap). Adds a controlled, reversible increment of R₀ without cutting the magnet or touching s₀ — mechanically the same effect as shortening l_pm, but tunable with shim stock during a bench characterization pass rather than committed by machining the magnet. Standard practice for trimming bias flux in relay/electromagnet assemblies.
   - **Increase the working gap s₀.** Also raises R_total (R_gap ∝ s₀), lowering Φ_b — but s₀ is load-bearing in every §4b/§7 formula (F₀, k_i, k_s, ω_unstable all move with it), so this isn't an isolated knob; changing it re-derives the whole operating point, not just the bias.
   - **Increase pole face area A.** Spreads the same Φ_b over more area, cutting B_b = Φ_b/A directly without touching the flux value itself. Least practical here since A = 1 in² is fixed by the leg cross-section in `Diagram_1.png`; changing it means redesigning the yoke, not trimming it.

2. **Sense a scaled tap, not the raw pole-face field.** A deliberately undersized secondary air gap or shunt leg elsewhere in the magnetic circuit — sized via the same reluctance-network method already used for the PM/steel/gap budget in [[Maglev - PM Bias and Force Linearization]] §4b/§7 — could present the sensor with a known, safely-scaled fraction of total flux, similar in spirit to how current-transducer shunts scale a large primary current down to a sensor-friendly range. This leaves B_b at the pole face untouched (full force/stability budget preserved) and only changes what the *sensor* sees.

**Grade note (also secondary now):** the worked numbers this appendix is built on assumed **N42** (B_r ≈ 1.3 T). The actual magnet in use is **N52** (B_r typically ≈ 1.42–1.48 T) — which, taken at face value against the reluctance-network model, would predict an even *higher* bias than 1.15 T. That the real measured field is well under 1.15 T regardless suggests the model (§4b/§7 of the PM Bias doc) is overestimating Φ_b relative to the built hardware — possibly unmodeled leakage, joint air gaps between PM and steel, or other non-idealities. That's a model-accuracy question worth a follow-up note in the PM Bias doc, independent of sensor selection (which this IRL data has already resolved).

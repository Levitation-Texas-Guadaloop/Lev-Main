## Laminating steel yokes

Scope: U/C-core electromagnets for a student EMS/HEMS rig. **[S]** = sourced fact (link inline). **[I]** = our inference or back-of-envelope; check it on the bench.

### 0. Our current build: sliced 1018/1020, JB-Welded

**What we have.** The U cross-section is cut from 1" thick 1018/1020 stock. Nine 1" slices are JB-Welded face-to-face to make the 9" depth. Legs are 1" wide with a 1" NdFeB PM in series; the base is 1.5" thick; the track is 0.25" solid steel. (Geometry from [[U-Core Electromagnet Manufacturing Research]] §Project context / LEV-72.)

**Is the orientation right? Yes [I].** The glue planes are parallel to the U profile, so flux runs *within* each slice and never crosses a glue line. That is the correct lamination orientation. Consequences:
- The glue lines add no reluctance.
- The glue lines break eddy loops that would otherwise run the full 9" depth.

**Does 1" count as "laminated"? No: lamination means sub-millimetre, but read the nuance below.**
- **[S] Standard sheet thickness.** Laminations are typically 0.35–0.65 mm (29–24 ga) (§2).
- **[I] Rule of thumb.** Sheet thickness should be ≲ skin depth δ at the highest frequency the control flux carries. For 1018 at μr ≈ 500, δ ≈ 1.3 mm at 50 Hz and ≈ 0.6 mm at 200 Hz. A 25.4 mm slice is 20–40× δ, so each slice behaves as solid steel.
- **[I] What slicing actually bought us.** The eddy loop in a leg is set by its *smaller* cross-section dimension. That was already the 1" leg width, so going from 1"×9" to 1"×1" cells gives only about a 2× improvement in the eddy time constant (the rectangular-bar mode scales with 1/(1/a²+1/b²)). The base (1.5"×9" → 1.5"×1") gains about 3×.
- **[I] What real lamination buys.** 0.5 mm sheets improve that time constant by about 1000×.

#### 0.1 Is 1018/1020 OK?

| Property | 1018/1020 (what we use) | 1008/1010 "dead soft" | NO Si steel (M19 class) | Source |
|---|---|---|---|---|
| Resistivity | 15.9 µΩ·cm (1018); low-C steels ≈ 12 µΩ·cm | ≈ 12 µΩ·cm | ≈ 3–4× higher than mild steel (Si-alloyed) | **[S]** [MatWeb 1018 CD](https://www.matweb.com/search/DataSheet.aspx?MatGUID=3a9cc570fbb24d119f08db22a53e2421), [SMAG Handbook v7 §low-C steels](https://www.magweb.us/wp-content/uploads/2021/08/SMAG-Handook-Version-7.pdf). Si-steel ratio is **[I]**: confirm on the AK DI-MAX sheet |
| Coercivity HcB | ≈ 300 A/m (1020) | ≈ 150 A/m | 40–100 A/m | **[S]** [SMAG Handbook v7 §2.5](https://www.magweb.us/wp-content/uploads/2021/08/SMAG-Handook-Version-7.pdf) |
| Remanence Br | 0.74 T (1020) | 1.25 T | 0.5–0.75 T | **[S]** same |
| 1.5 T permeability | Falls about 10× from 0.005% C to 0.2% C. Annealing recovers at most about 2×. | Higher | High | **[S]** same (Fig. 22) |

**[I] Verdict.**
- **Fine for the DC part.** The PM bias sets most of the flux. In our circuit the iron's reluctance is tiny next to about 60 mm of equivalent air (2×1" PM + 2× working gap). With l_Fe ≈ 330 mm and μr ≈ 500, the iron is about 0.66 mm equivalent, roughly 1% of the total. So 1018's lower permeability costs almost nothing in force or inductance.
- **Hysteresis costs some force-vs-current repeatability.** The hysteresis width in MMF is bounded by about Hc·l_Fe:

  | Material | Hc·l_Fe | Share of 2,550 At control authority |
  |---|---|---|
  | 1020 | ≈ 100 At | about 4% |
  | M19 class | ≈ 17 At | under 1% |

  This is an upper bound, since the large gap shears the loop. It shows up as a small force offset that depends on direction of travel. The integral action in the gap loop mostly absorbs it.
- **Eddy currents are the real cost.** Resistivity is about 3× worse than Si steel and our slices are thick. See §0.2 for how large it actually is.
- **Cheap improvement without changing process:** 1008/1010 or "magnetic iron" bar halves Hc. Keep the same slicing and gluing.

#### 0.2 How big is the eddy penalty for *our* geometry?

**[I] Model.** 1-D slab eddy model: iron reluctance × (x/tanh x), where x = (1+j)·d/(2δ). This is placed in series with the ~63 mm equivalent air/PM path. Inputs: σ = 1/1.59e-7 S/m, l_Fe = 0.33 m, magnitude and phase of gap flux per unit current relative to DC.

| Slice thickness d | μr (incremental, assumed) | 10 Hz | 50 Hz | 200 Hz |
|---|---|---|---|---|
| **25.4 mm (current)** | 200 | −4° / 0.95 | −8° / 0.87 | −14° / 0.75 |
| **25.4 mm (current)** | 500 | −3° / 0.96 | −5° / 0.91 | −10° / 0.82 |
| 3.2 mm (1/8" mild steel) | 200–500 | ≈0° | −0.6° | −1.5 to −2° |
| 1.6 mm (1/16") | 200–500 | 0° | −0.2° | −0.6° |
| 0.76 mm (0.030", SendCutSend's thinnest) | 200–500 | 0° | 0° | −0.1° |

What this says [I]:
1. **The PM bias is protecting us.** The magnetic-bearing results in §1 ("segmenting doubled bandwidth") come from small-gap actuators where iron is a large share of the circuit. In our HEMS the 2" of PM in series dilutes the eddy effect. The current 1" slices probably cost about 5–15° of phase at a 50–200 Hz crossover, not a catastrophic √s roll-off.
2. **The model is optimistic.** It ignores:
   - 2-D eddy paths.
   - Flux crowding at the pole faces.
   - The **0.25" solid track**, which runs near saturation (low incremental μr, bigger share of reluctance) and is itself unlaminated.
   - Any shorted joints (§0.3).

   Treat the table as a floor, not a promise.
3. **"<< 1 inch" is right, but we don't need electrical-steel thinness to get most of the benefit.** Going from 25.4 mm to about 1.6–3.2 mm mild-steel slices removes nearly all of the modeled lag. Going on to 0.35–0.5 mm M19 mainly reduces core *loss* and hysteresis, which matter less in a DC-biased lev magnet.

#### 0.3 JB-Weld joints

- **[S]** J-B Weld states its epoxy is an insulator, not a conductor, despite the steel filler ([J-B Weld FAQ](https://www.jbweld.com/faqs)). So the glue lines should interrupt eddy paths.
- **[I] Things that can silently short slices back into one solid block:**
  - Metal-to-metal contact where the bond line is thin or where burrs touch.
  - **Facing or milling the pole faces after gluing.** Tool smear bridges the joints; this is the same mechanism as the burr shorts in §3.
  - Through-bolts or steel clamp plates without insulating sleeves (§4).
- **[I] Check:** measure resistance between adjacent slices with a meter (a 4-wire meter is ideal). It should read open or MΩ. A few mΩ means the slices are shorted. If the faces were milled after gluing, a light etch or stone across the pole faces restores the breaks.

#### 0.4 Upgrade ladder, cheapest first [I]

| Step | Change                                                                                                                                                                                        | Expected gain                                                                  |
| ---- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| 0    | Measure first: sine-sweep coil current, read gap B with a Hall probe or a search coil on a pole, and plot B/I magnitude and phase vs f. Compare with §0.2.                                    | Tells us whether any of the steps below is worth doing                         |
| 1    | Verify the slice joints are open (§0.3). Insulate any bolts.                                                                                                                                  | Recovers the intended 2–3× if joints are shorted                               |
| 2    | Same process, thinner slices: laser-cut 1/16"–1/8" 1008/1010 U-profiles (SendCutSend 0.030"+). Stack with thin epoxy, not thick JB-Weld beads. About 70–140 pieces per 9" yoke at 1/16"–1/8". | Removes most modelled eddy lag. Hc halves vs 1020                              |
| 3    | Laminate the **track** too, or at least make it thicker (the saturation finding in the sizing doc)                                                                                            | Track is likely the next-largest eddy and saturation contributor               |
| 4    | Real 0.35–0.5 mm M19 / M400-50A laminations from a lamination shop (§5), bonded                                                                                                               | Lowest loss and hysteresis. Only worth it if step 0 shows iron still limits us |

#### 0.5 Step 0 test: measure the eddy lag [I]

![[Pasted image 20260926165713.png|533]]

**Goal.** Measure E(f) = (gap flux per amp at f) ÷ (gap flux per amp at DC) on the real yoke and track. Compare it with §0.2 and `tutorials/eddy_margin_explorer.py`. Block diagram: [Yoke Eddy Bench Test](https://claude.ai/artifact/B3FZp4ggvn5SydP5xfHjWC). https://claude.ai/artifact/B3FZp4ggvn5SydP5xfHjWC?sk=4ES76t3lWM1Wm77B6Q2VrA

**Why a search coil rather than a Hall probe:**
- A search coil (a few turns of wire around the pole tip) outputs V = Nₛ·dΦ/dt for the **whole** pole flux.
- We only need the AC part, so no hardware integrator is needed. Divide by jω in post-processing: Φ = V/(jω·Nₛ).
- A single Hall probe sees local, surface-skin flux. That flux leads the pole average (the eddy caveat in §0.2), so a Hall probe makes the core look faster than it is. Use the Hall only as a cross-check.

**Equipment:**

| Item | Spec | Notes |
|---|---|---|
| Analyzer | 2-ch scope + generator with Bode / network-analyzer mode, or a DAQ + sine script | One box does the sweep and the gain/phase math |
| Drive | Linear/audio power amp, or our H-bridge in current mode if its current loop is ≫ 500 Hz | Needs ~|R + jωL|·I volts. At 1.1 Ω and 2.5 mH, ±1 A at 200 Hz needs ≈ 3.3 V |
| Current shunt Rₛ | 0.05–0.1 Ω, 4-terminal, low-inductance | Read differentially. Shunt inductance adds fake phase at high f |
| Search coil | 10–30 turns fine magnet wire, tight on the pole tip, twisted leads | Put it as close to the gap as possible so leakage flux isn't counted |
| Hall (optional) | Linear, rated ≥ 1 T at the PM bias | Many hobby Halls saturate near 0.1–0.2 T; check the datasheet |
| Fixture | Yoke clamped over the **actual track**, fixed gap set by G10/acrylic shims | Clamp before approach. The PM alone pulls hundreds of N (sizing doc) |

**Procedure:**
1. Clamp the yoke at nominal gap g₀. Use the real track so rail eddies are included.
2. Drive a small sine about 0 A (the PM carries the bias, so we are testing the operating incremental μr). Sweep 1 → 500 Hz at about 20 points per decade.
3. Record I on CH1 and V₂ (search coil) on CH2. Compute Φ/I = V₂/(jω·Nₛ·I), then normalize to the 2 Hz point.
4. Repeat at a second gap and at half the amplitude. The curves should overlay; if they don't, we are not small-signal. Keep runs short so the coil doesn't heat and shift R.
5. **Sanity check with no flux sensor:** the same sweep gives coil impedance Z = V_coil/I. Eddies appear as L_eff falling and R_ac rising with f, which is a second, independent read of the same effect.
6. Optional A/B test: a sliced yoke vs a single solid 1" block, or before and after the §0.3 joint fix.

**Decision.** Read E at the gap-loop crossover (≈10 Hz with the Layer 3 model gains).
- If |E| ≥ 0.95 and ∠E is within about 5°, iron is not the limit, so skip steps 2–4.
- If it is worse, do step 1, then step 2.

### 1. Solid vs laminated vs SMC: what eddy currents do to the loop

| Point                                                                                                                                                                                                                                                                                           | Evidence                                                                                                                                                                                                                                                                          |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| In a solid (non-laminated) actuator the magnetic skin effect causes "a significant lag between the force-generating magnetic flux and the measurable coil current". This substantially damps force in current-controlled systems.                                                               | **[S]** Zhu, Knospe, Maslen, *IEEE Trans. Magn.* 41(4), 2005, cited in [Zhu et al., "A Complete Model for Solid Cylindrical Magnetic Actuators" (Calnetix PDF)](https://www.calnetix.com/sites/default/files/14.pdf)                                                              |
| For a solid actuator in current mode, current stiffness *and* displacement stiffness roll off at half order (√s): F/I ≈ K_i·R0/(c·√s + R0), where c is set by conductivity, permeability and geometry. A laminated model with no eddy term is "accurate only for laminated magnetic actuators". | **[S]** [Zhu et al. (Calnetix PDF)](https://www.calnetix.com/sites/default/files/14.pdf). A follow-up covers **C-shaped** solid actuators specifically: Zhu, Knospe, Maslen, "Frequency domain modeling of non-laminated c-shaped magnetic actuators", ISMB-9, 2004 (cited there) |
| Segmenting a solid stator (six cuts) roughly **doubled actuator bandwidth**.                                                                                                                                                                                                                    | **[S]** Zhu/Knospe/Maslen 2005 abstract, via [search summary](https://www.calnetix.com/sites/default/files/3.pdf). See also [segmented thrust bearings, ISMB-14](https://www.magneticbearings.org/app/uploads/publications/ismb14/ismb14_submission_95.pdf)                       |
| Magnetic-bearing practice: parts that see changing flux are made of insulated laminations, which break up eddy paths. Eddy currents still flow inside each sheet, and performance degrades once skin depth drops below sheet thickness.                                                         | **[S]** [Calnetix, "How magnetic bearings work"](https://www.calnetix.com/sites/default/files/CALNETIX_HOW_MAGNETIC_BEARINGS_WORK.pdf)                                                                                                                                            |
| Low/medium-speed EMS maglev (China) uses **solid Q235 steel** for both rail and levitation electromagnet (σ ≈ 5×10⁶ S/m, B_sat ≈ 1.4 T). Motion-induced rail eddies cut the front magnet's lift by nearly 40% at 160 km/h.                                                                      | **[S]** [Machines 10(6):476 (MDPI)](https://doi.org/10.3390/machines10060476), [Yang, Transp. Syst. Technol.](https://journals.eco-vector.com/transsyst/article/view/10867), [Liang, Transp. Syst. Technol.](https://journals.eco-vector.com/transsyst/article/view/10755/en_US)  |
| Delft Hyperloop (Helios III) runs HEMS vertical + EMS lateral modules. Its page states laminated cores explicitly only for the propulsion motor ("to reduce the eddy-current losses").                                                                                                          | **[S]** [Delft Hyperloop Helios III](https://www.delfthyperloop.nl/our-pods/helios-iii-2024). No public source found stating the lev-magnet core material.                                                                                                                        |
| SMC (Somaloy) is insulated iron powder: μr about 50–500 (Somaloy 1P max ≈ 550), low eddy loss, usable DC–kHz.                                                                                                                                                                                   | **[S]** [Höganäs Somaloy 1P data](https://www.hoganas.com/globalassets/downloads/libary/somaloy_somaloy-1p-material-data_2272hog.pdf), [ISMB-14 SMC review](https://www.magneticbearings.org/app/uploads/publications/ismb14/ismb14_submission_22.pdf)                            |

==**[I] Why a solid yoke hurts current-to-force bandwidth.** Skin depth is δ = √(2/(ωμσ)). With σ = 5×10⁶ S/m and an assumed μr ≈ 1000, δ is about 2.3 mm at 10 Hz, 0.7 mm at 100 Hz and 0.2 mm at 1 kHz. A solid 20–30 mm yoke therefore carries changing flux only in a skin a few mm deep at typical gap-loop frequencies (tens to hundreds of Hz). The inner PI loop **can hold coil current perfectly while gap flux, and so force, lags behind.**== The added phase lag is roughly 45° per unit of the √s term, sitting exactly where the gap loop needs phase margin. Laminating at 0.35–0.5 mm pushes the eddy corner to roughly several hundred Hz to kHz. 
- **Caveat for our HEMS:** the Zhu et al. numbers are for small-gap bearings. With ~2" of PM in series, iron is only about 1% of our circuit reluctance, which dilutes this effect considerably. See §0.2.
**[I] Rail note.** Student tracks are almost always solid steel, so rail eddies remain even with a laminated U-core. At low speed they matter less than yoke eddies, but they set a floor on flux bandwidth.
**[I] SMC in an EMS U-core.** The low μr costs little, because the core's equivalent gap l_core/μr (≈200 mm/500 ≈ 0.4 mm) is small next to a ~10–20 mm total working gap. The real drawbacks are that SMC is brittle, needs press tooling or machined blanks, and saturates lower (see datasheet).

### 2. Grades and thicknesses

| Grade | Thickness | Key data | Notes |
|---|---|---|---|
| M270-35A (≈ AISI M-19, 0.35 mm) | 0.35 mm | P1.5/50 ≤ 2.70 W/kg; J ≥ 1.49/1.60/1.70 T at 2.5/5/10 kA/m; 7.65 kg/dm³ | **[S]** [thyssenkrupp powercore NO range](https://www.thyssenkrupp-steel.com/media/content_1/publikationen/lieferprogramme/thyssenkrupp_product-range_no-electrical-steel_powercore_steel_en.pdf) (equivalence table: M270-35A ↔ IEC 60404-8-4 270-35-A5 ↔ M-19) |
| M400-50A | 0.50 mm | P1.5/50 ≤ 4.00 W/kg; J ≥ 1.53/1.63/1.73 T; 7.70 kg/dm³ | **[S]** same source. Slightly higher J than 35A grades (less Si) |
| M19 / M27 / M36 / M43 (US) | 0.014″, 0.0185″, 0.025″ (29/26/24 ga); thin 0.002–0.007″ | Coatings C-0, C-3 (varnish, no post-anneal), C-4, C-5 (higher-resistance inorganic) | **[S]** [Proto Laminations steel page](http://www.protolam.com/page7.html) |
| Hiperco 50/50A (FeCoV) | e.g. 0.006″ (150 µm) strip | B_sat ≈ 2.4 T (24 kG). **Must** be final-annealed at about 857–871 °C for 2–4 h in dry H₂ or vacuum | **[S]** [Carpenter Hiperco 50A](https://www.carpentertechnology.com/alloy-finder/hiperco-50a), [Springer J. Electron. Mater. 2015](https://link.springer.com/article/10.1007/s11664-015-3990-3), [EFINEA annealing](https://www.efineametals.com/soft-magnetic-alloys/annealing-hiperco-50-50a-and-50-hs-soft-magnetic-alloys/) |

**[I]** M19/M270-35A at 29 ga is the default choice. Hiperco pays off only if you are force-per-mass limited near saturation, and the H₂/vacuum anneal plus cost make it a poor fit for a student team. 0.5 mm M400-50A is fine for sub-kHz flux content.

#### 2.1 Reading grade names, and where our 1018/1020 fits

**"Grade" and "thickness" are two independent choices.**
- **Thickness** sets how large the eddy loops can be. Eddy loss scales with t², and thickness is what fixes the phase lag in §0.2.
- **Grade** is the alloy and how it was processed. It sets resistivity (which scales eddy currents further) and hysteresis (Hc).

| Name you'll see | How to decode it | What it guarantees |
|---|---|---|
| **1018 / 1020** (AISI/SAE) | 10 = plain carbon steel, 18 = 0.18 % C. **[S]** [SMAG Handbook v7](https://www.magweb.us/wp-content/uploads/2021/08/SMAG-Handook-Version-7.pdf) (low-C section) | Chemistry and mechanical properties. **Nothing magnetic.** Bar stock also has no thickness in the lamination sense: it is whatever you slice |
| **M-19, M-27, M-36, M-43** (AISI) | M-number is a core-loss class; lower means lower loss. It is sold by gauge: 29 ga = 0.014″ (0.36 mm), 26 ga = 0.0185″ (0.47 mm), 24 ga = 0.025″ (0.64 mm) | Maximum core loss at a stated B and f, plus a coating class (C-3, C-5). **[S]** [Proto Lam](http://www.protolam.com/page7.html) |
| **M270-35A**, **M400-50A** (EN 10106 / IEC 60404-8-4) | 270 → maximum loss 2.70 W/kg at 1.5 T / 50 Hz. 35 → 0.35 mm. A → non-oriented, fully processed | Maximum loss and minimum polarisation (J) at fixed H. **[S]** [thyssenkrupp](https://www.thyssenkrupp-steel.com/media/content_1/publikationen/lieferprogramme/thyssenkrupp_product-range_no-electrical-steel_powercore_steel_en.pdf) |
| **50W470, 35W300** (Chinese GB, common on marketplaces) | **[I]** Same pattern: 50 → 0.50 mm, 470 → 4.70 W/kg. Confirm on the seller's sheet | Same as EN, if the seller supplies a mill cert |
| **CRML** (cold-rolled motor lamination) | Low-carbon lamination steel without silicon, often supplied semi-processed (the user anneals it) | **[S]** Unannealed 0.018″ CRML is 8–12 W/kg; a decarburising anneal brings it to about 2.6 W/kg ([SMAG v7](https://www.magweb.us/wp-content/uploads/2021/08/SMAG-Handook-Version-7.pdf)) |

**[I] Where 1018/1020 sits.** It is a structural steel that happens to be magnetic.
- Carbon is at the high end for soft magnetics, so Hc is about 300 A/m and permeability is roughly 10× lower than ultra-low-carbon steel (§0.1).
- It has no silicon, so resistivity is 3–4× lower than M-grades.
- None of this is guaranteed lot to lot.

For a DC-biased HEMS core that is acceptable. The upgrade path is to fix **thickness first, then grade**.

#### 2.2 Easy-to-get options, ranked by effort [I unless cited]

| #   | Material                                                      | Where to get it                                                                                                                                                                                                                                                                                                                                                                              | Thickness                   | vs 1018                                                                                            | Catch                                                                                                                                                               |
| --- | ------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------- | -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A   | **1008/1010 cold-rolled sheet** (ordinary "mild steel sheet") | Laser job shops: SendCutSend's thinnest mild steel is 0.030″ ([§5](#5-cheap-low-volume-routes)). McMaster lists 1008 and 1008–1010 low-carbon grades in its steel catalogue. OSH Cut and similar shops also carry it                                                                                                                                                                         | 0.030″–0.125″ (0.76–3.2 mm) | Hc about halves (1010 ≈ 150 A/m **[S]** SMAG). Similar resistivity. Kills most eddy lag at ≤ 1/16″ | You insulate each sheet yourself (thin varnish or epoxy). Laser burr needs deburring (§3). Rust                                                                     |
| B   | **Stock UI transformer laminations**                          | Chinese lamination makers sell standard UI shapes (UI-30 … UI-300) in CRNGO/CRGO, 0.23–0.5 mm, in small quantities **[S]** ([Centersky](https://centersky.en.made-in-china.com/product/qjrxDCmTHakZ/China-Ui-Type-Lamination-Silicon-Steel-for-Transformer-Core.html), [Jirui](https://www.eilaminations.com/UI-Shape-Electrical-Silicon-Steel-Lamination-For-Transformer-pd565457898.html)) | 0.35–0.5 mm                 | Real electrical steel, pre-cut, already U-shaped, insulated                                        | Must find a size whose leg width (≥ 1″) and window fit our coil. About 500 pieces per 9″ stack. Lead time and import. If CRGO, the corners cross the hard axis (§5) |
| C   | **NO silicon-steel sheet, cut to our DXF**                    | Buy sheet (M19 or 50W470 class) from marketplace or mill-cert sellers, then waterjet it or take it to a lamination prototype shop (Proto Lam, Polaris, Lamnow, Thomson; §5). SendCutSend doesn't list it. OSH Cut says it adds materials on request (quote@oshcut.com) **[S]** ([OSH Cut](https://www.oshcut.com/materials))                                                                 | 0.35–0.5 mm                 | Best: Hc 40–100 A/m, resistivity about 3–4× higher                                                 | Sourcing is the hard part. Cutting damage and burr matter at this thickness (§3)                                                                                    |
| D   | **Tape-wound cut C-core**                                     | Magnetic Metals, MK Magnetics, Metglas AMCC (§5)                                                                                                                                                                                                                                                                                                                                             | Tape, typically ≤ 0.3 mm    | Excellent                                                                                          | Stock sizes only. Pole-face geometry and PM mounting need adapting                                                                                                  |

**[I] Recommendation.**
- **Start with A at 1/16″ (1.6 mm) 1008/1010.** It uses vendors we already order from and the same slice-and-glue process with about 16× more pieces (≈ 145 per 9″ yoke). It captures essentially all of the eddy benefit modelled in §0.2 (−0.2° at 50 Hz vs −5 to −8° now), and halves hysteresis.
- **Go to B or C only if** the §0.5 bench test still shows iron-limited lag or hysteresis after A. The thing that is hard to get (silicon) mostly buys core *loss*, which a DC-biased lev magnet barely cares about.
- **Skip for this project:** cobalt-iron (Hiperco), amorphous stacks, and grain-oriented steel in stacked U shapes.

### 3. Cutting methods

| Method | Edge effect | Source |
|---|---|---|
| Laser | Thermal stress and domain changes at the edge. Deterioration reported up to 18 mm from the cut in NO steel. Edge hysteresis loss +10% (longitudinal) to 1.5× (transverse). On 50W350, laser vs shear ΔP1.0/50 ranged −12.6% to −4.1% (laser worse at 1.0 T, roughly equal at 1.5 T). Permeability falls below ~1.3 T. A 750 °C stress-relief anneal recovers properties. | **[S]** [AIP Advances 13, 025360 (2023)](https://pubs.aip.org/aip/adv/article/13/2/025360/2877717/Magnetic-properties-deterioration-of-non-oriented), [Materials (PMC9964751)](https://pmc.ncbi.nlm.nih.gov/articles/PMC9964751/) |
| Punching/shear | Plastic deformation plus burr. Burr is the main source of interlaminar shorts. | **[S]** [Hamzehbahmani et al., IEEE Trans. Magn. (burr, Part I)](https://ieeexplore.ieee.org/document/6571275/) |
| Wire EDM | Among the least damaging. Lower hysteresis loss than mechanical cutting. Preferred for prototypes (laser for volume). | **[S]** [EDM vs mechanical cutting (ResearchGate)](https://www.researchgate.net/publication/283021227_The_effect_of_mechanical_and_electrical_discharge_cutting_technologies_on_the_magnetic_properties_of_non-oriented_silicon_iron_steels), [WEDM parameters, Mater. Today Proc.](https://www.sciencedirect.com/science/article/abs/pii/S2214785321066463) |
| Abrasive waterjet | Very low magnetic deterioration. About 0.3 mm plastic-deformation zone, but no thermal zone. Stacks can be cut multi-layer. | **[S]** [JMMM 254 (2003) 370](https://www.sciencedirect.com/science/article/abs/pii/S030488530200882X), [Materials 17(1):94](https://doi.org/10.3390/ma17010094) |

**Burr penalty. [S]** Large burrs shorting 66 laminations nearly **doubled** total loss at 1.8 T. Even two shorted sheets create measurable extra eddy loss ([Hamzehbahmani et al., Part I/II](https://durham-repository.worktribe.com/output/1317702/eddy-current-loss-estimation-of-edge-burr-affected-magnetic-laminations-based-on-equivalent-electrical-network-part-i-fundamental-concepts-and-fem-modeling)).
**[I]** For a U-core, legs are ≥10–20 mm wide, so a ~0.3–few-mm damaged edge band hurts less than in narrow motor teeth. Deburr before stacking (light file or stone, then re-insulate the edges with varnish). This matters more than which cutting process you pick.

### 4. Stacking, bonding, stacking factor

| Method                                                                         | Eddy/loss effect                                                                                                                                                                                          | Source                                                                                                                                                                                                                                                                                                                                                                        |
| ------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Welding (laser/TIG/MAG seams on stack edge)                                    | The seam forms an electrically connected volume, so local eddy loss rises with seam size. About **+25% core loss with four weld joints**. Thin sheets are more sensitive. Heat also adds residual stress. | **[S]** [Modeling eddy losses of welded laminations](https://www.researchgate.net/publication/311467720_Modeling_of_Eddy_Current_Losses_of_Welded_Laminated_Electrical_Steels), [Stator core welding, JMMM 2020](https://www.sciencedirect.com/science/article/abs/pii/S0304885319328434), [Stress-dependent MEC, Machines 10:1153](https://doi.org/10.3390/machines10121153) |
| Interlocking (punched tabs)                                                    | Local shorts slightly raise eddy loss.                                                                                                                                                                    | **[S]** [Wikipedia: Stacking factor](https://en.wikipedia.org/wiki/Stacking_factor) (secondary); [stacking-process eddy study](https://www.researchgate.net/publication/269269292_Investigations_of_eddy_current_losses_in_laminated_cores_due_to_the_impact_of_various_stacking_processes)                                                                                   |
| Bonding varnish (Backlack; thyssenkrupp stabolit/stabosol; voestalpine isovac) | Full-surface bond with no shorts. Heat and pressure cure a B-stage coat. thyssenkrupp lists a "higher stacking factor" among its benefits. Store below 40 °C, ≤6 months.                                  | **[S]** [thyssenkrupp powercore brochure](https://www.thyssenkrupp-steel.com/media/content_1/publikationen/lieferprogramme/thyssenkrupp_product-range_no-electrical-steel_powercore_steel_en.pdf), [voestalpine isovac](https://www.voestalpine.com/isovac/en/Products/Insulating-varnish-systems)                                                                            |
| Epoxy glue / glue dots, oven cure                                              | Prototype route after laser/EDM. Needs no interlocks or welds.                                                                                                                                            | **[S]** vendor: [Lamnow prototyping](https://lamnow.com/prototype-motor-laminations-process-advantages-application/)                                                                                                                                                                                                                                                          |
| Through-bolts + clamp plates                                                   | Bolts through holes can cut the insulation and short the stack. Insulating sleeves and insulated pressing plates prevent the bolt/plate eddy loop.                                                        | **[S]** [US 6949858 insulated core stud](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/6949858), [ScienceDirect: stator cores](https://www.sciencedirect.com/topics/engineering/stator-cores)                                                                                                                                                              |

**Stacking factor. [S]** It is defined as steel volume over stack volume, measured per [IEC 60404-13:2018](https://webstore.iec.ch/en/publication/32477). Vendor figures: bonded stacks above 97%, and roughly 0.97 at 0.65 mm vs about 0.92 at 0.18 mm ([search summary / vendor](https://www.jvfengtech.com/news/industry-news/how-does-the-thickness-and-stacking-factor-of-laminations-in.html); treat as indicative).
**[I]** Plan on 0.95 for a hand-glued 0.35 mm stack and 0.93 if varnish is thick. Stacking factor reduces effective iron area, but in an air-gap-dominated EMS circuit it mainly lowers the saturation margin, not the inductance.
**[I] Student recipe.** Stack with C-5 or varnished sheets and a thin epoxy. Clamp between non-magnetic (aluminium/G10) end plates. Where bolts pass through, use nylon/G10 sleeves and washers so the bolt plus the two plates never close a conductive turn around the flux. Avoid edge welds, or put at most one on the outside of the back iron, parallel to the flux.

### 5. Cheap low-volume routes

| Route | Facts | Source |
|---|---|---|
| Tape-wound cut C/U cores | Stock mandrels, "almost any size" without tooling. Materials include Microsil (GO Si steel), Co-Fe, amorphous, Ni-Fe. | **[S]** [Magnetic Metals cut cores](https://www.magneticmetals.com/products-materials/tape-wound-cut-cores/), [MK Magnetics](https://www.mkmagnetics.com/products/tape-wound-soft-magnetic-cores/) |
| Metglas AMCC U-U cut cores | B_sat 1.56 T, much lower loss than CRGO. Sold as U-U pairs, multi-cut and blocks. | **[S]** [Proterial AMCC datasheet](https://www.india.proterial.com/images/products/pdf/C-Core-A3-Fold-Double-Side.pdf) |
| Laser lamination job shops | Polaris quotes DXF/DWG within one business day, stocks electrical steels, and ships welded or bonded prototype stacks. Proto Lam stocks M19–M43 at 29/26/24 ga. | **[S]** [Polaris prototype](https://www.polarislaserlaminations.com/prototype.html), [Proto Lam](http://www.protolam.com/page7.html), [Thomson Lamination prototyping](https://www.tlclam.net/capabilities/prototyping-services/) |
| SendCutSend | **No electrical/silicon steel listed.** Thinnest mild steel (A36/1018/1008) is 0.030″ (0.76 mm). | **[S]** [SendCutSend steel](https://sendcutsend.com/materials/laser-cut-steel/), [Endless-Sphere thread](https://endless-sphere.com/sphere/threads/laser-cut-silicon-steel-laminate.121019/) |

**[I]**
- **Half a C-core pair.** One half of a tape-wound GO C-core pair is already a laminated U-core, with the tape running along the flux path. The rail replaces the other half. This is probably the cheapest high-quality option if a stock size fits your pole-face area and window.
- **Grain-oriented steel in stacked U-laminations.** GO steel is poor in stacked U-shaped laminations, because flux turns 90° at the corners and crosses the hard direction. Use NO (M19) for stamped/laser U shapes, and GO only in wound cores.
- **Mild-steel sheets as a fallback.** 0.76 mm SendCutSend mild steel, varnished and stacked, is still far better than a solid block: eddy loss scales about with t², so 0.76 mm vs a 25 mm solid leg is roughly 1000× lower. It is still worse than 0.35 mm Si steel, because mild steel has about 2–3× the conductivity of M19 and more hysteresis.

### 6. Split U-cores and joint gaps

| Fact | Source |
|---|---|
| Straight-cut cores of 0.5–2 lb typically have about **0.001″ (25 µm)** residual gap per joint. Lapping gets about 0.0005″, at significant extra cost. A 45°/60° angled cut reduces gap-related magnetizing current by about 30%/50%. | **[S]** [Magnetic Metals A-Core](https://www.magneticmetals.com/products-materials/a-core/) |
| Butt joints in large machines are about 0.05 mm (Stoll, 1976). Model them as equivalent gaps in FEM. | **[S]** [JMAG engineer's diary #73](https://www.jmag-international.com/engineers_diary/073/) |

**[I] Joint penalty in EMS.** Two joints at 25–50 µm each add 0.05–0.1 mm of series gap. Against a total working gap of 2×(5–10) mm, that is about 0.25–1% extra reluctance, so it is negligible for force and inductance. In HEMS the PM thickness adds several more mm of "gap", which dilutes it further. What actually hurts:
- (a) **Lamination orientation at the joint.** If a bolted-on pole piece has its sheets rotated so flux must cross lamination planes, each insulating layer becomes a gap, and eddy currents flow in the plane you did not laminate.
- (b) **Rough or dirty faces.** Paint, burrs or a 0.2 mm shim turn the joint into a real 1–2% gap.
- (c) **A solid bolt-on pole piece** reintroduces the solid-core √s lag locally. Make pole pieces laminated in the same plane as the yoke, or accept the lag and measure it with an L(x,f) sweep.

### 7. Manufacturing Integration with Frame

With laminations, tapping into a yoke (to bolt with L-bracket as we currently do) is challenging. Thread pitch will be bigger than each sheet -- bad quality and alignment issues will arise.

**Alternatives:**
1. **Non-magnetic end clamp plates.** Put an aluminium or G10 plate on each end of the 9″ stack, held by insulated through-rods, and tap your mounting holes into the plates. This is standard lamination practice (§4), and the plates also hold the stack together so the glue isn't the only structure. Use insulating sleeves on the rods, or G10 plates, so the rods and plates can't form a loop around the legs.
2. **Solid end caps.** Keep a 1″ solid 1018 slice at each end, tap it as in your drawing, and laminate the middle 7″ (about 112 sheets). The changing control flux prefers the laminated middle, so the two solid ends add only a little lag. This is the least change from what you have now.

### Sources
- Centersky UI-type silicon-steel laminations: https://centersky.en.made-in-china.com/product/qjrxDCmTHakZ/China-Ui-Type-Lamination-Silicon-Steel-for-Transformer-Core.html
- Jirui UI-shape silicon-steel laminations: https://www.eilaminations.com/UI-Shape-Electrical-Silicon-Steel-Lamination-For-Transformer-pd565457898.html
- OSH Cut materials / special requests: https://www.oshcut.com/materials
- MatWeb, AISI 1018 cold drawn (resistivity): https://www.matweb.com/search/DataSheet.aspx?MatGUID=3a9cc570fbb24d119f08db22a53e2421
- MagWeb SMAG Handbook v7, Properties of Soft Magnetic Materials (Hc, Br, low-C permeability & resistivity): https://www.magweb.us/wp-content/uploads/2021/08/SMAG-Handook-Version-7.pdf
- J-B Weld FAQ (insulator): https://www.jbweld.com/faqs
- Zhu, Knospe, Maslen, "A Complete Model for Solid Cylindrical Magnetic Actuators": https://www.calnetix.com/sites/default/files/14.pdf
- Zhu, Knospe, Maslen, IEEE/ASME T-Mech 15(1) 2010 (Calnetix): https://www.calnetix.com/sites/default/files/3.pdf
- Segmented magnetic thrust bearings, ISMB-14: https://www.magneticbearings.org/app/uploads/publications/ismb14/ismb14_submission_95.pdf
- Calnetix, How magnetic bearings work: https://www.calnetix.com/sites/default/files/CALNETIX_HOW_MAGNETIC_BEARINGS_WORK.pdf
- Influence and Suppression of Eddy Current Effect on EMS Maglev Suspension, Machines 10(6):476: https://doi.org/10.3390/machines10060476
- Yang, eddy current in rail for medium/low speed maglev: https://journals.eco-vector.com/transsyst/article/view/10867
- Liang, eddy current in maglev rail and electromagnet design: https://journals.eco-vector.com/transsyst/article/view/10755/en_US
- Delft Hyperloop Helios III: https://www.delfthyperloop.nl/our-pods/helios-iii-2024
- Höganäs Somaloy 1P data: https://www.hoganas.com/globalassets/downloads/libary/somaloy_somaloy-1p-material-data_2272hog.pdf
- SMC review, ISMB-14: https://www.magneticbearings.org/app/uploads/publications/ismb14/ismb14_submission_22.pdf
- thyssenkrupp powercore NO product range: https://www.thyssenkrupp-steel.com/media/content_1/publikationen/lieferprogramme/thyssenkrupp_product-range_no-electrical-steel_powercore_steel_en.pdf
- Proto Laminations lamination steel: http://www.protolam.com/page7.html
- Carpenter Hiperco 50A: https://www.carpentertechnology.com/alloy-finder/hiperco-50a
- Effect of processing of Hiperco 50 laminates, J. Electron. Mater. 2015: https://link.springer.com/article/10.1007/s11664-015-3990-3
- EFINEA, annealing Hiperco: https://www.efineametals.com/soft-magnetic-alloys/annealing-hiperco-50-50a-and-50-hs-soft-magnetic-alloys/
- Magnetic properties deterioration of NO steel due to laser cutting, AIP Advances 13:025360: https://pubs.aip.org/aip/adv/article/13/2/025360/2877717/Magnetic-properties-deterioration-of-non-oriented
- Laser cutting parameters on 50W350, Materials (PMC9964751): https://pmc.ncbi.nlm.nih.gov/articles/PMC9964751/
- Hamzehbahmani et al., edge-burr eddy loss Part I (IEEE): https://ieeexplore.ieee.org/document/6571275/ ; repository: https://durham-repository.worktribe.com/output/1317702/eddy-current-loss-estimation-of-edge-burr-affected-magnetic-laminations-based-on-equivalent-electrical-network-part-i-fundamental-concepts-and-fem-modeling
- Mechanical vs EDM cutting of NO Si-Fe: https://www.researchgate.net/publication/283021227_The_effect_of_mechanical_and_electrical_discharge_cutting_technologies_on_the_magnetic_properties_of_non-oriented_silicon_iron_steels
- WEDM cutting parameters, Mater. Today Proc.: https://www.sciencedirect.com/science/article/abs/pii/S2214785321066463
- Abrasive waterjet on NO steels, JMMM 254 (2003): https://www.sciencedirect.com/science/article/abs/pii/S030488530200882X
- AWJ multilayer cutting of electrical steel, Materials 17(1):94: https://doi.org/10.3390/ma17010094
- Modeling eddy losses of welded laminations: https://www.researchgate.net/publication/311467720_Modeling_of_Eddy_Current_Losses_of_Welded_Laminated_Electrical_Steels
- Effects of stator core welding, JMMM: https://www.sciencedirect.com/science/article/abs/pii/S0304885319328434
- Stress-dependent MEC for welding, Machines 10:1153: https://doi.org/10.3390/machines10121153
- Eddy losses vs stacking processes: https://www.researchgate.net/publication/269269292_Investigations_of_eddy_current_losses_in_laminated_cores_due_to_the_impact_of_various_stacking_processes
- voestalpine isovac insulating/bonding varnish: https://www.voestalpine.com/isovac/en/Products/Insulating-varnish-systems
- Lamnow prototype laminations (vendor): https://lamnow.com/prototype-motor-laminations-process-advantages-application/
- US 6949858, insulated core stud: https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/6949858
- ScienceDirect Topics, stator cores: https://www.sciencedirect.com/topics/engineering/stator-cores
- IEC 60404-13:2018: https://webstore.iec.ch/en/publication/32477
- Stacking factor (Wikipedia, secondary): https://en.wikipedia.org/wiki/Stacking_factor
- Jufeng, thickness vs stacking factor (vendor): https://www.jvfengtech.com/news/industry-news/how-does-the-thickness-and-stacking-factor-of-laminations-in.html
- Magnetic Metals tape-wound cut cores: https://www.magneticmetals.com/products-materials/tape-wound-cut-cores/
- Magnetic Metals A-Core (cut-core gap): https://www.magneticmetals.com/products-materials/a-core/
- MK Magnetics tape-wound cores: https://www.mkmagnetics.com/products/tape-wound-soft-magnetic-cores/
- Proterial Metglas AMCC cut cores: https://www.india.proterial.com/images/products/pdf/C-Core-A3-Fold-Double-Side.pdf
- Polaris Laser Laminations prototype: https://www.polarislaserlaminations.com/prototype.html
- Thomson Lamination prototyping: https://www.tlclam.net/capabilities/prototyping-services/
- SendCutSend steel materials: https://sendcutsend.com/materials/laser-cut-steel/
- Endless-Sphere, laser-cut silicon steel thread: https://endless-sphere.com/sphere/threads/laser-cut-silicon-steel-laminate.121019/
- JMAG engineer's diary #73, butt joints: https://www.jmag-international.com/engineers_diary/073/


## Appendix

**Flux-sensing to compensate eddy loss**:
  
> "**[I] Why a solid yoke hurts current-to-force bandwidth.** Skin depth is δ = √(2/(ωμσ)). With σ = 5×10⁶ S/m and an assumed μr ≈ 1000, δ is about 2.3 mm at 10 Hz, 0.7 mm at 100 Hz and 0.2 mm at 1 kHz. A solid 20–30 mm yoke therefore carries changing flux only in a skin a few mm deep at typical gap-loop frequencies (tens to hundreds of Hz). The inner PI loop can hold coil current perfectly while gap flux, and so force, lags behind. "  
  
> If we use flux (hall-effect-based) in the control loop, does that allow us to compensate for eddy losses? Intuitively, we can meet magntiude requirement but the phase lag will persist as a function of electrical properties, inertia, eddy, etc ??

-- 

Yes. A flux loop removes the phase lag as well as the magnitude loss, up to that loop's bandwidth. Your intuition is half right: the inertia stays, but the eddy lag doesn't have to.

**Why the lag isn't permanent:**

- The eddy effect is a dynamic, like a lossy inductor, not a fixed time delay.
- If an inner loop drives coil voltage to make _measured_ flux track a flux command, the eddy dynamics sit inside that loop. The loop corrects for them the same way the current loop corrects for L/R.
- Up to the flux-loop bandwidth, flux follows the command in both magnitude and phase.

**What it costs:**

- Near crossover the driver has to push harder, by roughly a factor of 1/|E|, to overcome the eddy currents fighting the change. That uses voltage headroom and adds some eddy heating.
- Above the flux-loop bandwidth, the lag comes back.

**What persists is inertia, and that isn't a lag to compensate.** The m·s² term is the plant itself, and the outer gap loop still has to deal with it.

**There's a bonus.** Force is F = φ²/(μ₀A). If flux is held fixed, force no longer depends on the gap, so ideally the negative stiffness k_s disappears. The unstable plant k_i/(m s² − k_s) becomes a double integrator. That follows from the force law above. In practice, how closely you get there depends on flux-loop bandwidth and sensor accuracy.

**Sensor caveats:**

- **Placement.** The eddy currents make flux uneven across the pole face. A single Hall sensor near the surface sees the skin flux, which leads the flux in the middle. It can make the loop look faster than the total force really is.
- **Range.** The magnet's DC bias flux is large, so the Hall sensor needs enough range to measure it without saturating.
- **Drift.** Hall sensor readings drift with temperature.
- **A common fix:** add a search coil wound around the pole. It measures the total flux change well at high frequency but drifts at DC. Pair it with the Hall sensor for DC.

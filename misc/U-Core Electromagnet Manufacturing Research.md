# U-Core Electromagnet Manufacturing Research

Mechanical/manufacturing research for the HEMS U-yokes: lamination, yoke sizing, coil impregnation, winding & slide-on bobbins, and bobbin materials (incl. 3D printing). E-cores deliberately out of scope. Compiled 2026-09-26.

Tags used throughout: **[S] / sourced** = backed by the cited source; **[I] / inference** = our engineering judgement.

## TL;DR — recommendations for our U-core build

1. **Slide-on bobbin is fine and has prior art.** Transrapid's production patent (US6584671) uses a plastic winding body that can be wound off-core and mounted. No source shows a magnetic penalty. The real costs are lost window area, the hub collapsing under winding tension, and retaining the coil. → §Winding
2. **Make the U separable so pre-wound coils can go on.** Use bolt-on/doweled pole shoes (which also retain the coil axially) or a two-piece cut core. Joint gaps (~12–50 µm) add <1% reluctance next to our ~60 mm equivalent air path (PMs + working gaps) [I]. → §Lamination §6, §Sizing, §Winding §3
3. **Replace the 1/4" acrylic bobbin.** PMMA is rated 82 °C continuous, is notch-brittle, and is attacked by acetone/MEK/xylene. It can't survive a varnish or epoxy bake. It also eats ~30–40% of the usable window. Target 1.5–2 mm walls [I].
   - Hobby-printer tier: **PA6-GF** (HDT ~158 °C), or PAHT-CF after a 500 V megger check.
   - Better tier: ULTEM / PPS-CF.
   - Non-printed: machined G10/FR4.
   → §Bobbin materials
4. **Impregnate with a room-temp or ≤65 °C epoxy**, either vacuum-only or wet-wound, unless the bobbin can take a hot bake. Low-viscosity resin penetrates the winding; filled "thermally conductive" pots (27k–60k cP) don't. Check **Tg**, not just the "service range". → §Impregnation
5. **Laminate the yoke.** Solid steel causes force (not current) to lag, via eddy currents; this is a half-order roll-off that eats phase margin in the gap loop. Use 29-ga M19 (C-5 coat) or M400-50A. Bond with varnish or epoxy (not welds). Insulate any through-bolts. Deburr. → §Lamination
6. **⚠ Track saturation.** A 0.25" track runs at ~4× gap flux density (1.3–1.9 T at the required flux), which caps each yoke near 430–620 N versus 517–677 N required. Rule: track ≥ pole width × B_gap / 1.5 T, i.e. ≥ 0.5". → §Sizing
7. **⚠ Check the Maple force law.** It may be off by a factor ~(½ − η) if flux is allowed to vary with gap inside the derivative. Verify with nonlinear-B-H Ansys before sizing from the LEV-72 mass table. → §Sizing

**Evidence gaps:**
- No student Hyperloop team publicly documents its levitation core material, its winding process, or its bobbin material with thermal data. Prior art comes mostly from Transrapid patents, CERN magnet-school notes, and supplier guides.
- MDPI/ResearchGate were blocked for several sources.

---

## Project context

Everything here comes from the repo, the Obsidian vault, and git history. It is not web research. Tags: **[repo]** means stated in a project file. **[derived]** means our own arithmetic on repo numbers. **[reported]** means the coordinator told us and we could not find it in the repo.

### Two hardware scales. Don't mix their numbers.

| | Small dual-yoke test rig | Full-scale "big yoke" (pod) |
|---|---|---|
| Source | `Vault/guadaloop_lev_control/lev_sim/SIM_REALISM_HANDOFF.md`, `ReadMe.md` [repo] | `Vault/Magnetic-Circuit-Model/LEV-72-mechanical-dimensions-and-specs.md`, `reluctance_model.py` (port of `full_hems.mw`) [repo] |
| Supported mass | 10.52 kg pod, 2 yokes × 2 coils | 211–276 kg pod on 4 yokes, i.e. **517–677 N per yoke** [derived] |
| Target gap | 11.86 mm | **6–8 mm** recommended equilibrium gap |
| Coil electrical | R = 1.1 Ω, L = 2.5 mH (sim), 12 V, ±10.2 A clamp. LCR reading: L ≈ 2 mH at gap = ∞ (`Maglev Actuator Characterization.md`) | N = 250 (Maple `NN`). Maple `Mmf = 2(PM − N·i)` implies N turns **per leg**. The worksheet's demo uses ±16 A |
| Force data | Ansys Maxwell sweep `Ansys Results 12-9.csv`. At 0 A: 103 N at 6 mm, 45.6 N at 12 mm, per yoke | Maple linear reluctance model only. No FEM or measurement of this yoke found in the repo |

The digital twin (`MAGLEV_DIGITALTWIN_PYTHON/parameters.py`: 2.2 Ω, 5 mH, 30 A) and `tutorials/maglev/params.py` (N = 250, 2 Ω, 5 A, 24 V, 1 in² pole, s0 = 3 mm, from git `HEAD~1`) both say they use **illustrative** values. Don't use them for hardware sizing.

### Big-yoke geometry [repo, from `YokeGeometry` defaults and LEV-72]

- **Topology:** U-shaped **solid 1018 steel** yoke. One **1"-long NdFeB PM per leg**, sitting in series in the leg (H_c = 11 kOe, about N52; μ_rec = 1.05). A coil is wound on the legs. Flux closes through a steel track (rail). It is PM-biased and designed for "zero-power" hover (`Maglev - PM Bias and Force Linearization.md`).
- **Cross-section:** legs/poles are 1" wide. The base is 5" long × 1.5" high. Each leg has 1" of PM plus 1" of steel above the base in the model. The diagram shows 0.5" of steel, which is an unreconciled quirk noted in `reluctance_model.py`. The track is **0.25" thick** in the model.
- **Depth (`ydepth`):** the forcing table uses 6". The **built yoke is 9" deep**: 5" × 3.5" × 9", **14 kg**, with 2 mounting holes per face for L-brackets. LEV-72 asks mechanical teams to reserve space for the 9" yoke.
- **Pole-face area per pole:** 6" gives 3.87 × 10⁻³ m². 9" gives 5.81 × 10⁻³ m² [derived].
- **Mass check [derived]:** steel volume is 5×1.5×9 + 2×(1×1×9) = 85.5 in³, about 11.0 kg. PMs are 2×(1×1×9) in³, about 2.2 kg. Together about 13.2 kg, which matches the quoted 14 kg. So the 3.5" height includes 1" of steel above each PM, as the model has it.
- **Coil window [derived, confirm on CAD]:** 5" − 2×1" legs gives a **3" (76.2 mm) wide** window. 3.5" − 1.5" base gives a **2" (50.8 mm) high** window. The two leg coils share it, so each gets about 38 mm of radial build before clearance.
- **Envelope:** the net box per yoke is 7" × 5.5" × 15". That includes a shielding box (+2" per side during transport) and a gap sensor 4" away (LEV-72).

### Current bobbin [reported]

The coordinator reports a **1/4" (6.35 mm) acrylic (PMMA) bobbin, laser-cut and assembled**. No bobbin, wire gauge, or turn-count record for the big yoke was found in the repo. Section 02 estimates how much window this bobbin costs.

### Team constraints [repo]

- **Size:** five people, one stream each (`levitation-candidate-review-v2.md`). **S6, "Magnet manufacture + yoke shielding"**, owns PM grade, potting/retention, and shielding (`Maglev - Magnet Manufacture and Shielding.md`, currently a stub). **S5** owns rig mechanical work.
- **Shop access:** Tormach CNC, lathe, bandsaw, laser cutter, angle grinder, rivet gun, Prusa/Ender FDM printers, and Onshape (S5 owner's listed skills, `levitation-candidate-review-v2.md`). Ansys Maxwell is in use.
- **Priorities:** "BUILD SHIELDING FOR BIG YOKE" is goal #1 (`levitation-candidate-context.md`). E-cores are out of scope, per the brief.
- **Open modelling issues already flagged in the vault:**
  - Measured L ≈ 2 mH is inconsistent with μ_rec = 1.05.
  - Leakage and saturation at the pole faces have not been checked.
  - Solid-steel eddy lag is unmeasured. `L(x, f)` is meant to "decide laminated vs. solid vs. SMC yoke" (`Maglev Actuator Characterization.md`, `Levitation Research Claude.md`).

### Sources

- `Vault/Magnetic-Circuit-Model/LEV-72-mechanical-dimensions-and-specs.md`
- `Vault/Magnetic-Circuit-Model/reluctance_model.py`, `Vault/Magnetic-Circuit-Model/CLAUDE.md`
- `Vault/guadaloop_lev_control/lev_sim/SIM_REALISM_HANDOFF.md`, `Vault/guadaloop_lev_control/ReadMe.md`, `Vault/guadaloop_lev_control/lev_sim/Ansys Results 12-9.csv`
- `Vault/guadaloop_lev_control/MAGLEV_DIGITALTWIN_PYTHON/parameters.py`
- `git show HEAD~1:maglev/params.py` (deleted `tutorials`-era params)
- `Vault/docs/rfcs/knowledge/Maglev - PM Bias and Force Linearization.md`, `Vault/docs/rfcs/streams/Maglev Actuator Characterization.md`, `Vault/docs/rfcs/streams/Maglev - Magnet Manufacture and Shielding.md`, `Vault/docs/rfcs/Levitation Research Claude.md`
- `levitation-candidate-context.md`, `levitation-candidate-review-v2.md`

---

## Laminating steel yokes

Scope: U/C-core electromagnets for a student EMS/HEMS rig. **[S]** = sourced fact (link inline). **[I]** = our inference or back-of-envelope; check it on the bench.

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

**[I] Why a solid yoke hurts current-to-force bandwidth.** Skin depth is δ = √(2/(ωμσ)). With σ = 5×10⁶ S/m and an assumed μr ≈ 1000, δ is about 2.3 mm at 10 Hz, 0.7 mm at 100 Hz and 0.2 mm at 1 kHz. A solid 20–30 mm yoke therefore carries changing flux only in a skin a few mm deep at typical gap-loop frequencies (tens to hundreds of Hz). The inner PI loop can hold coil current perfectly while gap flux, and so force, lags behind. The added phase lag is roughly 45° per unit of the √s term, sitting exactly where the gap loop needs phase margin. Laminating at 0.35–0.5 mm pushes the eddy corner to roughly several hundred Hz to kHz.
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

| Method | Eddy/loss effect | Source |
|---|---|---|
| Welding (laser/TIG/MAG seams on stack edge) | The seam forms an electrically connected volume, so local eddy loss rises with seam size. About **+25% core loss with four weld joints**. Thin sheets are more sensitive. Heat also adds residual stress. | **[S]** [Modeling eddy losses of welded laminations](https://www.researchgate.net/publication/311467720_Modeling_of_Eddy_Current_Losses_of_Welded_Laminated_Electrical_Steels), [Stator core welding, JMMM 2020](https://www.sciencedirect.com/science/article/abs/pii/S0304885319328434), [Stress-dependent MEC, Machines 10:1153](https://doi.org/10.3390/machines10121153) |
| Interlocking (punched tabs) | Local shorts slightly raise eddy loss. | **[S]** [Wikipedia: Stacking factor](https://en.wikipedia.org/wiki/Stacking_factor) (secondary); [stacking-process eddy study](https://www.researchgate.net/publication/269269292_Investigations_of_eddy_current_losses_in_laminated_cores_due_to_the_impact_of_various_stacking_processes) |
| Bonding varnish (Backlack; thyssenkrupp stabolit/stabosol; voestalpine isovac) | Full-surface bond with no shorts. Heat and pressure cure a B-stage coat. thyssenkrupp lists a "higher stacking factor" among its benefits. Store below 40 °C, ≤6 months. | **[S]** [thyssenkrupp powercore brochure](https://www.thyssenkrupp-steel.com/media/content_1/publikationen/lieferprogramme/thyssenkrupp_product-range_no-electrical-steel_powercore_steel_en.pdf), [voestalpine isovac](https://www.voestalpine.com/isovac/en/Products/Insulating-varnish-systems) |
| Epoxy glue / glue dots, oven cure | Prototype route after laser/EDM. Needs no interlocks or welds. | **[S]** vendor: [Lamnow prototyping](https://lamnow.com/prototype-motor-laminations-process-advantages-application/) |
| Through-bolts + clamp plates | Bolts through holes can cut the insulation and short the stack. Insulating sleeves and insulated pressing plates prevent the bolt/plate eddy loop. | **[S]** [US 6949858 insulated core stud](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/6949858), [ScienceDirect: stator cores](https://www.sciencedirect.com/topics/engineering/stator-cores) |

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

### Sources
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

---

## Sizing the U-core yoke

**Legend:** **[src]** means a cited source. **[derived]** means our arithmetic on the repo's big-yoke numbers (see Context). **[inference]** means engineering judgement that needs checking in Ansys or on the bench.

### 2.1 Rules the design has to respect

| Rule | Value | Source |
|---|---|---|
| Pole force (per pole face) | F = B²A / 2μ₀ | [Wikipedia, Electromagnet](https://en.wikipedia.org/wiki/Electromagnet) |
| Practical steel ceiling | "around 1.6 to 2 teslas", about 1 MPa maximum magnetic pressure | [Wikipedia, Electromagnet](https://en.wikipedia.org/wiki/Electromagnet) |
| Design flux limit in the iron | Keep iron B **< 1.5 T** and iron reluctance under "a few per cent" of the air-gap reluctance | [Zickler, CAS, arXiv:1103.1119 §4.2](https://arxiv.org/pdf/1103.1119) |
| Low-carbon steel knee | Begins to saturate around 1.5 T. μ approaches 1 above about 2 T | [Sanfilippo, CAS 2024, arXiv:2602.19808](https://arxiv.org/pdf/2602.19808) |
| Choke points | Back-irons where flux turns sharply, converging paths, sharp corners, sudden narrowing. One saturated section drags down the whole circuit | [Dexter Magnetics, *Electromagnet Design Considerations*](https://www.dextermag.com/wp-content/uploads/2023/07/Electromagnet-Design-Considerations_2022rev-6-23-23-2-1.pdf) |
| Pole-end chamfers | Help prevent saturation at pole ends | [Sanfilippo](https://arxiv.org/pdf/2602.19808) |
| Air-cooled current density | ≤ **1 A/mm²** for voluminous coils enclosed in the yoke; small, thin coils < 2 A/mm² | [Zickler §4.6.1](https://arxiv.org/pdf/1103.1119) |
| Same, second source | Below 1 A/mm² needs no forced cooling | [Sanfilippo §5.3.3](https://arxiv.org/pdf/2602.19808) |
| Fill factor | 0.63 for round wire, 0.8 for rectangular. Packing factor 0.6–0.8 | [Zickler §4.6.1, §5](https://arxiv.org/pdf/1103.1119) |
| Coil aspect ratio | Height : width between 1:1 and 1:2 | [Zickler §5](https://arxiv.org/pdf/1103.1119) |
| Fringing (McLyman) | F = 1 + (g/√A)·ln(2h/g), where h is the window height | [Encyclopedia Magnetica](https://e-magnetica.pl/doku.php/flux_fringing_factor) |
| Solid vs laminated | Solid yokes "cannot be cycled or pulsed rapidly" | [Zickler §4.4](https://arxiv.org/pdf/1103.1119) |

### 2.2 Force → required gap flux density [derived]

Each U-core has two pole faces in series. That gives F_yoke = B_g²·A_pole/μ₀, with A_pole = 1" × depth. The load is 211–276 kg on 4 yokes (LEV-72), i.e. 517–677 N per yoke.

| Depth | A_pole | B_g needed for 517 N | B_g needed for 677 N | Magnetic pressure |
|---|---|---|---|---|
| 6" | 3.87e-3 m² | 0.41 T | 0.47 T | about 70–88 kPa |
| 9" (built) | 5.81e-3 m² | 0.34 T | 0.38 T | about 45–58 kPa |

That is well below the 1.5 T iron limit, so **the poles are not force-limited**. The face area is large because a 6–8 mm gap takes a lot of MMF per tesla: NI_gap = B·2g/μ₀ ≈ 4,900 At at 0.44 T and 7 mm. Pole area is chosen so the PM can supply the lift at modest B.

The PM-bias check, with steel treated as ideal: B_g ≈ μ₀H_c·l_pm / (l_pm/μ_rec + g). With H_c = 11 kOe and l_pm = 1", that gives **0.93 / 0.90 / 0.87 T at 6 / 7 / 8 mm**. This is roughly twice the needed B_g, *if* the rest of the circuit can carry the flux. The next table shows it can't.

### 2.3 Flux continuity: every section must carry φ = B_g·A_pole

For the current geometry, B_section = B_g × (1" / section thickness), independent of depth [derived].

| Section | Thickness (flux ⟂) | B at the required B_g of 0.34–0.47 T | B at the model's linear B_g of 0.80 T (7 mm) | Verdict |
|---|---|---|---|---|
| Leg / pole | 1.0" | 0.34–0.47 T, plus leakage | 0.80 T | OK |
| PM | 1.0" | same as leg | same | OK |
| Base (back-iron) | 1.5" | 0.23–0.31 T | 0.53 T | **Oversized** |
| **Track** | **0.25"** | **1.34–1.88 T** | **3.2 T (impossible)** | **Saturated. The binding constraint** |

Key findings [derived / inference]:

1. **The 0.25" track is the choke point.** At 1.5–1.8 T in the track, the gap flux caps at B_g = 0.375–0.45 T. That gives at most **430–620 N (6" yoke)** or **650–940 N (9" yoke)**, which sits right at the requirement. Near saturation, k_i and k_s collapse and become strongly nonlinear.
   - **Sizing rule:** t_track ≥ w_pole · B_g / B_max. With B_max = 1.5 T ([Zickler](https://arxiv.org/pdf/1103.1119)), that is **≥ 0.3" for B_g = 0.45 T and ≥ 0.55" for B_g = 0.8 T**. Recommend a **≥ 0.5" (12.7 mm) reaction rail**, or confirm that the real rail is thicker or wider than the model assumes.
2. **The Maple force law looks wrong. Verify before trusting the LEV-72 pod-mass table [derived].**
   - `reluctance_model.py` takes F = ∂/∂g(½·ℛ_air·φ²), with φ = φ(g). The standard co-energy result at fixed MMF is F = ½φ²·∂ℛ_total/∂g = φ²/(μ₀A_pole). That equals the Maxwell-stress sum over both poles.
   - The two differ by a factor of (½ − η), where η is the gap's share of total reluctance (about 0.2 at 7 mm). At 7 mm, 6" depth, the model's own flux gives **591 N (Maple) vs 1,973 N (Maxwell)**. Numerically we reproduce the worksheet's 772.6 N check point.
   - The Maple form also goes negative for η > 0.5, which is unphysical.
   - The linear-steel model (μ_r = 100) also ignores the track saturation above, which pulls the true force back down. The two errors partly cancel, so the table may be accidentally close. **Check it against an Ansys magnetostatic run of the big yoke with a nonlinear 1018 B-H curve before sizing anything else from it.**
3. **The base can shrink [inference].** The base carries the same φ as the legs. Sized to the leg (1.0–1.1" high, plus an inner-corner radius against choking per [Dexter](https://www.dextermag.com/wp-content/uploads/2023/07/Electromagnet-Design-Considerations_2022rev-6-23-23-2-1.pdf)), it saves about **2.9 kg per 9" yoke** (11.6 kg per pod) against the 1.5" base. Do this only after FEM, because the base also carries leakage flux.
4. **Joint gaps are cheap in this circuit [derived].** The two 1" PMs are magnetically about 48 mm of air, and the two working gaps are 12–16 mm. An extra 0.05–0.1 mm per bolted interface is < 0.5% of loop reluctance. A **separable yoke** (bolted legs or pole pieces, so pre-wound coils can slide on) costs almost nothing magnetically here. That is the opposite of a gapless transformer core.

### 2.4 Coil window and copper

The coil sets control authority, not lift, because the PM carries mg at zero power. With the PM dominating: Δφ/φ ≈ N·I / (H_c·l_pm) per leg, so **ΔF/F ≈ 2·N·I / 22,234 At** [derived from the model's MMF]. For example, N·I = 2,550 At (250 turns × 10.2 A) gives about ±23% force authority, which matches the model's 463–734 N swing at 7 mm.

Window per coil [derived; assumptions: 38.1 mm radial half-window, 1 mm leg clearance, 1.5 mm half-gap between coils, 3 mm recess below the pole face so touchdown lands on steel; fill 0.6]:

| Bobbin | Winding area | Copper area | N·I at 2 A/mm² (continuous) | N·I at 6 A/mm² (short peak) |
|---|---|---|---|---|
| None (bobbinless/bonded) | 1,700 mm² | 1,020 mm² | 2,040 At | 6,130 At |
| 2 mm printed/thin wall | 1,470 mm² | 880 mm² | 1,770 At | 5,300 At |
| **6.35 mm acrylic (current)** | **1,030 mm²** | **620 mm²** | **1,230 At** | **3,700 At** |

- **The 1/4" acrylic bobbin costs about 40% of the usable window** compared with bobbinless, and 30% compared with a 2 mm wall. Most of the loss is the two 6.35 mm flanges eating a 50.8 mm window height.
- **Continuous vs peak current [inference].** Zero-power hover keeps coil RMS current near zero. The continuous-J limit (1–2 A/mm² from [Zickler](https://arxiv.org/pdf/1103.1119) and [Sanfilippo](https://arxiv.org/pdf/2602.19808)) therefore applies to RMS disturbance current. Short peaks can run higher, bounded by the coil's thermal time constant. Log coil temperature via R_dc drift, as the vault characterization doc already recommends.
- **Aspect ratio.** The per-coil window is about 35 × 48 mm, which fits Zickler's 1:1–1:2 guidance.
- **Taller legs trade copper for leakage [inference].** Leg-to-leg leakage permeance across the window is roughly μ₀·(h/2)·d / w. For the current 2" × 3" window that is about **18% of the gap permeance** at 7 mm. That is significant, because the PM-dominated loop has high reluctance and flux readily takes the shortcut; the vault's `Levitation Research Claude.md` already flags this risk.
  - A taller window adds N·I linearly but adds leakage.
  - A wider window cuts leakage but lengthens the base and track path.
  - Settle the trade in Ansys.

### 2.5 Fringing

At g / w_pole = 7 / 25.4 ≈ 0.28, fringing is not a small correction. McLyman's factor gives about 1.3 using √A of a 1" × 6" pole and h = 50.8 mm ([e-magnetica](https://e-magnetica.pl/doku.php/flux_fringing_factor)). The formula targets gapped inductor legs, and for a long, thin pole √A overstates the relevant dimension. Treat 1.3 as an order of magnitude and take the real number from FEM [inference].

Chamfering pole edges reduces edge saturation ([Sanfilippo](https://arxiv.org/pdf/2602.19808)). Here, though, the pole faces run at only about 0.4 T, so the saturation fix belongs on the track, not the poles.

### 2.6 Checklist for the next yoke revision [inference]

1. Run Ansys on the big yoke with nonlinear 1018 B-H and the real rail. Replace the Maple force law.
2. Rail thickness ≥ w_pole·B_g/1.5 T, i.e. ≥ 0.5".
3. Legs ≥ pole width, with no necking at the PM interface.
4. Base cross-section about equal to the leg's plus leakage margin, with radiused inner corners.
5. Pole faces stand proud of the coils by ≥ 3 mm.
6. Bobbin wall and flanges ≤ 2–3 mm to recover about 30–40% of window.
7. Separable legs are acceptable magnetically: joint gaps are < 0.5% of loop reluctance.

### Sources

- T. Zickler, "Basic design and engineering of normal-conducting, iron-dominated electromagnets," CERN Accelerator School, [arXiv:1103.1119](https://arxiv.org/pdf/1103.1119). Used §4.2 (iron < 1.5 T), §4.4 (solid vs laminated), §4.6.1 (air-cooled J, fill factor), §5 (packing 0.6–0.8, aspect ratio).
- S. Sanfilippo, "Conventional Accelerator Magnets," CERN Accelerator School 2024, [arXiv:2602.19808](https://arxiv.org/pdf/2602.19808). Used saturation about 1.5 T, the passive-cooling J < 1 A/mm², and chamfers.
- Dexter Magnetic Technologies, [*Electromagnet Design Considerations* (rev 6/23/23)](https://www.dextermag.com/wp-content/uploads/2023/07/Electromagnet-Design-Considerations_2022rev-6-23-23-2-1.pdf). Used choke points.
- [Wikipedia, "Electromagnet"](https://en.wikipedia.org/wiki/Electromagnet). Used F = B²A/2μ₀ and the 1.6–2 T ceiling.
- [Encyclopedia Magnetica, "Flux fringing factor"](https://e-magnetica.pl/doku.php/flux_fringing_factor). Used McLyman's formula.
- Repo: `Vault/Magnetic-Circuit-Model/reluctance_model.py`, `LEV-72-mechanical-dimensions-and-specs.md`, `Vault/docs/rfcs/Levitation Research Claude.md`, `Vault/docs/rfcs/streams/Maglev Actuator Characterization.md`.

---

## Coil impregnation (epoxy/varnish)

Scope: how to lock the turns of a U-core EMS/HEMS coil after winding, or while winding. Tags: **[S#]** marks a sourced fact (see Sources). **[Inference]** marks our own reasoning, not taken from a source.

### 1. Constraint that decides most of this: the bobbin

| Bobbin material | Heat limit (sourced) | Solvent sensitivity (sourced) |
|---|---|---|
| Cast PMMA (acrylic) | HDT 105 °C, Vicat 105–112 °C, **max continuous service 82 °C** [S1] | Solvents such as alcohols, turpentine and acetone can damage the sheet. Environmental stress cracking happens when stress (e.g., from fabrication) meets a chemical; annealing removes the stress [S1] |
| PLA (printed) | HDT ~55 °C [S2] | Low chemical/solvent resistance [S2] |
| PETG (printed) | HDT ~70 °C [S2] | Better than PLA [S2] |
| ABS (printed) | HDT ~98 °C [S2] | Softened by acetone (acetone smoothing) [S2] |

**[Inference]** Laser cutting leaves stressed edges on acrylic, so a 1/4" laser-cut PMMA bobbin is a likely place for stress cracking. Keep any cure or bake at or below about 80 °C for PMMA, about 60 °C for PETG, and about 45 °C for PLA. Avoid ketones and aromatic thinners, and test alcohols on scrap before use. If a process needs 120 °C or more, the bobbin has to be removable (a mandrel) or made from a high-temperature material.

### 2. Method comparison (summary)

| Method | Typical resin / viscosity | Cure | Thermal class | Voids | Rework | Equipment | PMMA / printed bobbin OK? |
|---|---|---|---|---|---|---|---|
| **VPI** | Solventless polyester or epoxy, low viscosity. CC-1105: 300–800 cP at 25 °C [S3] | CC-1105: 1–2 h at 325 °F or 2–3 h at 300 °F [S3] | CC-1105 in UL systems up to 220 °C [S3] | Best. Dry vacuum at ~5 Torr, then 85–95 psig pressure [S4]. CC-1105 cycle: 1–5 mbar for 30–60 min, then 80–90 psi for 30–120 min [S3] | None (thermoset) [Inference] | Vacuum/pressure vessel, transfer tank, oven [S4] | **No.** 149–163 °C bake is well above PMMA's 82 °C service limit [S1, S3] |
| **Vacuum-only (DIY)** | Same low-viscosity resins, or a room-temperature epoxy | Depends on resin | Depends on resin | Good. Vacuum removes air, and atmospheric pressure pushes resin in when vacuum is released [Inference]. Elantas lists vacuum impregnation separately from VPI [S5] | None | Vacuum chamber and pump. MG degasses at 25 inHg for 2 min [S6] | **Yes, only with a cure at 80 °C or below** (e.g., a room-temperature epoxy) [Inference] |
| **Dip-and-bake** | Solvent varnish, e.g. Dolph's AC-43 at 20–70 cP, thinned with T-200X [S7] | AC-43: air-dries in 1 h; 20–30 min at 150 °C for best toughness and bond strength [S7] | AC-43 "UL Systems to 180 °C" [S7] | Fair. Solvent loss leaves a thin film (1–1.5 mil/side) [S7], not a solid fill [Inference] | Partial: can be re-dipped [Inference] | Tank, oven | **Risky.** Air-dry avoids the heat, but the thinner could stress-crack PMMA. The TDS does not state what the thinner is, so check the SDS [S1, S7] |
| **Trickle** | 1K epoxy or UP. Damisol 3500 HiR: 600 mPa·s, cures 30 min at 160 °C [S8]. 2K alternative: Epoxylite 6107 at 100 cP (65 °C), cures 6–8 h at 121 °C, short exposure to 260 °C [S24] | Hot-cure | Class H [S8] | Good. Resin drips onto a rotating, **preheated** winding and thins as it heats [S9] | None | Rotating fixture, heating (oven or winding current) [S9] | **No.** Needs a preheated winding and ~160 °C cure [S8, S9] |
| **Wet-winding** | Room-temperature or low-heat epoxy brushed on each layer | Resin-dependent | Resin-dependent | Can be void-free if resin fully surrounds each turn and excess is squeezed out [S10]. In practice, air gets trapped at layer turnarounds [Inference] | None | Brush, winder, gloves | **Yes** with a cure at 80 °C or below [Inference] |
| **Self-bonding wire** | Bondcoat on the wire (butyral, polyamide, epoxy) | Oven 10–30 min; resistance, hot-air or solvent activation [S11, S12] | Base coat to Class F/H, but **bondcoat re-softens lower** (butyral ~100–105 °C) [S12, S13] | Turns bond only where they touch. Interstices stay empty [Inference] | **Thermoplastic bondcoats can be re-bonded** [S11] | Power supply (resistance) or oven, plus a fixture | **No as-bonded.** 110–230 °C bonding temperatures [S12, S13]. Suited to **bobbinless** coils on a removable mandrel [S11] |
| **Full potting in mold** | Filled epoxy. MG 832TC: 27,000 cP, 0.7 W/m·K [S14]. Epoxies Etc 50-3150: 60,000 cP [S15] | 832TC: 96 h at room temperature, or 2 h at 65 °C / 1 h at 80 °C / 45 min at 100 °C [S14]. 50-3150: 3–4 h at 85 °C [S15] | 832TC service −30 to 175 °C, **but Tg only 50 °C** [S14] | High viscosity does not penetrate the winding. Degas the mix [S6, S16] | None | Mold, mold release (MG 8329) [S17], vacuum chamber, oven | **Yes** for 832TC at room temperature or 65 °C [S1, S14]. 50-3150 at 85 °C is marginal for PMMA [S1, S15] |

### 3. Cross-cutting findings

**Thermal conductivity (sourced)**
- Varnish impregnants are 0.25–0.60 W/m·K [S18].
- Potted windings transfer heat much better than varnish-impregnated windings, but varnish costs less and handles transient overloads better [S18].
- MG 832TC (filled) is 0.7 W/m·K [S14].
- In HTS impregnation practice, fillers raise viscosity and get filtered out at gaps in the winding. That blocks resin and hinders VPI, so unfilled resins penetrate better but conduct heat worse [S16].
- The CC-1105 TDS lists thermal conductivity as "0.53 BTU-in/hr-ft²-°F" [S3]. **[Inference]** Taken literally that is about 0.08 W/m·K, which looks like a unit misprint. Verify with Dolph's before relying on it.

**[Inference]** The best path is split in two: a low-viscosity resin fills the interstices, and a filled resin goes only on the outside skin or as the pot. Filled resin alone will not reach between the turns.

**Rigidity, Lorentz forces and vibration**
- Resin painted onto a winding leaves voids. The wires can then move in service and fail, and pressure alone lets trapped gas re-expand afterward [S4].
- Rigid high-temperature epoxies with a CTE mismatch against copper cause interlaminar stress cracks. Flexibilizers fix the cracking but cost temperature capability [S19].
- **[Inference]** Forces between turns in an EMS coil are modest. The real loads are pod vibration, handling, and thermal cycling. Any method that bonds every turn is adequate, and void-free methods (vacuum, VPI) mainly add heat transfer and dielectric margin.

**Tg trap (832TC)**
- 832TC has Tg 50 °C and CTE 142 ppm/°C below Tg [S14].
- **[Inference]** A coil that runs above about 50 °C passes through the pot's Tg, so the pot softens and expands a lot. Either choose a higher-Tg potting compound (with a hotter cure, so bobbin limits apply) or keep the coil hot spot below Tg.

**Degassing and handling**
- MG: let the mix sit 15 min, or pull 25 inHg for 2 min. Preheating parts to 65 °C lowers viscosity but shortens working time [S6].
- Hand-mixed batches are limited (e.g., 3 kg for 832TC) to avoid flash cure [S6].
- Check viscosity and run a gel test before impregnating, because resin that is past its working life will not penetrate [S19].

**Bondable wire size limits**
- Elektrisola self-bonding wire comes in 0.010–0.50 mm only [S11].
- MWS offers AWG 14–50 [S13].
- **[Inference]** Heavy-gauge EMS windings probably need MWS or a custom order.
- Resistance bonding: 10–30 min, uniform heat, typical for wire thicker than 0.2 mm [S12].
- Solvent bonding for Elektrisola polyamide grades uses ethanol or methanol [S11]. MWS epoxy bondcoat uses MEK or acetone [S13], which is PMMA-hostile [S1].

### 4. Documented maglev / hyperloop / electromagnet examples

| Example                                               | What is documented                                                                                                                    |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| Transrapid (commercial EMS)                           | Levitation magnet poles are "assembled and sealed with resin based on epoxy components" and made by automatic pressure gelation [S20] |
| HTS maglev coil patent                                | Coils built from epoxy-impregnated pancake coils [S21]                                                                                |
| Accelerator / HTS magnets                             | Vacuum or VPI epoxy (e.g., CTD-101K), wet winding, and filler trade-offs are documented in detail [S16, S19]                          |
| Student hyperloop teams (TUM, EPFL, Delft, Swissloop) | **Not found.** Their public papers and proposals describe EMS architecture and control, but no coil impregnation process [S22, S23]   |

### 5. Practicality for a student team [Inference]

| Rank | Method | Why |
|---|---|---|
| 1 | **Vacuum-only impregnation with a room-temperature or ≤65 °C epoxy**, then an optional thin filled skin | Cheap vacuum chamber, fits the PMMA limits, good void removal |
| 2 | **Wet-winding with the same epoxy** | No equipment. Voids are more likely. Good for a first coil |
| 3 | **Mold potting with 832TC-class filled epoxy** | Best external heat path and rigidity, but heavy, not reworkable, and Tg 50 °C. Pair with #1 or #2 for the interior |
| 4 | **Bondable wire, bobbinless** | Clean and lightweight, but needs a mandrel and heavy-gauge sourcing, and re-softens around 100–180 °C depending on bondcoat |
| 5 | Dip-and-bake, trickle, VPI | Bake temperatures and solvents conflict with PMMA and printed bobbins. VPI can be outsourced to a motor-rewind shop if the bobbin changes to a high-temperature material |

### Sources

- [S1] Plaskolite, OPTIX Cell Cast Acrylic Sheet PDS — https://plaskolite.com/docs/default-source/pds/pds419_opx_cell_cast_eu.pdf
- [S2] UltiMaker, PETG vs PLA vs ABS — https://ultimaker.com/learn/petg-vs-pla-vs-abs-3d-printing-strength-comparison/
- [S3] John C. Dolph Co., DOLPHON CC-1105 TDS — https://www.electro-wind.com/web-files/Dolph's/Datasheets/CC1105-ds.pdf ; SDS (DAP-based, styrene/vinyl-toluene free) — https://res.cloudinary.com/eisinc/image/upload/product/von-roll-john-c-dolph/DOLCC110555G_MSDS.pdf
- [S4] Teledyne Hastings, App Note PB-195 "Vacuum Pressure Impregnation (VPI) Systems" — https://www.teledyne-hi.com/en-us/What-we-do_/Documents/ApplicationNotes/vacuum%20pressure%20impregnation%20system.pdf
- [S5] ELANTAS, Vacuum impregnation / VPI — https://www.elantas.com/europe/products/impregnating-materials/applications/vacuum-impregnation-vacuum-pressure-impregnation.html
- [S6] MG Chemicals, Application Guide – Potting Compounds — https://www.mgchemicals.com/downloads/application-guides/Application%20Guide-Potting%20Compound.pdf
- [S7] John C. Dolph Co., Synthite AC-43 TDS — https://www.electro-wind.com/web-files/Dolph's/Datasheets/AC-43-TECH.pdf
- [S8] Von Roll Damisol 3500 HiR (MatWeb) — https://www.matweb.com/search/datasheettext.aspx?matguid=a859fda20cef41b0a6ef941c0441368f ; Von Roll impregnation resins — https://www.vonroll.com/en/electrical/impregnation-resins/
- [S9] ELANTAS, Trickle Impregnation — https://www.elantas.com/europe/application-methods/impregnating-materials/trickle.html
- [S10] US Patent 4,554,730, "Method of making a void-free non-cellulose electrical winding" — https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/4554730
- [S11] Elektrisola, Selfbonding Wire Manufacturing Program and Technical Data — https://www.elektrisola.com/Download/Selfbonding%20wire_eng.pdf
- [S12] Elektrisola, Selfbonding Wire Info — https://www.elektrisola.com/en/Selfbonding-Wire/Info
- [S13] MWS Wire, Bondable Magnet Wire — https://mwswire.com/bondable-magnet-wire/
- [S14] MG Chemicals, 832TC TDS (Ver. 4.3, Feb 2026) — https://www.mgchemicals.com/downloads/tds/tds-832tc-2parts.pdf
- [S15] Epoxies Etc. 50-3150 (SpecialChem listing) — https://www.specialchem.com/plastics/product/epoxies-etc-50-3150
- [S16] "Review of materials for HTS magnet impregnation," Supercond. Sci. Technol. (2024) — https://iopscience.iop.org/article/10.1088/1361-6668/ad1aeb
- [S17] MG Chemicals, 8329 Epoxy Mold Release — https://mgchemicals.com/products/potting-compounds/sundries/8329-epoxy-mold-release/
- [S18] Liu et al., "Comparative study of thermal properties of electrical windings impregnated with alternative varnish materials," J. Eng. (2019) — https://www.researchgate.net/publication/333456714
- [S19] Hubrig & Biallas, "Managing Coil Epoxy Vacuum Impregnation Systems…," PAC 2005 — https://proceedings.jacow.org/accelconf/p05/PAPERS/MPPT091.PDF
- [S20] "The Superspeed Maglev System Transrapid…composite construction…" (ETDEWEB) — https://www.osti.gov/etdeweb/biblio/20164331
- [S21] US Patent 5,668,090, HTS AC magnets for maglev — https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/5668090
- [S22] TUM Hyperloop, "Propulsion and Suspension Concept of the TUM Hyperloop Full-Scale Demonstrator," ASI 7(2):19 (2024) — https://doi.org/10.3390/asi7020019
- [S23] EPFL DESL, Pod Levitation project proposal — https://www.epfl.ch/labs/desl/wp-content/uploads/2025/10/Proposal_Pod_Levitation.pdf
- [S24] Epoxylite 6107 TDS (ELANTAS PDG): 100:100 mix, 100 cP at 65 °C, cure 6–8 h at 121 °C, dip/trickle — https://res.cloudinary.com/eisinc/image/upload/product/elantas-pdg-inc/EPO6107G_Brochure.pdf

---

## Winding methods and U-core assembly

Legend: **[S]** = sourced fact (citation inline). **[I]** = our inference or engineering judgement. Source keys are listed under Sources.

### Bottom line

- **[S]** Industry does both. Transrapid's reference pole winds aluminium strip and insulating foil straight onto the core [P-7724120]. The Transrapid production-process patent instead uses a plastic "winding body" (a frame around the core cavity). That body can be wound after it is placed on the lamination stack, or wound first and then mounted, and the patent says either works [P-6584671].
- **[I]** A separate bobbin that slides onto an open-ended U leg is standard practice, and nothing in the sources says it costs performance. Its real costs are lost window area, hub collapse under winding pressure, and how the coil is held in place. Pole shoes are the one geometric blocker, and bolt-on shoes solve it.

---

### 1. Prior art: direct-on-steel vs slid-on former

| Example                               | Approach                                                                          | Key detail                                                                                                                                                        | Source                                                      |
| ------------------------------------- | --------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| Transrapid magnet pole (ThyssenKrupp) | **Direct on core**                                                                | Al strip ~0.2 mm plus insulating foil, "wound coaxially ... onto said core". An insulation layer between core and winding serves for both assembly and insulation | [P-7724120]                                                 |
| Transrapid pole, alternate patent     | Direct, many layers                                                               | Poles of "up to 300 layers" of strip                                                                                                                              | [P-7911312] (search abstract only; full text not retrieved) |
| Transrapid subassembly process        | **Plastic winding body (bobbin)**, wound in place *or pre-wound and then mounted* | Aluminium pole jaws slide onto guide rods through the stack. The whole assembly is then cast in epoxy at 1–3 bar, giving a 2–3 mm coating                         | [P-6584671]                                                 |
| Early Japanese EMS U-magnet           | Coils on each leg (not on the yoke)                                               | Leg-wound coils leak less flux than coils wound on the root/yoke                                                                                                  | [P-4123976]                                                 |
| Lifting magnet with pole shoe         | A bolt serves as the winding mandrel and also holds the pole shoe on              | Shows the "wind on a mandrel, then fix the pole piece" pattern                                                                                                    | [P-4264887]                                                 |
| Student MAGLEV prototype              | Non-magnetic bobbin, 130 turns of 2.54 mm wire                                    | Coil wound on a bobbin                                                                                                                                            | [SD-Maglev] (search abstract)                               |
| Cut C-core transformers               | Coils pre-wound on bobbins; two core halves inserted and banded                   | Standard industrial practice                                                                                                                                      | [ElectroCore], [McLyman]                                    |

**[S]** We found no student Hyperloop team report (Delft, Swissloop, TUM, EPFLoop, UPV, MIT) that documents its coil-winding method in retrievable detail. What they publish is system level [TUM-ASI], [HEMS-Wiki].
**[I]** Treat any team-specific claim about their winding method as unverified.

---

### 2. Bobbin/former design

| Topic | Sourced guidance | Inference for the team |
|---|---|---|
| **Wall thickness** | Minimum molded walls: nylon 0.025", PBT 0.030", PPS/PET 0.035", LCP 0.012". Walls that are too thin let the flanges flare and the tube collapse during winding. Wire pressure must not collapse the bobbin core [COSMO] | A 1/4" (6.35 mm) acrylic wall is about 8x a molded wall. On each side it takes 6.35 mm of radial build (the window depth) and 2 × 6.35 mm of axial length (both flanges). Use Ampère-turn and resistance budgets to decide whether to thin it to ~1.5–3 mm. |
| **Window loss** | Single-bobbin effective-window factor S3 = 0.835–0.929 for laminations. Overall Ku ≈ 0.4 is typical [McLyman] | Compute Ku with your real bobbin. Thick walls and flanges pull S3 well below 0.83. |
| **Flanges** | Untapered flanges wind better. Thick flanges may be cored out. Flanges can be designed for encapsulant overmold [COSMO] | Flanges also react the axial bulge of the coil. Glued acrylic flange joints are the weak point under winding pressure. |
| **Clearance to leg** | Plastic CTE is up to 6x that of metal, and heating changes bobbin size [COSMO]. Bobbins must slip on over the core's min/max tolerances [McLyman] | Give ~0.3–0.5 mm radial clearance per side, measured after winding, because winding pressure shrinks the ID. Shim or wedge afterwards. |
| **Split bobbins** | COSMO covers two-part bobbin/cover designs with "I.D. clearance ... for mismatch of the cover" [COSMO]. Transrapid's winding body is a frame [P-6584671] | Split halves let you slip a former over a closed core, but the seam must survive hoop compression. Prefer a one-piece hub with bonded flanges. |
| **Bobbinless coils** | Self-bonding wire has a thermoplastic or thermoset bond coat, activated by hot air, oven, current (resistance bonding, for wire > 0.2 mm) or solvent. Voltage and time must be found experimentally. Thermoplastic bonds soften again when heated [Elektrisola]. Oven bonding needs fixtures [Bondable-Search] | Wind on a split or tapered aluminium mandrel coated with release agent, bond the coil, then press the mandrel out. This removes the wall entirely. You still need a separate Nomex/Kapton ground liner. |
| **Insulation to steel** | Nomex 410 at 0.13 mm: ~27 kV/mm (680 V/mil) [Nomex410]. Kapton HN at 1 mil: 7,700 V/mil [KaptonHN]. Thin slot-liner Nomex is 0.09–0.38 mm [Nomex-Search] | At <100 V drive, dielectric strength is not the issue. Abrasion and cut-through at sharp steel corners is. One 0.13–0.25 mm Nomex wrap on the leg, or inside a bobbinless coil, is enough. |
| **Lead exits** | Start-lead slots should be tangent to the tube so the first turns are insulated. Radius the slot corners and edges. For low volume, a start groove with the lead taped out of the way is recommended [COSMO] | Put exits on the flange, not the hub. Sleeve the start lead (PTFE or glass sleeving) where it crosses later layers. |
| **Strain relief / retention** | Molded crush ribs or V-ribs give an interference fit that stops vibration noise, instead of wedging or gluing [COSMO]. Low-viscosity epoxy or VPI fills voids and improves thermal conductivity and vibration resistance [Elantas], [MasterBond] | Retention loads: Lorentz force on the coil pushes it radially outward and toward the gap, and pod vibration adds to it. Lock the bobbin with a clamp plate or pole shoe, not friction alone. Tie the leads to the frame, never to the terminals. |

---

### 3. U-core assembly for pre-wound coils

| Option | How it works | Pros / cons | Source |
|---|---|---|---|
| **One-piece U, plain legs** | Slide the coil over the free pole end | Simplest. Works only if the pole face is no wider than the leg | [I] |
| **One-piece U with wide pole shoes** | Shoes block the coil from sliding on | Must either wind in place or make the shoes removable | [I] |
| **Bolt-on pole shoes** | Slide the coil on, then bolt or dowel the shoe on | Adds one butt joint per leg. The shoe also acts as the coil's axial retainer | [P-4264887], [P-6584671] (pole jaws on rods) |
| **Two-piece cut C-core** | Cut, lap and etch the mating faces, insert the coils, band the halves together | Cut cores must be varnish-impregnated first. Lapping reduces noise and vibration. Etching removes burrs that short laminations. Closed gaps are typically 0.0005–0.002" (13–50 µm) | [ElectroCore] |
| **Laminated stack assembled around coils** | Stack laminations on guide rods through a pre-wound winding body, then resin-cast | Industrial Transrapid route. Needs a mold and resin casting | [P-6584671] |

**Butt-joint penalty:**
- **[S]** A lapped closed joint is 13–50 µm [ElectroCore]. In one cut-core example the gap is 0.07 mm with a 250 mm path [eMagnetica].
- **[I]** An EMS magnet runs a working gap of ~2 × 8–15 mm. Two extra joints of ~50 µm add about 0.1 mm to a ~20 mm total, a <1% MMF penalty. Unlapped saw-cut faces could be 10x worse and still come in around 5%.
- **[I]** For a HEMS magnet, joint reluctance also slightly reduces the PM operating point.
- **[I]** Put joints where flux density is modest, and keep flux crossing them normal to the face.

---

### 4. Winding practice

| Topic | Sourced facts | Inference |
|---|---|---|
| **Machines / jigs** | DIY winders use one stepper on the spindle and one driving a leadscrew wire-guide carriage. Lathe-style headstock/tailstock builds are common [Hackaday-1805], [DIY-Search] | Cheapest good option: lathe or hand crank, mechanical or Hall-sensor turn counter, and a tension brake on the spool. Traverse can be manual for ≤18 AWG. |
| **Tension** | Maximum copper tensions, set by annealed yield: AWG 14 = 32 lb (15 kg), AWG 16 = 20 lb (9.2 kg), AWG 18 = 13 lb (5.8 kg), AWG 20 = 8 lb. Minimums are ~75% of those. Exceeding the maximum stretches the wire and raises resistance [MWS]. Use 50–80% of maximum [Tension-Search] | Kilogram-level tension over hundreds of turns builds large hoop compression on the hub. That is the mechanism behind COSMO's "tube collapse" warning, and it applies to a glued acrylic box hub. |
| **Orthocyclic vs random** | Theoretical: hexagonal/orthocyclic 0.907, square layer 0.785 [McLyman]. Practical: orthocyclic ~90% of theoretical, wild/random 73–80% [Wiki-CWT]. In real designs layer and random both land near 0.61 once insulation is included [McLyman]. Wound length exceeds calculated length by 10–15% [McLyman] | Plan for 0.55–0.6 copper fill with hand-wound round wire. Treat orthocyclic as a bonus you cannot count on without a guided machine. |
| **Round vs rect / foil** | On rectangular formers, orthocyclic lay works on only three sides; the fourth side takes the layer step [Wiki-CWT]. Transrapid uses Al strip and foil [P-7724120]. Rectangular or foil conductors can reach ~85% fill vs ~55% for round [Foil-Search] | Foil gives the best fill and heat path (each turn reaches the flanges), but the edges need deburring and it needs interleaved film. Moderate for students. |
| **Layer insulation** | Any layer insulation lowers fill further [McLyman] | For low-voltage DC magnets, enamel alone between layers is normal. Add a Kapton or Nomex layer every N layers only if layers bulge or for thermal/mechanical reasons. |
| **Corner bulging on rectangular legs** | Winding on rectangular bobbins bows outward. Derate the available build by 15–20% (0.85x). Round bobbins give uniform 360° tension and negligible bowing [McLyman]. Orthocyclic crossover zones run 5–10% taller [Wiki-CWT] | Radius the hub corners generously (≥ 3–5 mm or more). Consider a clamp plate on the long sides while winding. Budget the 0.85x build when checking clearance to the rail and the other leg. |
| **Turn verification** | Copper α = 0.00393/°C at 20 °C [Cirris] | Measure R with a 4-wire milliohm meter, correct it to 20 °C, and compare with ρ·N·MLT/A. A ±2–3% error band means a few turns. Also measure L on the core against FEM. A shorted turn shows as a Q drop or a large L drop at kHz. |

---

### 5. Failure modes

| Failure | Mechanism | Source |
|---|---|---|
| Turn-to-turn short | Nicked wire, loose vibrating turns, contamination, overheating | [EEP-Motor] |
| Enamel carbonization | Running over thermal class, leading to runaway shorting | [ElectricalFlux] |
| Tube collapse / flange flare | Thin or weak bobbin under winding pressure | [COSMO] |
| Higher R than design | Wire stretched by over-tension | [MWS] |
| Build larger than calculated | Rectangular-bobbin bowing, crossover humps, lay factor | [McLyman], [Wiki-CWT] |
| Shorted core laminations after cutting | Cut burrs | [ElectroCore] |
| Lead breakage | Sharp or undersized lead slots | [COSMO], [Bobbin-Search] |

**[I]** Failure modes specific to student U-cores that we expect:
- Enamel cut at the steel leg corners if the ground liner is skipped.
- The coil walking toward the rail under vibration when it is held only by friction.
- Acrylic softening or crazing at coil temperature. The separate material agent covers this.
- Coil build fouling the rail or the adjacent coil because of bulging.

---

### Sources

- [P-7724120] US7724120B2, Magnetic pole for magnetic levitation vehicles (ThyssenKrupp Transrapid). https://patents.google.com/patent/US7724120B2/en
- [P-7911312] US7911312, Magnet pole for magnetic levitation vehicles. https://www.freepatentsonline.com/7911312.html
- [P-6584671] US6584671B2, Process for producing an electromagnetic subassembly for a magnetic levitation railway. https://patents.google.com/patent/US6584671B2/en
- [P-4123976] US4123976A, Attractive type electromagnet device for magnetic levitation running vehicles. https://patents.google.com/patent/US4123976
- [P-4264887] US4264887A, Electro-lifting magnet. https://patents.google.com/patent/US4264887A/en
- [SD-Maglev] A prototype of an energy-efficient MAGLEV train, ScienceDirect (2021). https://www.sciencedirect.com/science/article/pii/S2666790821001774
- [TUM-ASI] Propulsion and Suspension Concept of the TUM Hyperloop Full-Scale Demonstrator, Appl. Syst. Innov. 7(2):19. https://doi.org/10.3390/asi7020019
- [HEMS-Wiki] Hybrid electromagnetic suspension. https://en.wikipedia.org/wiki/Hybrid_electromagnetic_suspension
- [McLyman] McLyman, Transformer and Inductor Design Handbook, Ch. 4, Window Utilization, Magnet Wire, and Insulation. https://coefs.charlotte.edu/mnoras/files/2013/03/Transformer-and-Inductor-Design-Handbook_Chapter_4.pdf
- [Wiki-CWT] Coil winding technology. https://en.wikipedia.org/wiki/Coil_winding_technology
- [COSMO] Cosmo Corp., Coil Bobbin Catalog and Design Manual. https://www.cosmocorp.com/docs/en/COSMO-bcat-en-mdres.pdf
- [ElectroCore] Electro-Core, Processes (cut cores). https://www.electro-core.com/processes
- [eMagnetica] Encyclopedia Magnetica, Air gap. https://www.e-magnetica.pl/doku.php/air_gap
- [Elektrisola] Elektrisola, Selfbonding wire info. https://www.elektrisola.com/en-us/Selfbonding-Wire/Info
- [Bondable-Search] MWS Wire, Bondable magnet wire. https://mwswire.com/bondable-magnet-wire/
- [Nomex410] DuPont Nomex 410 Technical Data Sheet. https://www.dupont.com/content/dam/aramids/amer/us/en/safety/public/documents/en/Nomex_410_Tech_Data_Sheet.pdf
- [Nomex-Search] Electrolock, Slot liner insulation. https://www.electrolock.com/thought-leadership/slot-liner-insulation-and-motor-efficiency-material-considerations/
- [KaptonHN] DuPont Kapton HN Technical Data Sheet. https://docs.rs-online.com/c6e2/0900766b80659d8c.pdf
- [MWS] MWS Wire, Recommended Winding Tensions. https://mwswire.com/wp-content/uploads/2016/10/Recommended-Winding-Tensions.pdf
- [Tension-Search] Ingrid West Machinery, tension calculator. https://www.coilwindingmachines.eu/engineers_corner/tension.html
- [Hackaday-1805] Coil Winding Machine, Hackaday.io. https://hackaday.io/project/1805-coil-winding-machine
- [DIY-Search] element14, Building a Coil Winding Machine. https://community.element14.com/products/raspberry-pi/raspberrypi_projects/b/blog/posts/building-a-coil-winding-machine-part-1-prototype
- [Foil-Search] Electrocube, Foil transformers technical bulletin (via search abstract). https://www.electrocube.com/pages/transformers-technical-bulletin-11
- [Elantas] ELANTAS, Vacuum / VPI impregnation. https://www.elantas.com/europe/products/impregnating-materials/applications/vacuum-impregnation-vacuum-pressure-impregnation.html
- [MasterBond] MasterBond, Potting and impregnation compounds for ignition coils. https://www.masterbond.com/techtips/potting-and-impregnation-compounds-ignition-coils
- [Cirris] Cirris, Temperature coefficient of copper. https://cirris.com/temperature-coefficient-of-copper/
- [EEP-Motor] EEP, Troubleshooting winding problems. https://electrical-engineering-portal.com/troubleshooting-winding-problems-three-phase-electric-motors
- [ElectricalFlux] ElectricalFlux, Wire sizing and insulation classes. https://electricalflux.com/wire-switches/electromagnetic-wire-sizing-insulation-classes
- [Bobbin-Search] Bobbin design search results (corner radius ≥0.005", lead-out slot breakage). Secondary source only; treat as low confidence.

---

## Bobbin materials (incl. 3D printing)

Labels used in this section:
- **[S#]** is a sourced fact. The number points to the Sources list.
- **[Inference]** is my own engineering judgement or arithmetic. It is not in the cited source.

Datasheet values are "typical" figures, and vendors test them differently: ISO 75 vs ASTM D648, printed vs molded specimens, annealed vs as-printed. Treat cross-vendor comparisons as ±10–20 °C.

### 1. Context: what temperatures does a bobbin actually see?

- **Insulation classes.** UL 1446 rates insulation *systems* by temperature class: Class A = 105 °C, B = 130 °C, F = 155 °C, H = 180 °C [S1][S2]. The bobbin is one component of that system.
- **Glass-epoxy reference.** G10/FR4 is typically treated as Class B (130 °C continuous) [S3].
- **Molded PA66-GF30 reference.** Zytel 70G30HSL carries a UL 746B electrical RTI of 140 °C [S4].
- **Impregnation bake cycles are the hottest event in a bobbin's life.**
  - Dolph's dip-and-bake varnishes and resins list bake temperatures of 230–350 °F (110–177 °C) [S5].
  - ELANTAS Ripley E468-2 epoxy impregnating resin cures in 50–80 min at 150 °C [S6].
- **[Inference] Design target.** A student levitation coil at holding current will probably run at 50–100 °C at the hotspot. The bake cycle (110–150 °C for 1–6 h) is therefore the governing thermal requirement, unless the team uses a room-temperature-cure epoxy. **Size the bobbin to survive the bake, not just normal operation.**

### 2. Honest evaluation of the baseline: 6.35 mm laser-cut acrylic (PMMA)

| Issue | Sourced facts | Assessment [Inference] |
|---|---|---|
| **HDT vs coil temperature** | Cast acrylic: HDT 99 °C at 264 psi (1.82 MPa). Maximum recommended continuous service 180 °F (82 °C), or 200 °F short-term [S7]. Extruded/"premium" grades are rated lower, at 160 °F (71 °C) continuous [S8]. | Acceptable for a coil held below about 70 °C in service. **Fails any 110–150 °C varnish or epoxy bake.** The flanges will sag and bow under winding pressure. |
| **Brittleness and notch sensitivity** | Notched Izod 0.4 ft·lb/in (21.6 J/m). Elongation at rupture 4.2% [S7]. | Very notch sensitive. Laser-cut slots, lead-exit notches and the sharp inside corners of tab/slot joints concentrate stress. Winding tension loads exactly those corners. |
| **Crazing (solvents and stress)** | Crazing needs residual stress *plus* chemical attack. Annealing (80 °C, about 1 h per mm of thickness) minimizes it. Cemented parts should be annealed [S9]. ACRYLITE's chemical-resistance table rates acetone, MEK, toluene, xylene, lacquer thinner, ethyl acetate and 95% ethanol as **"N" (not resistant)** [S7]. | Many dip varnishes are thinned with aromatic solvents. Styrene-based polyester resins and solvent cements are also aggressive. Laser-cut edges and solvent-welded joints are exactly the stressed regions that craze. Solvent varnish on acrylic is therefore high risk. Solventless epoxy is lower risk, but it is not risk-free. |
| **Dielectric** | 430 V/mil (17 kV/mm) at 0.125 in thickness [S7]. | Not a limitation. See section 5. |
| **Window area lost to 6.35 mm walls and flanges** | (arithmetic) | See the worked example below. |

**Worked example: window area [Inference]**

Assume hypothetical dimensions: 50 mm available winding length along the leg, and 12 mm available radial build per coil.

- **Acrylic.** Two 6.35 mm flanges plus a 6.35 mm tube wall leave (50 − 12.7) × (12 − 6.35) = **211 mm²** of copper window.
- **Printed.** Two 2.0 mm flanges plus a 1.5 mm tube wall leave (50 − 4) × (12 − 1.5) = **483 mm²**, about **2.3× more** window.

That is 2.3× the ampere-turns at the same current density. Equivalently, it is roughly 2.3× lower I²R loss for the same NI. Stated generally, each millimetre of wall or flange costs (window length × 1 mm) or (radial build × 1 mm) of copper.

**Baseline verdict [Inference].** Acrylic is fine for a first, un-impregnated, low-duty test coil. It is the wrong material for an impregnated, oven-baked, or continuously powered levitation coil. It also wastes a large share of the window.

### 3. Comparison table

**Column key**

| Abbreviation | Meaning |
|---|---|
| HDT 0.45 / HDT 1.8 | Heat deflection temperature at 0.45 and 1.8 MPa. |
| CUT | Continuous-use temperature. |
| E | Tensile or Young's modulus. XY is in-plane; Z is across layers. |
| Moisture | Water uptake. |
| Bake? | Survives a 120–150 °C epoxy bake. This column is my [Inference] from HDT, keeping a 20 °C or larger margin at 0.45 MPa. |
| Printer | Open frame / enclosure / heated chamber / hardened nozzle. |
| Cost | Rough 2026 street price, [Inference] unless it has a citation. |
| Creep | Qualitative [Inference]. |

| Material | HDT 0.45 / 1.8 (°C) | CUT (°C) | Dielectric (kV/mm) | E (GPa) | Creep | Moisture | Resin/varnish compatibility | Bake? | Printer | Cost |
|---|---|---|---|---|---|---|---|---|---|---|
| **PMMA (baseline)** | – / 99 [S7] | 82 [S7] | 17 [S7] | 2.8–3.3 [S7] | Low at room temp; high near 80 °C | 0.2%/24 h [S7] | Poor: acetone, MEK, toluene, xylene rated N [S7] | **No** | Laser cutter | ~$30–60 per sheet |
| **PLA** (Prusament) | 55 / 55 [S10] | none given | 23.5 (printed, 1.2 mm) [S11] | 2.3–2.4 [S10] | Severe above ~45 °C | 0.13%/24 h [S10] | Moderate | **No** | Open frame | ~$20–25/kg |
| **PETG** (Prusament) | 68 / 68 [S12] | none given | 27.6 (printed) [S11] | 1.5–1.6 [S12] | High above ~55 °C | 0.07%/24 h [S12] | Fair; some solvents attack it | **No** | Open frame | ~$20–25/kg |
| **ASA** (Prusament) | 93 / 86 [S13] | none given | 20.4 (printed) [S11] | 1.6–1.7 [S13] | Moderate | 0.16%/24 h [S13] | Poor with ketones and aromatics [Inference: styrenic] | **No** | Enclosure | ~$25–30/kg |
| **PC Blend** (Prusament) | 113 / 93 [S14] | none given | ~30 (printed PC/ABS) [S11] | 1.9–2.0 [S14] | Moderate; prone to stress-cracking | 0.13%/24 h [S14] | Poor: stress-crazes with many solvents [Inference] | **Marginal** at 120 °C; **no** at 150 °C | Enclosure; 110 °C bed | ~$30–40/kg |
| **PA6-GF** (Bambu) | 182 / 158 [S15] | none given | not given | 2.85 XY / 1.95 Z [S15] | Moderate; worse when wet | **2.56%** saturated [S15] | Good with epoxy [Inference]. Dry the part first. | **Yes**; anneal 80–130 °C [S15] | Enclosure, 45–60 °C chamber [S15]; hardened nozzle | ~$40–60/kg |
| **PA-CF** (Bambu PA6/PA12-CF) | 180 / 160 [S16] | none given | not given; see CF caution | 4.08 XY / 2.45 Z [S16] | Low-moderate | 1.70% [S16] | Good with epoxy [Inference] | **Yes** | Enclosure; hardened nozzle | ~$50–80/kg |
| **PAHT-CF** (Bambu) | 194 / 170 [S17] | none given | not given; see CF caution | 3.86 XY / 2.18 Z [S17] | Low-moderate | 0.88% [S17] | "Not resistant to some organic solvents" [S17] | **Yes**; anneal 80–130 °C [S17] | Enclosure, 45–60 °C chamber [S17]; hardened nozzle | ~$60–90/kg |
| **Unfilled PA12** | 0.45 MPa value not published in the page reached [S18] | none given | not given | ~1–1.5 [Inference] | High | ~1–1.5% [Inference] | Good | Marginal | Enclosure; warps without it [S18] | ~$40–60/kg |
| **PPS-CF** (Bambu) | 264 / 235 [S19] | ">200 °C" (marketing claim) [S20] | not given; see CF caution | 8.23 XY / 2.85 Z [S19] | Very low | **0.05%** [S19] | Excellent: acid, alkali, organic solvents all rated "resistant" [S19] | **Yes**; anneal 180–220 °C [S19] | Heated chamber 60–90 °C, 310–340 °C nozzle (X1E-class) [S19] | ~€133 per 0.75 kg [S21] |
| **PEI – ULTEM 9085** (Stratasys) | 178 / 170–173 [S22] | Tg 177 [S22] | volume resistivity >6.9×10¹⁵ Ω·cm [S22] | 2.4–2.5 XZ, 2.1–2.4 ZX [S22] | Low | low [Inference] | Excellent [S22] | **Yes** | Industrial heated chamber (Fortus/F900) [S22] | Service bureau pricing [Inference] |
| **PEI – ULTEM 1010** | 215 / 213 [S23] | none given | 240 V/mil (~9.4) [S23] | ~2.7 [Inference] | Very low | low | Excellent | **Yes** | Industrial heated chamber | Service bureau pricing |
| **PEEK** (Evonik VESTAKEEP i4 3DF) | 205 / 150 (resin reference) [S24]. 3DXTech ThermaX PEEK: 140 at 0.45 as printed [S25] | Tg 143–152 [S24][S25] | 19 (IEC 60243, compounds) [S26] | 3.5–3.7 [S24][S25] | Very low once crystallized | very low | Excellent | Only after annealing/crystallization [Inference from the 140 °C as-printed HDT] | 380–400 °C nozzle, 130–140 °C bed, hot chamber [S25] | ~$400–700/kg [Inference] |
| **PEKK-A** (3DXTech) | "HDT 260" (load not stated) [S27] | Tg 162 [S27] | not given | not given | Very low | very low | Excellent | **Yes** | 345–375 °C nozzle, 70–150 °C chamber [S27] | $175 per 250 g [S27] |
| **Formlabs High Temp** (SLA) | 238 / 101 after UV + 160 °C/3 h cure; only 120 / 78 with UV cure alone [S28] | none given | not given | 2.8 [S28] | Very low | <1% in the 24 h solvent test [S28] | Formlabs publishes a solvent table [S28] | **Yes**, if thermally post-cured | SLA printer plus oven [S28] | ~$200–300/L [Inference] |
| **Formlabs Rigid 10K** (SLA) | 218 / 82–110 depending on cure [S29] | none given | not given | 10–11 [S29] | Very low | low | Solvent table in the TDS [S29] | **Yes** at 0.45 MPa; marginal at 1.8 MPa | SLA plus oven | ~$200–300/L [Inference] |
| **G10/FR4** (machined) | n/a (thermoset) | 130 (Class B) [S3] | ~19.7 (500 V/mil) [S3] | ~17–19 [Inference] | Negligible | 0.10% max/24 h [S3] | Excellent; it is epoxy | **Yes** | CNC with dust control [S3] | Cheap sheet stock; machining is the cost |
| **PA66-GF30** (molded; Zytel 70G30HSL) | – / 250 [S4] | RTI 140 (electrical) [S4] | typical for grade | ~10 [Inference] | Low | 1–2% [Inference] | Excellent; the industry standard | **Yes** | n/a (molded, catalog part) | Pennies per part in volume |
| **PA6-GF30** (molded; Zytel 73G30L) | 220 / 210 [S30] | not given | – | – | Low | – | Excellent | **Yes** | n/a | – |
| **PET/PBT-GF30** (molded, FR) | – | RTI up to 155 for FR 30% GF PET [S31] | – | – | Low | Low | Excellent | **Yes** | n/a | – |

Takeaways from the table [Inference]:

1. **Mechanical is the constraint, not electrical.** Printable options below PA-GF/CF (PLA, PETG, ASA, and effectively PC) cannot survive a real oven bake.
2. **Moisture is the hidden issue for nylons.** PA6-GF saturates at 2.56% [S15]. Wet nylon outgasses and bubbles during an impregnation bake, and it softens. Dry the bobbin immediately before impregnation.
3. **No FDM filament here has a UL RTI.** Only the molded references (PA66-GF, PET-GF, G10) come with a real long-term thermal rating. For printed parts, use HDT at 1.8 MPa minus about 20–30 °C as a practical ceiling.

### 4. Caution: carbon-fiber-filled filaments and conductivity

**Sourced facts**
- **Continuous carbon fiber is a conductor.** As-received continuous CF/nylon filament measured about 13,500 S/m. Printing reduced conductivity by about 40% because fibers broke [S32]. (Only the paper's abstract and summary were reached.)
- **Chopped-CF filaments vary widely.**
  - 3DXTech CarbonX PETG-CF lists surface resistivity >10¹⁰ Ω/sq (IEC 60093), which is effectively insulating at DC [S33].
  - Markforged had to add "a precisely controlled quantity of conductive filler" to make Onyx ESD, the static-dissipative version of its chopped-CF nylon Onyx [S34].
  - Markforged markets Onyx GF (glass) as the naturally non-conductive choice "for applications requiring robust electrical isolation" [S35].
- **CF compounds can percolate.** Carbon-filled nylon compounds can reach dissipative volume resistivity (10⁵–10⁸ Ω·cm), with percolation near 12 wt% CF [S36].

**Does it matter for a bobbin wall between copper and steel? [Inference]**
- **Magnet-wire enamel is the primary insulation.** The bobbin is the *ground insulation* between the winding and the steel yoke.
- **Enamel damage is where it matters.** Enamel nicks happen most often at bobbin corners and lead exits, under winding tension. At that point a conductive or semi-conductive bobbin can bridge copper to the core and the frame.
  - At 12–48 V this is a ground fault or a noisy leakage path, not a shock hazard.
  - It can still upset current sensing. It can also short two coils through the common yoke.
- **Chopped short-fiber CF prints are usually too resistive to act as a conductor.** Resistivity is batch-dependent and unverified, though.
- **Rules**
  1. Prefer **GF grades** (PA6-GF, Onyx GF) for bobbins.
  2. If you use CF, measure the part with a megohmmeter at 500 V.
  3. **Never** embed *continuous* carbon fiber that loops around the leg. It forms a closed conductive turn linking the core flux: a shorted secondary that adds eddy loss and slows the current-to-force response, which hurts levitation control bandwidth. The fiber is conductive enough [S32] for this to be real.

### 5. Dielectric strength is not the limiting property

**Sourced facts**
- Printed specimens 1.2 mm thick (IEC 60243, 500 V/s) broke down at [S11]:
  - ABS 30.3 kV/mm
  - PC/ABS 30.1 kV/mm
  - PETG 27.6 kV/mm
  - PLA 23.5 kV/mm
  - ASA 20.4 kV/mm
- Porous layers and interlayer interfaces reduce breakdown strength [S11].

**[Inference]**
- Even at 10 kV/mm (a porous FDM part, derated), a 1.5 mm wall withstands about 15 kV. A levitation coil driver runs at tens of volts, and transients reach perhaps a few hundred volts on turn-off.
- Choose wall thickness for **mechanics, pinholes, and abrasion**, not for kV/mm.
- Print at 100% infill, with at least 3–4 perimeters on insulating walls, to avoid through-porosity.

### 6. Caution: anisotropy and layer-line weakness

**Sourced facts**
- **Tensile strength across layers.** ULTEM 9085 breaks at 68.1 MPa in the XZ orientation but only 39.4 MPa in ZX (across layers): about 58% [S22].
- **Modulus across layers.**
  - PPS-CF: 8.23 GPa XY vs 2.85 GPa Z (35%) [S19].
  - PAHT-CF: 3.86 vs 2.18 GPa [S17].
  - PA6-GF: 2.85 vs 1.95 GPa [S15].
- **Fibers make it worse.** Fiber reinforcement *increases* anisotropy, because the fibers align in-plane [S19][S17].
- **Annealing and chamber heat help Z strength.** Bambu notes that higher chamber and nozzle temperatures increase Z-direction properties [S19]. Annealing above Tg can improve interlayer bonding [S37].

**How winding pressure loads a bobbin [Inference]**
- Wire tension produces (a) radial compression on the tube and (b) an axial push on the flanges as layers build up. Impregnation and bake add thermal-expansion stress on top.
- On a rectangular U-core leg, the flat tube walls bow inward and clamp onto the leg.
- The flange root carries a bending moment. If that root lies along a layer line, it peels off. This is the classic printed-bobbin failure.

### 7. Design advice for printed bobbins [Inference unless cited]

- **Wall thickness**
  - Tube wall: 1.2–2.0 mm FDM (3–5 perimeters of 0.4 mm), or 1.0–1.5 mm in SLA High Temp or Rigid 10K.
  - Flanges: 1.5–2.5 mm plus ribs or gussets on the outside face, rather than thicker flat plate.
  - This recovers most of the window lost to 6.35 mm acrylic.
- **Print orientation**
  - Print the bobbin **upright (tube axis = Z)**. The tube perimeters then run continuously around the leg and carry hoop compression, and both flanges print flat, with in-plane fiber alignment carrying flange bending.
  - Add **1–2 mm fillets at the flange-to-tube root** to spread the layer-line tension there.
  - Alternative: print the flanges flat as separate plates and key them onto the tube. This removes the weak root entirely.
- **Annealing**
  - Anneal per the vendor: PA6-GF and PAHT-CF at 80–130 °C for 6–12 h [S15][S17]; PPS-CF at 180–220 °C for 6–12 h [S19].
  - Vendors warn that parts can deform and warp during annealing [S15][S19]. Anneal *on the leg dummy* or in a fixture, and anneal **before** winding.
  - Anneal at or above the planned bake temperature so the bobbin does not shrink onto the core during impregnation.
  - PEEK must be annealed or crystallized. Printed ThermaX PEEK shows only 140 °C HDT [S25], vs 205 °C at 0.45 MPa for the resin [S24].
  - SLA High Temp needs its 160 °C/3 h thermal cure to reach 238 °C HDT [S28].
- **Fit onto the yoke leg**
  - Design 0.2–0.4 mm diametral/side clearance for FDM (0.1–0.2 mm for SLA). Then test-fit *after* winding a dummy layer, because tension bows the walls inward.
  - Chamfer the leading edge of the bore.
  - Wrap the leg in one layer of Kapton or Nomex tape if the steel edges are sharp. This also protects against enamel nicks.
- **Split or two-piece designs**
  - Split along the tube axis (two C-halves), or use a tube plus separate flanges. Either lets you wind on a mandrel and slide the coil on, or print each piece in its strongest orientation.
  - Fix halves with epoxy plus alignment pins or dovetails. Impregnation then locks everything.
- **Joints**
  - Prefer **bolted or pinned joints** with heat-set brass inserts over snap fits.
  - Snap fits creep and relax at 100–150 °C and in wet nylon.
  - Keep all fasteners non-magnetic and outside the flux path. Brass or stainless 300-series fasteners are fine.
- **Lead-exit slots**
  - Cut the start-lead slot through the flange with a 1 mm radius, not a sharp notch, and route it out tangentially.
  - Add a small ramp so the lead does not cross the winding at a sharp angle.
  - Put the finish-lead exit on the outside face with a strain-relief boss or a tie-wrap anchor.
  - Round every edge the wire touches to at least 0.5 mm radius.

### 8. Examples of printed bobbins and coil formers in practice

- **Physics lab coil.** A fast Feshbach coil for a quantum-gas experiment was wound on an **FDM PLA** printed mount, chosen for ease and low cost, and fixed with epoxy [S38]. It worked because the duty cycle was 2% and the coil rose at most about 25 °C above room temperature [S38]. PLA suits low-duty coils only.
- **Commercial coil suppliers.**
  - Prem Magnetics offers 3D-printed custom bobbins for transformers, inductors and coils in PLA, ABS, PA, PC, PLA-CF, PETG-CF and ASA [S39].
  - Remington Industries also sells 3D-printed bobbins and spools for coils [S40].
  - Neither publishes thermal ratings for them [S39][S40].
- **Student-scale maglev.** The "Mini Hyperloop" maglev project combines 3D-printed structure with custom-wound electromagnets on milled iron cores [S41]. The bobbin material is not stated.
- **Research on printed electromagnetics.**
  - MIT printed complete solenoids, using PLA as the dielectric layer [S42].
  - A 2026 fully printed wave-wound motor used carbon-filled nylon as the insulating substrate, chosen for thermal conductivity and operating temperature [S43]. This again shows that CF-nylon resistivity has to be checked case by case.

### 9. Recommendation [Inference, built on the facts above]

**Acrylic vs printed.** Move off acrylic for any coil that will be impregnated, baked, or run continuously.
- Acrylic's 82 °C continuous rating and 99 °C HDT [S7] leave no margin for a 110–150 °C bake [S5][S6].
- Its solvent-crazing list covers typical varnish solvents [S7].
- It is notch-brittle [S7].
- The 6.35 mm stock costs roughly half the copper window in the example above.
- Keep acrylic only for jigs, winding mandrels, or a throwaway first test coil.

**Hobby-printer tier** (enclosed Bambu P1S/X1C or Prusa Core One class, hardened nozzle)
1. **First choice: PA6-GF or PAHT-CF.** HDT 158–170 °C at 1.8 MPa [S15][S17], so they survive a 120–150 °C bake.
   - Prefer the **GF** grade for guaranteed insulation.
   - PAHT-CF absorbs less water (0.88% vs 2.56%) [S17][S15], but megger-test it.
   - Dry the filament, anneal the part, and dry the part again right before impregnation.
2. **If the team uses room-temperature-cure epoxy and no bake, and the coil stays below about 70 °C: PC or ASA.** They are easy to print. PC has the higher HDT (113/93 °C) [S14].
3. **Avoid for powered coils: PLA and PETG.** HDT is 55 and 68 °C [S10][S12].

**Better-equipped tier** (heated-chamber FDM, SLA with oven, or a service bureau)
1. **ULTEM 9085 or 1010 (PEI).** This is the best all-round printed bobbin: HDT 170–215 °C, very high resistivity, UL-grade flame behavior [S22][S23].
2. **PPS-CF.** It is outstanding thermally and chemically: HDT 235 °C at 1.8 MPa, 0.05% water [S19]. Megger-test it for CF leakage, or look for a GF-filled PPS.
3. **Formlabs High Temp (thermally post-cured).** HDT 238 °C at 0.45 MPa [S28]. It suits small, precise bobbins with filleted flanges, but it is brittle: 2.3% elongation [S28].
4. **PEKK-A** is easier to print than PEEK and is bake-proof [S27]. PEEK only makes sense if the part is properly crystallized [S24][S25].
5. **Non-printed gold standard: CNC-machined G10/FR4** tube-and-flange (Class B, 130 °C) [S3], or a **catalog molded PA66-GF / PET-GF bobbin** (RTI 140–155 °C) [S4][S31] if the yoke leg matches a standard size. Laser-cutting G10/FR4 is not advisable: it chars, and FR4 contains brominated resin [Inference]. Machine it wet, with dust extraction [S3].

### Sources

1. [S1] UL Solutions, "Electrical Insulation Systems (EIS) Product Standards" (UL 1446). https://www.ul.com/resources/electrical-insulation-systems-eis-product-standards; In Compliance Magazine, "Properly Specifying Electrical Insulation Systems". https://incompliancemag.com/practical-engineering-properly-specifying-electrical-insulation-systems/
2. [S2] Schmidbauer, "UL insulation systems for transformers/chokes/coils according to UL 1446". https://www.schmidbauer.net/en/ul-insulationsystems-for-transformers-chokes-coils-in-according-to-ul-1446/
3. [S3] Ready Plastics, "G10 Properties — Mechanical, Electrical and Thermal". https://www.readyplastics.com/resources/materials/g10/properties
4. [S4] Celanese/DuPont Zytel 70G30HSL NC010 technical datasheet (SpecialChem). https://www.specialchem.com/plastics/product/celanese-zytel-70g30hsl-nc010
5. [S5] John C. Dolph Co., "Impregnating Varnishes & Resins Selection Chart". https://www.electro-wind.com/web-files/Dolph's/Literature/varnish-resin-guide.pdf
6. [S6] EIS, ELANTAS PDG Ripley E468-2 epoxy impregnating resin. https://www.eis-inc.com/product/epoxy-impregnating-resin-ph21-ripley-e468-2
7. [S7] ACRYLITE cast (cell-cast acrylic) Physical Properties, incl. chemical resistance table. https://www.acrylite.co/files/content/acrylite.co/documents/product-information/ACRYLITE-cast-Physical-Properties.pdf
8. [S8] ACRYLITE premium (FF) Technical Information. https://www.acrylite.co/files/content/acrylite.co/documents/product-information/ACRYLITE-Premium-FF-Technical%20Information.pdf
9. [S9] ACRYLITE, "Annealing" Technical Information 1319-12E. https://www.acrylite.co/files/content/acrylite.co/documents/fabrication-briefs/Extruded-Fabrication-Annealing-Technical-Information.pdf
10. [S10] Prusament PLA Technical Datasheet. https://prusament.com/wp-content/uploads/2022/10/PLA_Prusament_TDS_2021_10_EN.pdf
11. [S11] "Integrated Evaluation of Electrical Breakdown Strength and Mechanical Properties of 3D-Printed Polymers" (PMC). https://pmc.ncbi.nlm.nih.gov/articles/PMC13259274/
12. [S12] Prusament PETG Technical Datasheet. https://prusament.com/wp-content/uploads/2022/10/PETG_Prusament_TDS_2021_10_EN.pdf
13. [S13] Prusament ASA Technical Datasheet. https://prusament.com/wp-content/uploads/2022/10/ASA_Prusament_TDS_2022_16_EN.pdf
14. [S14] Prusament PC Blend Technical Datasheet. https://prusament.com/wp-content/uploads/2022/10/PCBlend_Prusament_TDS_2022_16_EN.pdf
15. [S15] Bambu Lab PA6-GF Technical Data Sheet. https://wiki.bambulab.com/filament-acc/absgf-pa6gf/bambu_pa6-gf_technical_data_sheet.pdf
16. [S16] Bambu Lab PA-CF Technical Data Sheet (via Additive-X). https://www.additive-x.com/shop/mpattachments/file/viewonline/id/643/product_id/2450/
17. [S17] Bambu Lab PAHT-CF Technical Data Sheet V3.0. https://wiki.bambulab.com/filament-acc/asacf-pahtcf/65f1b18a6d6142d794a1a6a00f1496ef.pdf
18. [S18] Fiberlogy PA12 (via Filament2Print). https://filament2print.com/en/nylon-pa/2394-fiberlogy-pa12.html
19. [S19] Bambu Lab PPS-CF Technical Data Sheet. https://store.bblcdn.eu/s8/default/623b28bf2fbe495fa9dd559a85f494ed/Bambu_PPS-CF_Technical_Data_Sheet.pdf
20. [S20] Bambu Lab, "Comprehensive Guide to PPS-CF". https://bambulab.com/en/filament/pps-cf
21. [S21] Welectron listing, Bambu Lab PPS-CF. https://www.welectron.com/Bambu-Lab-PPS-CF-Filament-on-Spool
22. [S22] Stratasys ULTEM 9085 Resin Material Data Sheet. https://www.stratasys.com/contentassets/264560ca109a4876a3761fde68c3ab5e/mds_fdm_ultem9085_0525a.pdf
23. [S23] Stratasys ULTEM 1010 Resin Data Sheet. https://www.stratasys.com/siteassets/materials/materials-catalog/fdm-materials/ultem1010/mds_fdm_ultem-1010-resin_0921a.pdf
24. [S24] Evonik VESTAKEEP i4 3DF TDS. https://www.evonik.com/content/dam/evonik/documents/tds-vestakeep-i4-3DF.pdf
25. [S25] 3DXTech ThermaX PEEK TDS (via Rev1Tech). https://support.rev1tech.com/portal/en/kb/articles/thermax-peek
26. [S26] Evonik, VESTAKEEP PEEK Compounds brochure. https://products.evonik.com/assets/35/91/VESTAKEEP_Compounds_EN_EN_243591.pdf
27. [S27] 3DXTech ThermaX PEKK-A product page. https://www.3dxtech.com/products/pekk-a
28. [S28] Formlabs High Temp Resin TDS. https://formlabs-media.formlabs.com/datasheets/1801087-TDS-ENUS-0P.pdf
29. [S29] Formlabs Rigid 10K Resin TDS. https://formlabs-media.formlabs.com/datasheets/2001479-TDS-ENUS-0.pdf; "Using Rigid 10K Resin". https://formlabs.com/support/Using-Rigid-10k-Resin/
30. [S30] DuPont Zytel 73G30L NC010 datasheet. https://upmold.com/wp-content/uploads/data-sheet/PA66-GF30-Zytel%2073G30L%20NC010.pdf
31. [S31] DuPont, "Design Information: Crastin PBT and Rynite PET". https://www.distrupol.com/Crastin_PBT_and_Rynite_PET_Design_Info_Module_IV.pdf
32. [S32] "Electrical properties of 3D printed continuous carbon fibre composites made using the FDM process", Composites Part A (2021). https://www.sciencedirect.com/science/article/abs/pii/S1359835X2100378X
33. [S33] 3DXTech CarbonX CF-PETG datasheet (UL Prospector). https://www.ulprospector.com/plastics/en/datasheet/379505/carbonx-carbon-fiber-reinforced-petg-3d-filament
34. [S34] Markforged, "Introducing Onyx ESD". https://markforged.com/resources/blog/introducing-onyx-esd
35. [S35] Markforged, "Onyx GF". https://markforged.com/materials/plastics/onyx-gf; https://markforged.com/resources/news-events/markforged-introduces-onyx-gf-bringing-functional-color-and-industrial-strength-to-the-factory-floor
36. [S36] "Electrical conductivity of carbon filled nylon 6,6" (ResearchGate). https://www.researchgate.net/publication/230340897_Electrical_conductivity_of_carbon_filled_nylon_66
37. [S37] "Optimisation of Strength Properties of FDM Printed Parts — A Critical Review", Polymers 13(10):1587. https://www.mdpi.com/2073-4360/13/10/1587
38. [S38] "A compact and fast magnetic coil for the interaction manipulation of quantum gases with Feshbach resonances", arXiv:2103.05273. https://arxiv.org/pdf/2103.05273
39. [S39] Prem Magnetics, "3D Printing & Additive Manufacturing". https://www.premmagnetics.com/3d-printing-services/
40. [S40] Remington Industries, "3D Printed Bobbins & Custom Plastic Spools". https://www.remingtonindustries.com/3d-printed-bobbins-spools/
41. [S41] Hackaday.io, "Mini Hyperloop – Magnetic Levitation Train". https://hackaday.io/project/181257-mini-hyperloop-magnetic-levitation-train
42. [S42] MIT News, "MIT engineers 3D print the electromagnets at the heart of many electronics" (2024). https://news.mit.edu/2024/mit-engineers-3d-print-electromagnets-solenoids-0223
43. [S43] Schwalbe et al., "Fully 3D-Printed Wave-Wound Electromagnetic Motors", Advanced Materials Technologies. https://advanced.onlinelibrary.wiley.com/doi/10.1002/admt.70994

---


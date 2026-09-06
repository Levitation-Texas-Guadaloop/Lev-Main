# Maglev - PM Bias and Force Linearization

*Support doc for [[Levitation Research Claude]] — answers Section A questions on PM-bias linearization and stiffness derivation.*

---

## 1. Where Does F = k(i/x)² Come From?

Start from Maxwell's stress tensor (or equivalently, the co-energy of a magnetic circuit). For a simple U-shaped yoke with a single coil of N turns and an air gap x:

 
**Reluctance of the air gap** (dominant term, assuming high-permeability steel):


$$\mathcal{R}(x) = \frac{2x}{\mu_0 A}$$

where A is the pole-face area. The factor of 2 counts two air-gap crossings (each side of the U).
**==Using 1018 ANSI steel with a 1" cross section. Can we still neglect non-air reluctances? Also, we definitely can NOT ignore the significant reluctance induced by the PM right? ==**

> **Answer.**
>
> **Steel — borderline-neglectable, flux-dependent.** The relevant comparison is the ratio
> $$\frac{\mathcal{R}_{steel}}{\mathcal{R}_{air}} = \frac{l_{iron}/(\mu_0\mu_r A)}{2x/(\mu_0 A)} = \frac{l_{iron}}{2x\,\mu_r}$$
> For 1018 (μ_r ≈ 500–1000 while unsaturated), l_iron ≈ 0.2 m, 2x = 6 mm:
> - μ_r = 1000 → ~3% of the gap reluctance
> - μ_r = 500 → ~7%
> - μ_r = 200 (near saturation) → ~17%
>
> So neglecting steel is fine to first order (~5%), **but only while unsaturated.** 1018 μ_r collapses as pole-face B approaches ~1.5–2 T. Check B at the pole faces; if you're pushing flux (which PM bias does — see below), include the steel as a lumped series reluctance. It's not automatically negligible here.
>
> **PM — correct, cannot ignore.** A sintered NdFeB magnet has recoil permeability μ_rec ≈ 1.02–1.05, i.e. magnetically it behaves like an *air gap of its own length*. Your `Diagram_1.png` puts a **1" PM in each leg** — 2" (0.051 m) of magnet in the loop:
> $$\mathcal{R}_{pm} = \frac{l_{pm}}{\mu_0\mu_{rec}A} \approx 6\times10^7 \text{ A/Wb} \approx 8\,\mathcal{R}_{air}\ (\text{at } x=3\text{ mm})$$
> The PM reluctance doesn't just rival the working gap — it *dominates* the loop (~89% of total). It must be in the network. See **§4b / §7** for the full consequences.
>
> Consequence: model the PM as a Thévenin source — MMF $F_{pm} = H_c l_{pm}$ in series with $\mathcal{R}_{pm}$ — not as a fixed flux. This means the doc's shorthand **Φ_b = B_r·A (line 48) is the short-circuit flux and overstates the actual bias.** The true Φ_b is the loadline intersection:
> $$\Phi_b = \frac{H_c\,l_{pm}}{\mathcal{R}_{pm} + \mathcal{R}_{air} + \mathcal{R}_{steel}}$$

**Inductance** of the coil:

$$L(x) = \frac{N^2}{\mathcal{R}(x)} = \frac{\mu_0 A N^2}{2x}$$

**Co-energy** stored in the magnetic field:

$$W^*(i, x) = \frac{1}{2} L(x) i^2 = \frac{\mu_0 A N^2}{4x} i^2$$

**Force** on the armature (at constant current — i.e., the electrical supply holds i fixed during the virtual displacement):

$$F = \frac{\partial W^*}{\partial x}\bigg|_i = -\frac{\mu_0 A N^2}{4x^2} i^2$$

The negative sign means the force is *attractive* (pulling the gap closed, reducing x). Absorbing constants into k:

$$\boxed{F = -\frac{k \, i^2}{x^2}, \quad k = \frac{\mu_0 A N^2}{4}}$$

This is the canonical result. Force increases with i², decreases with x² — a strongly nonlinear, attractive-only relationship.

> **Note:** this clean 1/x² form assumes the air gap is the *only* reluctance. It is not — the PM and steel add a large series reluctance ℛ₀. The generalized law and its effect on the stiffnesses are in **§4b**; for this yoke the gap is only ~11% of the loop reluctance.

---

## 2. The PM-Bias Idea

Without a permanent magnet, the coil current i is bipolar: you need positive current to attract, but you cannot repel (force is always attractive). More importantly, the i² law means force is *even* in i — you cannot linearize around i=0 because dF/di|₀ = 0.

A permanent magnet pre-loads the circuit with a steady bias flux Φ_b. Now the total flux through the gap is:

$$\Phi_{total} = \Phi_b + \Phi_{coil}(i)$$

where Φ_coil = NiA/ℛ = μ₀ANi/(2x) and Φ_b = B_r·A (residual flux density of the PM, roughly constant for small perturbations).

**Force as a function of total flux:**

$$F = \frac{\Phi_{total}^2}{2\mu_0 A} = \frac{(\Phi_b + \Phi_{coil})^2}{2\mu_0 A}$$

*(Per air-gap face. The U-core has two faces, so the total attractive force is twice this — F = Φ²/μ₀A, as used in §4b. The factor cancels in the linearity ratio below, so it doesn't affect this section's conclusion.)*

Expand:

$$F = \underbrace{\frac{\Phi_b^2}{2\mu_0 A}}_{\text{constant bias force}} + \underbrace{\frac{\Phi_b \cdot \Phi_{coil}}{\mu_0 A}}_{\text{linear in } i} + \underbrace{\frac{\Phi_{coil}^2}{2\mu_0 A}}_{\text{quadratic, small if } \Phi_{coil} \ll \Phi_b}$$

The **cross-term** is linear in the coil current i. If Φ_b ≫ Φ_coil (operating well within the linear range of the bias), the quadratic term is negligible and **F is approximately linear in i**. This is the linearization the PM provides.
> **==What is a good way to characterize or compute the \phi_b vs \phi_coil? And how can I conclude that it is negligible?==**
>
> **Answer.** The exact criterion is the ratio of the quadratic term to the linear term in the §2 expansion:
> $$\frac{\Phi_{coil}^2/(2\mu_0 A)}{\Phi_b \Phi_{coil}/(\mu_0 A)} = \frac{\Phi_{coil}}{2\Phi_b}$$
> So the **fractional force nonlinearity is ≈ Φ_coil/(2Φ_b)**, evaluated at your *maximum* operating current. Pick a tolerance and size accordingly:
> - Want < 5% nonlinearity over the current swing → need Φ_coil,max / Φ_b < 0.1.
>
> **Computing the two fluxes:**
> - **Φ_b** — from the PM loadline above: $\Phi_b = H_c l_{pm} / \mathcal{R}_{total}$, with $\mathcal{R}_{total} = \mathcal{R}_{pm} + \mathcal{R}_{air} + \mathcal{R}_{steel}$.
> - **Φ_coil** — driven through the *same* network: $\Phi_{coil} = N i / \mathcal{R}_{total}$. Evaluate at i = I_max.
>
> Both share ℛ_total, so the ratio simplifies cleanly:
> $$\frac{\Phi_{coil}}{\Phi_b} = \frac{N\,I_{max}}{H_c\,l_{pm}}$$
> i.e. **it reduces to coil MMF vs. magnet MMF** — a quantity you can read off directly from turns, current, coercivity, and magnet length. No network solve needed for the ratio itself.
>
> **Empirical check:** put a Hall probe in the gap. B with coil off = B_b; the slope ΔB/Δi = B_coil per amp. Confirm B_coil·I_max / B_b matches the MMF ratio, and that total pole-face B stays clear of saturation.
>
> **Design tension:** large Φ_b buys linearity but also raises k_s (worse instability, §4) and pushes the steel toward saturation. Don't oversize the magnet — set Φ_b to just meet the linearity target.

Pictorially: the bias flux "shifts" the operating point away from i=0 (where the nonlinearity is worst) to a region where the F-vs-i curve has a meaningful, non-zero slope.

---

## 3. Formal Linearization Around the Operating Point (I_b, s₀)

In an EMS/AMB context the "bias current" equivalent I_b is the DC coil current (or PM-equivalent current) at the operating gap s₀. Linearize F(i, x) about (I_b, s₀):

$$F(i, x) \approx F(I_b, s_0) + \underbrace{\frac{\partial F}{\partial i}\bigg|_{I_b, s_0}}_{k_i} (i - I_b) + \underbrace{\frac{\partial F}{\partial x}\bigg|_{I_b, s_0}}_{k_s} (x - s_0)$$

At equilibrium F(I_b, s₀) = mg (supports the weight). Define small signals δi = i − I_b, δx = x − s₀. Then:

$$\delta F = k_i \, \delta i + k_s \, \delta x$$

---

## 4. The Stiffness Coefficients — Derived

Starting from the full expression F = −μ₀AN²i²/(4x²):

### Current stiffness k_i (force-per-amp at the bias point)

$$k_i = \frac{\partial F}{\partial i}\bigg|_{I_b, s_0} = -\frac{\mu_0 A N^2 \cdot 2I_b}{4 s_0^2} = -\frac{\mu_0 A N^2 I_b}{2 s_0^2}$$

This is **positive** in the AMB convention where *increasing i increases attractive force toward the rail* (force and displacement toward rail are taken as positive). The sign depends on coordinate convention; the magnitude is what matters:

$$|k_i| = \frac{\mu_0 A N^2 I_b}{2 s_0^2}$$

k_i is positive: more current → more force. This is the "good" stiffness — it's what the controller actuates.

### Position stiffness k_s (force-per-metre of gap change)

$$k_s = \frac{\partial F}{\partial x}\bigg|_{I_b, s_0} = \frac{\mu_0 A N^2 I_b^2}{2 s_0^3}$$

This is **negative** in the physical sense: if the gap x *decreases* (pod moves toward rail), force *increases* — pulling the pod further in. A restoring force would have the opposite sign. This is the "negative stiffness" that makes the plant open-loop unstable.

> **Useful identity:** k_s / k_i = I_b / s₀.  
> This means the unstable pole √(k_s/m) = √(k_i·I_b / (m·s₀)). Increasing bias current I_b simultaneously increases both stiffnesses and ~~worsens~~ augments the instability — it doesn't help unless you also raise the controller bandwidth.
> **==This is OK. We are generally going to aim for an s₀ where I_b = 0==**
>
> **Answer — careful, this needs disambiguation.** There are two different "bias currents" and they must not be conflated:
> - **Coil DC current at hover** — the steady current the *coil* carries to hold the pod at s₀. Aiming for this = 0 is the **zero-power / PM-biased design goal**: the PM alone supports mg at s₀, coil DC = 0, no I²R at hover. Correct and desirable.
> - **I_b in the k_i / k_s formulas** — this is the *total bias* setting the bias flux Φ_b, which for your design is the **PM-equivalent current I_pm**, not the coil DC. It is *not* zero.
>
> **If you literally drove I_b → 0 (total bias flux zero), the scheme collapses:** k_i ∝ I_b → 0, so dF/di → 0 and you're back on the pure i² law with no linear actuation authority. The PM's entire job is to keep I_b ≠ 0.
>
> **So the correct statement is:** choose s₀ (and magnet sizing) so the *coil DC* is zero at hover, while the PM supplies I_b = I_pm. Then:
> - k_i, k_s are fixed by **I_pm**, not by coil current.
> - The RHP pole $\sqrt{k_s/m}$ **remains** — zeroing the coil current does not remove the instability. You still stabilize actively; you just do it with δi swinging around 0.
> - **The identity's "bigger bias → worse instability" warning is actually reversed once ℛ_pm is included.** At the weight-supporting point the pole is √(2gη/s₀) (§4b) — it depends on η, not directly on PM strength. A longer/stronger magnet *raises* ℛ₀ and *lowers* η, so it makes the instability **milder**, not worse (Φ_b just saturates toward B_r·A). The real cost of oversizing the PM is loss of force-per-amp (k_i ∝ η), not a faster pole.

---

## 4b. Propagating the PM + Steel Reluctance into F and the Stiffnesses

Because ℛ_pm is comparable to — here, *larger* than — the gap reluctance, the clean 1/x² law of §1 is only the **ℛ₀ → 0 limit**. Carry the full series reluctance through.

**Geometry (from `Diagram_1.png`):** U-core, 1"×1" pole faces (A = 1 in² = 6.45 cm²), a **1" PM in each leg** (so l_pm = 2" total in the loop), 1018 base/legs, N = 250. Flux path: up one leg → gap → rail → gap → down the other leg → across the base.

**Full reluctance and MMF:**

$$\mathcal{R}(x) = \underbrace{\frac{2x}{\mu_0 A}}_{\text{two gaps}} + \mathcal{R}_0, \qquad \mathcal{R}_0 = \mathcal{R}_{pm} + \mathcal{R}_{steel}$$

$$\mathcal{R}_{pm} = \frac{l_{pm}}{\mu_0 \mu_{rec} A}, \quad \mathcal{R}_{steel} = \frac{l_{iron}}{\mu_0 \mu_r A}, \quad \mathcal{F}(i) = Ni + \mathcal{F}_{pm}, \quad \mathcal{F}_{pm} = H_c\, l_{pm}$$

**Flux and force** (energy method — only the gap term depends on x, so $F = \tfrac{1}{2}\Phi^2\, d\mathcal{R}/dx$):

$$\Phi(i,x) = \frac{Ni + \mathcal{F}_{pm}}{\frac{2x}{\mu_0 A} + \mathcal{R}_0}, \qquad \boxed{F(i,x) = \frac{\Phi^2}{\mu_0 A} = \frac{1}{\mu_0 A}\left(\frac{Ni + \mathcal{F}_{pm}}{\frac{2x}{\mu_0 A} + \mathcal{R}_0}\right)^2}$$

Set ℛ₀ = 0 and this collapses to the §1 result (with bias). ✓

**One number captures the whole effect — the gap-reluctance fraction:**

$$\eta \equiv \frac{\mathcal{R}_{gap}(s_0)}{\mathcal{R}(s_0)} = \frac{2s_0/(\mu_0 A)}{2s_0/(\mu_0 A) + \mathcal{R}_0} \in (0, 1]$$

η = 1 is the idealized core of §1–§4. Here η ≈ 0.11 (see §7).

**The linearized stiffnesses each pick up a factor η:**

$$k_i = \frac{2\Phi_0 N}{\mu_0 A\, \mathcal{R}(s_0)} = \eta \cdot k_i^{\text{ideal}}, \qquad |k_s| = \frac{4\Phi_0^2}{(\mu_0 A)^2 \mathcal{R}(s_0)} = \eta \cdot k_s^{\text{ideal}}$$

At the weight-supporting equilibrium (F₀ = Φ₀²/μ₀A = mg) the position stiffness and unstable pole take a clean geometry-independent form:

$$|k_s| = \frac{2mg\,\eta}{s_0}, \qquad \omega_{unstable} = \sqrt{\frac{k_s}{m}} = \sqrt{\frac{2g\,\eta}{s_0}}$$

**Consequences:**

- **Both stiffnesses are diluted equally by η.** The §5 equation of motion keeps its exact form; only the k-values shrink.
- **The instability is milder.** The RHP pole drops by √η — a long PM trades force authority for a lower required control bandwidth. Here the pole falls from ~12.9 Hz (η=1) to ~4.3 Hz.
- **…but k_i shrinks by the same η.** Force-per-amp falls proportionally, so you need more current for a given control force. This is the price of the series reluctance.
- **The §4 identity survives in form.** k_s/k_i is η-independent (both scale together); the *absolute* stiffnesses do not.
- **Steel is the minor partner.** ℛ_steel ≪ ℛ_pm here (§7), so ℛ₀ ≈ ℛ_pm. Steel only matters if a pole face saturates and μ_r collapses.

---

## 5. The Linearized Equation of Motion

**Coordinate convention — pin this before any controller work.** Let the raw air gap be $x_g$, positive when open (pod below rail) — the vault-wide convention. The force $F(i, x_g)$ is *attractive* (acts to close the gap), and "up" is the $-x_g$ direction. The exact nonlinear vertical EoM is therefore

$$m\ddot{x}_g = mg - F(i, x_g)$$

— gravity opens the gap, the magnet closes it. **This is the equation the simulation integrates.** At equilibrium $F(I_b, s_0) = mg$.

**Control coordinate.** For control it is cleaner to use displacement from the hover point, positive up: $\delta z \equiv -\delta x_g = -(x_g - s_0)$. Linearizing $F$ and using $\delta\ddot{x}_g = -\delta\ddot{z}$:

$$m\,\delta\ddot{z} = k_s\,\delta z + k_i\,\delta i, \qquad k_i \equiv \frac{\partial F}{\partial i}\bigg|_0 > 0, \quad k_s \equiv -\frac{\partial F}{\partial x_g}\bigg|_0 = \frac{2mg\,\eta}{s_0} > 0$$

Both stiffnesses are positive in this coordinate. Transfer function (this is the plant every downstream control doc uses):

$$\frac{\delta Z(s)}{\delta I(s)} = \frac{k_i}{ms^2 - k_s}, \qquad \text{poles } s = \pm\sqrt{k_s/m}$$

The $+\sqrt{k_s/m}$ pole is the RHP (unstable) pole — the mathematical origin of the maglev instability.

> **Sign bookkeeping — the one thing that flips a feedback loop.** The control plant above is in up-displacement $\delta z$. If you instead close the loop directly on the measured *gap* $x_g$, the input gain flips sign:
> $$\frac{\delta X_g(s)}{\delta I(s)} = \frac{-k_i}{ms^2 - k_s}$$
> Use **one** coordinate end-to-end. Canonical choice for this project: the **sim state is the gap $x_g$** (it owns the nonlinear physics); the **linear controller is designed in $\delta z = -\delta x_g$**, with the sign flip applied at the sim↔controller boundary (measurement `δz = s₀ − x_g`, and the controller's force/current command drives $-x_g$).

---

## 6. Why PM Bias Specifically Helps the Controller

Besides linearizing F(i), the PM bias provides:

1. **Force at zero coil current.** The PM holds the pod at partial levitation even if the coil is de-energized — a safety benefit and a power-saving opportunity.

2. **Bidirectional force actuation.** The coil modulates Φ_coil around the PM-set Φ_b. *Reducing* coil current below its bias level decreases total flux and thus decreases force; *increasing* it above the bias increases force. So the coil effectively pushes and pulls the pod relative to its bias equilibrium — even though magnetic force is always attractive.

3. **Force-current linearity in the operating range.** As shown in §2, the cross-term dominates when Φ_b ≫ Φ_coil. This is the Calnetix statement: "primary purpose is to linearize the applied force vs. coil current relationship of the actuator."

4. **Reduced I²R heating.** Less coil current needed at hover (the PM does the heavy lifting), which keeps the coils cooler and keeps R (and thus the R/L time constant) more predictable.

---

## 7. Sanity Check: Numbers (this yoke, per core)

Actual geometry from `Diagram_1.png`, one 1"-deep core (stack N of them for a heavier pod — force and mass scale together, so the pole is unchanged):
- A = 1 in² = 6.45×10⁻⁴ m²
- l_pm = 2 × 1" = 0.051 m total (both legs), μ_rec ≈ 1.05, NdFeB N42 (B_r ≈ 1.3 T)
- l_iron ≈ 0.15 m, μ_r ≈ 800 (1018, unsaturated)
- N = 250, s₀ = 3 mm (illustrative design gap)

**Reluctance budget** (this is the whole story):

| Term | Value (A/Wb) | Share |
|---|---|---|
| ℛ_gap (2×3 mm) | 7.4×10⁶ | 11% |
| ℛ_pm (2×1" NdFeB) | 6.0×10⁷ | 89% |
| ℛ_steel | 2.3×10⁵ | <1% |
| **ℛ_total** | **6.7×10⁷** | → **η ≈ 0.11** |

**Bias operating point** (coil off, PM loadline):

$$\mathcal{F}_{pm} = H_c l_{pm} \approx 5.0\times10^4 \text{ A}, \quad \Phi_b = \frac{\mathcal{F}_{pm}}{\mathcal{R}_{total}} \approx 0.74 \text{ mWb}, \quad B_b \approx 1.15 \text{ T}$$

(1.15 T is a healthy bias but watch the pole-face knee — this is where steel μ_r would collapse.) The bias supports **F₀ ≈ 680 N per core** (≈ 69 kg), so a heavier pod needs several cores stacked.

**Stiffnesses (with η ≈ 0.11 already folded in):**

$$k_i \approx 6.8 \text{ N/A}, \qquad |k_s| \approx 5.0\times10^4 \text{ N/m}$$

$$\omega_{unstable} = \sqrt{2g\eta/s_0} \approx 27 \text{ rad/s} \approx 4.3 \text{ Hz} \quad (\text{vs. } 12.9 \text{ Hz if } \eta = 1)$$

**Linearity check** (§2 criterion): Φ_coil/Φ_b = Ni/ℱ_pm ≈ 0.5% per amp, so ±10 A gives only ~5% flux modulation → force is very linear, but note k_i is correspondingly small (weak authority — the flip side of large ℛ_pm).

The unstable mode is ~4.3 Hz — the minimum closed-loop bandwidth to stabilize. Current-loop bandwidth needs 5–10× this (~20–45 Hz minimum), trivially met by a PWM current loop. The PM reluctance has *relaxed* the control requirement relative to the idealized core, at the cost of force-per-amp.

> **Grade flag: this table assumes N42 (B_r ≈ 1.3 T).** The actual magnet in use is **N52** (B_r typically ≈ 1.42–1.48 T, confirm off the supplier datasheet) — every number here that depends on Φ_b (B_b, F₀, k_i, k_s) should eventually be recomputed with the correct B_r/H_c. Taken at face value, higher B_r should push Φ_b/B_b *up* (Φ_b saturates toward B_r·A as l_pm grows, §4 answer), predicting an even higher bias than the 1.15 T worked here.
>
> **However:** IRL Gauss-meter testing on the actual hardware shows the real pole-face field, even at maximum coil current, is well *under* 1.15 T — the opposite direction from what the N42→N52 swap alone would predict. This suggests the reluctance-network model above is overestimating Φ_b relative to the built hardware (candidates: unmodeled leakage flux, joint air gaps between PM and steel sections not captured by the ideal series-reluctance model, or B_r/H_c deviating from catalog values). That's a model-accuracy question worth its own follow-up characterization pass — it does **not** block sensor selection, which the IRL measurement has already resolved (see [[Maglev - Hall Sensor Selection]] Appendix A). Don't use the worked numbers above as committed design values until this gap is understood.

---

*See also: [[Maglev - Coupling and Geometry]] (why 4 actuators in a rigid body still couple despite separate power supplies)*

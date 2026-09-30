# Maglev - Control Allocation and MIMO

*Support doc for [[Levitation Research Claude]] — expands the two-sentence treatment of `f = B⁺u + f_null` in [[Maglev - Coupling and Geometry]] §2 into the full allocation + MIMO picture. Read that doc first for *why* the 4→3 coupling exists; this doc is *how* you resolve it.*

---

## 1. Where allocation sits in the stack

The layered architecture separates three concerns that must not be mixed:

$$\underbrace{(z,\theta,\phi)}_{\text{estimate}} \xrightarrow{\text{stabilizer}} \underbrace{\mathbf{u}=[F_z, M_\phi, M_\theta]^\top}_{\text{generalized wrench (3)}} \xrightarrow{\text{allocator}} \underbrace{\mathbf{f}=[f_1..f_4]^\top}_{\text{corner forces (4)}} \xrightarrow{\text{actuator inv.}} \underbrace{[i_1..i_4]}_{\text{coil currents}} \xrightarrow{\text{current loop}} \text{PWM}$$

- **The stabilizer** (LQR / ADRC / MPC) knows the *dynamics*. It works in 3 modal coordinates and outputs 3 numbers — a desired force + two moments. It neither knows nor cares how many magnets exist.
- **The allocator** knows the *geometry and the actuator limits*. It is (mostly) a static map from 3 demands to 4 forces.
- Keeping these separate is what makes a coupled 4-actuator plant designable as if it were 3 independent SISO loops. Control allocation as a discipline: Härkegård, Bodson.

---

## 2. The effectiveness matrix B

Stack the rigid-body equilibrium equations from [[Maglev - Coupling and Geometry]] §1 as $\mathbf{u} = B\mathbf{f}$:

$$\begin{bmatrix} F_z \\ M_\phi \\ M_\theta \end{bmatrix} = \underbrace{\begin{bmatrix} 1 & 1 & 1 & 1 \\ \ell_x & -\ell_x & \ell_x & -\ell_x \\ \ell_y & \ell_y & -\ell_y & -\ell_y \end{bmatrix}}_{B,\ 3\times 4} \begin{bmatrix} f_1 \\ f_2 \\ f_3 \\ f_4 \end{bmatrix} \qquad (\text{order } [FL,FR,RL,RR])$$

- **B is "wide" (3×4), rank 3.** Given a demand **u**, the equation $B\mathbf{f}=\mathbf{u}$ has *infinitely many* solutions. That freedom is the null space — the same statically-indeterminate 4th mode, now stated as linear algebra.
- **3-yoke geometry → B is 3×3.** If square and non-degenerate it is invertible: allocation collapses to $\mathbf{f}=B^{-1}\mathbf{u}$, one matrix multiply, no freedom, no drift *by construction*. This is exactly why the 1-rear+2-front layout "needs no allocation math" (Coupling §4). See §9.

---

## 3. The pseudo-inverse solution `f = B⁺u`

For a wide, full-row-rank B the **Moore–Penrose pseudo-inverse** is the *right* inverse:

$$B^+ = B^\top (B B^\top)^{-1}, \qquad B B^+ = I_{3\times 3}$$

So $\mathbf{f} = B^+\mathbf{u}$ satisfies $B\mathbf{f} = BB^+\mathbf{u} = \mathbf{u}$ **exactly** — the commanded wrench is delivered.

Among the infinitely many solutions, $B^+\mathbf{u}$ is the unique **minimum-2-norm** one:

$$\mathbf{f} = B^+\mathbf{u} = \arg\min_{\mathbf f}\ \tfrac12\|\mathbf f\|^2 \quad \text{s.t.}\quad B\mathbf f=\mathbf u$$

*Derivation (one line):* Lagrangian $\tfrac12\mathbf f^\top\mathbf f - \boldsymbol\lambda^\top(B\mathbf f-\mathbf u)$ → $\mathbf f = B^\top\boldsymbol\lambda$ → substitute → $\boldsymbol\lambda=(BB^\top)^{-1}\mathbf u$ → $\mathbf f = B^\top(BB^\top)^{-1}\mathbf u$. ∎

**Why min-norm is the right default:**
- It puts **zero energy in the null space**, so the drift of Coupling §27 cannot happen — the allocator has no reason to let diagonal corners fight.
- $\min\|\mathbf f\|^2$ ≈ least total force² ≈ least $I^2R$ ≈ least effort — a sensible secondary objective when you have no better one.

> **Elegant duality (ties the two halves of Coupling §2 together).** The force map is the transpose of the kinematic map: $B = J^\top$, where $J=\partial\mathbf g/\partial\mathbf q$ sends modal displacement to the four gaps. The gap→modal averaging matrix $T$ (Coupling §39) is $J^+$. Therefore the minimum-norm allocator is (up to weighting) **the transpose of the measurement transform**: $B^+ = T^\top$. Sanity check: pure heave $\mathbf u=[F_z,0,0]$ spreads to $F_z/4$ per corner — exactly $T^\top$ applied to heave. Measurement averaging and force spreading are the same geometry, mirrored.

---

## 4. The null space and `f_null`

$$\mathcal N(B) = \{\mathbf n : B\mathbf n = \mathbf 0\}, \qquad \dim\mathcal N = 4-3 = 1 \ \text{(4-corner)}$$

Solving $B\mathbf n=\mathbf 0$ for the symmetric corner layout gives the single basis vector

$$\mathbf n = [\,1,\ -1,\ -1,\ 1\,]^\top \quad\Rightarrow\quad \mathbf f = B^+\mathbf u + \alpha\,\mathbf n$$

This is the **diagonal / twist mode**: FL & RR push while FR & RL pull (or vice-versa). It produces zero heave, zero roll, zero pitch — invisible to the rigid body. `f_null = α·n` is the one free scalar you own.

**Uses of the free parameter α:**
1. **Default α = 0** (pure $B^+$) → min effort, no drift. Correct baseline.
2. **Bias-point / current centering.** Choose α to keep every corner nearest its zero-power hover current (minimize $\|\mathbf f - \mathbf f_{bias}\|$), so no corner is needlessly hot or near saturation. Equalizes headroom.
3. **Saturation recovery (the real workhorse).** If $B^+\mathbf u$ drives one corner past its force limit, spend α to pull it back into the feasible box *while preserving* **u** exactly (because n changes nothing the body sees). With one null DOF you can rescue exactly one saturated corner this way.
4. **Zero-power seeking.** Slew α to minimize net coil power, letting the PM carry as much static load as possible.

---

## 5. Weighted allocation

Corners are rarely identical (different $k_i$, thermal state, or you care about *power* not *force*). Minimize a weighted norm $\tfrac12\mathbf f^\top W\mathbf f$ instead:

$$\mathbf f = W^{-1}B^\top\!\left(B W^{-1} B^\top\right)^{-1}\mathbf u \equiv B^+_W\,\mathbf u$$

- $W=I$ → ordinary pseudo-inverse.
- $W=\mathrm{diag}(1/k_{i,j}^2)$ → minimizes total **current** (weakest/hottest corner does less).
- $W=\mathrm{diag}(R_j)$ → minimizes total **ohmic power**.
- $W$ can be scheduled on measured coil temperature to shed load off a hot corner in real time.

---

## 6. Constraints — why the raw pseudo-inverse isn't enough

Actuators saturate. Each corner force is boxed:

$$f_{\min,j} \le f_j \le f_{\max,j}$$

With PM bias the coil modulates force around the bias point $F_0$, and the coil current is limited to $\pm I_{\max}$, so $f_j \in [F_0-\Delta,\ F_0+\Delta]$ — a genuine box, and force is **not** simply "≥0."

The unconstrained $B^+\mathbf u$ ignores this. If you just **clip** the result, $B\mathbf f \ne \mathbf u$ — the delivered wrench is wrong, coupling reappears, and on an unstable plant that can destabilize. Options, in order of sophistication:

- **Redistributed (cascaded) pseudo-inverse** — clip the saturated corner to its limit, subtract its contribution from **u**, re-solve for the remaining corners using the leftover freedom. For 4→3 (one spare DOF) this is one cheap extra step and is real-time trivial. This is §4-use-3 done algorithmically.
- **Constrained QP allocation** — solve
  $$\min_{\mathbf f}\ \|W(\mathbf f-\mathbf f_{des})\|^2 \quad\text{s.t.}\quad B\mathbf f=\mathbf u,\ \ f_{\min}\le\mathbf f\le f_{\max}$$
  by active-set (Härkegård's `qcat`) or interior-point. $\mathbf f_{des}$ = the preferred (bias-centered) point.
- **Prioritized / two-stage** — when **u** itself is infeasible (demand exceeds total actuator capacity), don't fail: first minimize $\|B\mathbf f-\mathbf u\|$ with priority weighting (keep **heave** over tilt — you'd rather stay levitated and slightly tilted than drop), then optimize effort within whatever slack remains.

---

## 7. Why the layering is valid (and where it breaks)

- In the feasible region $B B^+ = I$, so from the stabilizer's viewpoint the 4-magnet plant looks like **3 decoupled channels** $z,\theta,\phi$. That is the decoupling that lets you design a 3-state LQR (or three lead-lag loops) instead of a tangled 4×4 problem.
- **It breaks on saturation.** When the allocator can't meet **u**, the modal channels re-couple and integral terms in the stabilizer wind up. Mitigations: (a) prioritized allocation (§6) so the important DOF degrades last; (b) **anti-windup** driven by the *achieved* wrench $B\mathbf f_{achieved}$ fed back to the integrators, not the commanded **u**. Design these together — a stabilizer tuned assuming perfect allocation will misbehave at the limits.

---

## 8. The modal model the stabilizer actually sees

Working in $\mathbf q=(z,\theta,\phi)$, the rigid-body dynamics are

$$M\ddot{\mathbf q} = K_s\,\mathbf q + \mathbf u, \qquad M=\mathrm{diag}(m, I_{xx}, I_{yy})$$

where $K_s$ is the modal negative-stiffness (from the per-corner $k_s$ of [[Maglev - PM Bias and Force Linearization]], mapped through the same geometry). Two facts that decide how hard MIMO is:

- **If** the CG sits at the geometric centroid **and** the pod's principal axes align with roll/pitch, then $M$ is diagonal and $K_s$ is diagonal → the three modes are genuinely independent → you may design **three SISO RHP-pole loops**. Each is the $k_i/(ms^2-k_s)$ plant of PM-Bias §5, per mode.
- **Off-centroid CG or product-of-inertia terms** put off-diagonal entries in $M$ (and $K_s$) → the modes couple → you need a true **MIMO LQR/H∞** that captures the cross terms. This is the analytic reason the Coupling §104 CG-alignment note matters: alignment buys you decoupled SISO design; misalignment forces full MIMO. Counterweighting the CG onto the centroid is therefore a *controls* simplification, not just mechanical tidiness.

---

## 9. The 3-yoke case (recommended geometry) in this language

For 1-rear + 2-front (positions FL, FR at $(\pm\ell_x, +a)$, rear at $(0,-b)$):

$$B = \begin{bmatrix} 1 & 1 & 1 \\ \ell_x & -\ell_x & 0 \\ a & a & -b \end{bmatrix}\ (3\times 3),\qquad \mathbf f = B^{-1}\mathbf u$$

- Non-degenerate (yokes not collinear) → **B invertible** → allocation is exact and unique. **No null space, no drift, nothing to tune.**
- Roll ← front differential only (rear row has 0); pitch ← front-vs-rear with the long arm $b$; heave ← sum. Clean, as Coupling §85 argues.
- **The cost is the flip side of §4/§6:** with zero redundancy there is *no* freedom to redistribute, so a saturated or failed yoke immediately loses a DOF — you cannot trade it away. Acceptable given the "fault tolerance is don't-care" call, but know that saturation headroom management (§4-use-2,3) is a capability you're giving up.

---

## 10. Force → current inversion (the step after allocation)

The allocator outputs **forces**; the current loop wants **currents**. Invert the per-corner actuator model from PM-Bias §4b. Given desired $f_j$ and measured gap $x_j$:

$$f_j = \frac{\Phi_j^2}{\mu_0 A},\quad \Phi_j=\frac{N i_j + \mathcal F_{pm}}{\mathcal R(x_j)} \quad\Rightarrow\quad i_j = \frac{\mathcal R(x_j)\sqrt{\mu_0 A\, f_j} - \mathcal F_{pm}}{N}$$

- This exact static inversion **cancels the actuator nonlinearity** (the $(i/x)^2$ law), so the loop above it sees a clean linear force command — cheaper and more robust than full input-output feedback linearization of the whole plant.
- Locally it reduces to $\delta i_j = \delta f_j / k_i$ (the small-signal current stiffness), which is what the linear stabilizer assumes.
- Requires a decent gap measurement and PM/reluctance model; pair with flux feedback ([[Maglev - Sensing and Flux Feedback]]) to keep $\mathcal F_{pm}$ honest under thermal drift.

---

## 11. Implementation recipe

1. Measure 4 (or 3) gaps → **modal transform** $T$ → $(z,\theta,\phi)$.
2. Observer/EKF → clean state + rates (velocity is not directly measured).
3. **Stabilizer** (LQR/ADRC) on the modal state → $\mathbf u=[F_z,M_\phi,M_\theta]$.
4. **Allocate**: $\mathbf f = B^+\mathbf u$ (or $B^{-1}$ for 3-yoke); redistribute/QP if any corner saturates; pick α to stay bias-centered.
5. **Force→current inversion** per corner (§10).
6. Inner **current loop** per coil → PWM.
7. **Anti-windup** on the stabilizer's integrators using $B\mathbf f_{achieved}$.

Steps 1–4 are pure linear algebra at the outer-loop rate (~1 kHz); only step 6 needs the fast (kHz–tens of kHz) loop.

---

*See also:*
- *[[Maglev - Coupling and Geometry]] — why the 4→3 null space exists (the problem this doc solves)*
- *[[Maglev - Control Theory Fundamentals]] — the RHP-pole loop shaping / LQR that generates **u***
- *[[Maglev - PM Bias and Force Linearization]] §4b, §5 — the per-corner force model inverted in §10*

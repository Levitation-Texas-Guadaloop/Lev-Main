# Maglev - Coupling and Geometry

*Support doc for [[Levitation Research Claude]] — answers Section A questions on the statically indeterminate 4→3 coupling problem and the central-rear + 2-front-corner yoke proposal.*

---

## 1. What Is the Coupling, Exactly?

Yes — the four electromagnets are mechanically and electrically separate. Each has its own coil, its own H-bridge driver, and its own power supply rail. There is no direct electrical coupling between them.

The coupling arises from **rigid-body mechanics**, not from the electromagnets themselves.

Here is the key insight: the pod is a *single rigid body*. Its motion is completely described by **6 degrees of freedom** (DOF): three translations (x, y, z) and three rotations (roll, pitch, yaw). With the rail constraining lateral and yaw motion, only **3 DOF remain free**: heave (z), pitch (θ), roll (φ).

Now, each corner magnet produces one force — a scalar. Four corners = 4 scalar forces. But those 4 forces must satisfy the **rigid-body equilibrium equations**, which are only 3 equations (sum of forces in z, sum of moments about x-axis, sum of moments about y-axis):

$$F_1 + F_2 + F_3 + F_4 = m\ddot{z}$$
$$\ell_x (F_1 - F_2 + F_3 - F_4) = I_{xx}\ddot{\phi}$$  
$$\ell_y (F_1 + F_2 - F_3 - F_4) = I_{yy}\ddot{\theta}$$

(where ℓ_x, ℓ_y are the half-widths between corner pairs)

**Three equations, four unknowns (F₁, F₂, F₃, F₄).** The system is underdetermined — there is a one-dimensional null space: any combination of the form (a, −a, a, −a) or similar satisfies all three equations with zero net effect on z/pitch/roll. The fourth "mode" of the magnet forces is invisible to the rigid body. This is called **statically indeterminate**.

### The Drift Problem

Because the null-space force combination does nothing to z/pitch/roll, a naive per-corner controller has no reason to prevent it. The integral terms in four independent PID controllers will slowly drift to find different solutions within this null space. In practice, one corner pulls harder, another slackens — the currents diverge over time even if the pod appears to be hovering stably. This is the "slow current drift" you'd observe in practice.

It also means the four corners are **effectively competing** when their integral terms diverge: corner 1 might be over-driven and corner 3 under-driven, yet the rigid-body motion appears the same. The four controllers "fight" in the null space.

---

## 2. Why Centralized MIMO + Control Allocation Fixes This

The solution is to **decouple the rigid-body problem from the force-distribution problem**:

**Step 1 — Work in modal coordinates.** Transform the four gap measurements into three rigid-body coordinates:

$$z = \frac{g_1 + g_2 + g_3 + g_4}{4}, \quad \phi = \frac{g_1 - g_2 + g_3 - g_4}{2\ell_x}, \quad \theta = \frac{g_1 + g_2 - g_3 - g_4}{2\ell_y}$$

The MIMO stabilizer (LQR/ADRC/MPC) operates only on (z, φ, θ) and produces three desired generalized forces/torques (F_z, M_φ, M_θ).

**Step 2 — Control allocation.** Map three generalized demands to four coil force commands:

$$\mathbf{f} = B^+ \mathbf{u} + \mathbf{f}_{null}$$

where B is the 3×4 geometry matrix, B⁺ is its pseudo-inverse (minimum-norm solution), and f_null is any combination from the null space. The minimum-norm pseudo-inverse sets f_null = 0 by default, preventing drift. You can also use f_null for secondary objectives (e.g., keeping all currents equal, or seeking zero-power).

> **Full treatment → [[Maglev - Control Allocation and MIMO]].** That doc derives B⁺, computes the null-space vector (the diagonal twist mode [1,−1,−1,1]), covers weighted/constrained (QP) allocation and saturation recovery, the force→current inversion, and when the modal plant decouples into SISO vs. needs full MIMO.

**Result:** The MIMO controller never sees the coupling. The allocator enforces consistency. No drift.

---

## 3. Alternative: The Augmented Integral Compensator (Zhang et al., 2023)

Zhang et al. add an extra integral loop that measures the *differential* current between paired corners and drives it to zero. This forces the null-space mode to be zero without needing a full pseudo-inverse — a clever but more ad-hoc fix. It's a practical retrofit for a system that already uses 3 control loops, adding one more parameter.

For a new design starting from scratch, explicit control allocation (the B⁺ approach) is cleaner and more principled.

---

## 4. The Central-Rear + 2-Front-Corner Proposal

Your proposed geometry: **one yoke at the center-rear** and **two yokes at the front corners**.

```
     [Front-Left]     [Front-Right]
           \               /
            \             /
             [Center-Rear]
```

### Counting DOF

Three actuators, three forces → **3 equations, 3 unknowns**. The system is now **statically determinate** — the null space is eliminated. This is a real advantage.

| Property | 4-corner | 1-rear + 2-front |
|---|---|---|
| Forces available | 4 | 3 |
| Controlled DOF (z, pitch, roll) | 3 | 3 |
| Statically indeterminate? | Yes | No |
| Null space / drift problem | Yes | Eliminated |
| Redundancy / fault tolerance | Can lose 1 coil | Lose 1 coil → lose DOF |
| Control allocation needed | Yes (B⁺) | No (B is square, invertible) |
==**Redundancy/fault tolerance is a don't care for now.**==
### Effect on Pitch Control

The center-rear placement gives a long moment arm for pitch. With the two front yokes at the same fore-aft position and the rear yoke centered:

- **Pitch** is controlled primarily by the rear yoke vs. the combined front pair. Long lever arm → efficient pitch actuation.
- **Roll** is controlled by the differential between the two front yokes. The rear yoke is symmetric and contributes zero net roll moment.
- **Heave** is the sum of all three.

This geometry is actually favorable for pitch authority, and the symmetric front pair cleanly decouples roll from pitch.

### The Lateral Asymmetry Concern

You raised: "naive controller may exaggerate lateral asymmetries." With 4 symmetric corners, manufacturing tolerances (one magnet slightly stronger, one gap sensor miscalibrated) inject roll/pitch errors that the controller must correct. With 2 front + 1 rear:

- **Front roll** is directly observable (differential front gap) and directly controlled (differential front current).
- **Rear lateral bias** would show up as a yaw disturbance — but yaw is rail-constrained, so it manifests as a lateral force on the rail rather than pod rotation. This is probably acceptable for a rail-guided system.

### Practical Concerns

1. **Center-of-mass alignment.** The pod's CG should be near the centroid of the three yoke positions for balanced hover. If the payload is forward-heavy, the rear yoke carries more load; if side-heavy, the front pair is asymmetric. This is solvable (the controller handles static offsets) but worth knowing.
	1. **==We can probably deal with this with something as simple as counterweights. Pod chassis/layout is flexible; also, we are not trying to meet any ulterior payload objectives==**

2. **Loss of redundancy.** With 3 actuators for 3 DOF, any actuator failure is unrecoverable — you immediately lose one DOF. The 4-corner design can lose one corner and still control heave + one tilt (losing the other tilt). If fault tolerance matters, this is the main cost of the 3-actuator design.
	1. ==**Don't care**==

3. **Mechanical layout.** The triangular footprint may be easier to manufacture consistently than a rectangular 4-corner layout (fewer parts to align). Depends on your pod chassis.

### Recommendation

The 1-rear + 2-front geometry is worth serious consideration for a prototype because:
- It eliminates the statically-indeterminate problem without any allocation math.
- The geometry is intuitively clean (pitch = rear vs. front, roll = front differential).
- It reduces the controller from a 4-output to a 3-output MIMO problem.

The main trade is fault tolerance. For a research/prototype pod that doesn't need to survive actuator failures, this is probably a **net win**.

---

## 5. Magnetic Flux Cross-Coupling (A Separate Issue)

There is also *magnetic* coupling between adjacent yokes if they share a common steel return path or if their fringe fields overlap. This is distinct from the rigid-body coupling above.

- If each yoke has its own magnetically isolated steel circuit → no flux coupling; the actuators are truly independent in the magnetic sense.
- If yokes share a common rail or chassis steel → flux from one yoke threads through the adjacent yoke's circuit, changing its effective bias. This is another reason to measure flux (Hall sensor) rather than relying solely on current.

For the 3-actuator geometry, placing the yokes far enough apart and using magnetically isolated circuits eliminates this.
	**==In our design case, yokes are ~3 feet apart at least. Magnetic coupling should be negligible as most of the chassis is aluminum/plastic anyway. There is a possibility of magnetic 'conduction' across the steel track to the other yoke -- hoping that distance and 'path-of-least-resistance' would desaturate propgatation along the track path==**

---

*See also:*
- *[[Maglev - PM Bias and Force Linearization]] — derives the force law each actuator obeys*
- *[[Maglev - Control Theory Fundamentals]] — discusses the MIMO control loop that operates on the modal coordinates*

# MIMO Stabilization of a Four-Corner PM-Biased Hybrid Maglev Pod: A Control-Methods Research Report

## TL;DR
- **Stabilize first with proven tools, then add learning on top.** The fastest reliable path for this open-loop-unstable, stiff, 4-actuator→3-DOF (z/pitch/roll) pod is a layered architecture: a fast inner current loop (kHz) → a MIMO state-feedback or ADRC/sliding-mode stabilizer running on the diagonalized z/pitch/roll modes → an optimization-based control allocator distributing 3 generalized forces onto 4 coils. Learning-based control (RL, Koopman-MPC, GP-MPC) should be layered *outside* a controller that already stabilizes, never used to bootstrap stability on bare hardware.
- **Add sensors now: per-coil current sensing is the single highest-value upgrade**, plus flux feedback (Hall) and IMU fusion. The (i/x)² nonlinearity and the unstable "negative-stiffness" pole make the current/flux state worth measuring directly; the literature repeatedly shows flux/current feedback enlarges the stable parameter region and improves disturbance rejection over gap-only feedback.
- **The 4-magnet-on-one-rigid-body geometry is "statically indeterminate"** (4 forces, 3 controlled DOF), which causes inter-magnet current coupling/drift. This must be resolved explicitly by control allocation (pseudo-inverse / weighted least squares) or an augmented-integral coupling compensator, independent of which stabilizer you choose.

## Key Findings
1. **Attraction-mode maglev is fundamentally a "mass on a negative spring."** Linearizing the force F=k(i/x)² about a bias point gives F ≈ k_i·i − k_s·x, with current stiffness k_i = μ₀AN²I_b/s₀² and position ("negative") stiffness k_s = μ₀AN²I_b²/s₀³. The equation of motion m·ẍ = k_s·x + k_i·i has open-loop poles at s = ±√(k_s/m) — one in the right-half plane. This is the source of the instability and is identical to the active-magnetic-bearing (AMB) problem, which is why AMB literature transfers directly.
2. **Classical control is genuinely sufficient for stabilization** of single/multi-point maglev and is the proven baseline: cascaded inner-current + outer-gap loops, state feedback with pole placement, and LQR/LQG are deployed on real maglev vehicles and commercial AMBs. It should not be dismissed even though the user prefers modern methods.
3. **Among nonlinear methods, sliding-mode (especially super-twisting/higher-order) and ADRC/ESO are the most battle-tested for maglev**, precisely because they are robust to the (i/x)² nonlinearity and to load/parameter changes without an exact model. Backstepping and feedback linearization are common in the literature but feedback linearization is fragile to model error.
4. **MPC is real-time feasible on embedded hardware** for maglev (including explicit/PWA MPC running sub-millisecond and embedded NMPC validated processor-in-the-loop), and it natively handles current/voltage/gap constraints and the MIMO allocation — making it attractive for this constrained, coupled plant.
5. **Learning-based control for maglev is real but immature for primary stabilization.** Demonstrated approaches include RL-tuned super-twisting SMC, RL optimal tracking for maglev levitation with input delay, data-driven (DMDc/Koopman, RL policy iteration) derivative-feedback control on real maglev, deep-RL maglev manipulation, and physics-informed NN for plant identification. Safe-RL via control-barrier-functions and GP-MPC give the safety scaffolding needed to learn on an unstable plant.

## Details

### A. System modeling for control
**Per-actuator electromechanics.** Each corner is a U-shaped steel yoke with N52 PMs providing static bias flux plus a control coil. The attractive force follows the canonical magnetic-reluctance relation F = k(i/x)² (force rises with current squared, falls with gap squared); the PM bias linearizes the force-vs-current relationship around the operating point — exactly the rationale the AMB community (e.g., Calnetix) gives for PM-biased bearings, where the bias's "primary purpose is to linearize the applied force vs. coil current relationship of the actuator." Linearizing about (I_b, s₀):

- Current stiffness (force-current gain), positive: k_i = ∂F/∂i = μ₀AN²I_b/s₀²
- Position stiffness ("negative stiffness"), destabilizing: k_s = ∂F/∂x = μ₀AN²I_b²/s₀³
- Useful identity: k_s/k_i = I_b/s₀.

> **Series-reluctance correction (see [[Maglev - PM Bias and Force Linearization]] §4b).** The forms above assume the air gap is the *only* reluctance. The PM (recoil μ_rec ≈ 1.05, so magnetically ~an air gap of its own length) adds a large series reluctance. Both stiffnesses are then scaled by the gap-reluctance fraction η = ℛ_gap/ℛ_total: k_i → η·k_i, k_s → η·k_s. For the actual yoke (1" PM per leg) η ≈ 0.11 — the gap is only ~11% of the loop reluctance, so both stiffnesses (and the unstable pole, ∝√η) are much smaller than the η=1 forms suggest.
> 	==**How to prove/derive that PM-biasing can effectively linearize the F ~ f(i) relationship? What are the stiffness relationships? Where do they come from?**== → [[Maglev - PM Bias and Force Linearization]]

These exact definitions and the linearized form f = k_s·x + k_i·i are the standard formulation in **Schweitzer & Maslen, *Magnetic Bearings: Theory, Design, and Application to Rotating Machinery* (Springer, 2009)**, and are reproduced in peer-reviewed AMB modeling work (e.g., ***Mathematical and Computer Modelling of Dynamical Systems*,** which calls k_x "the open-loop gain of the actuator [which] is negative" and k_i "the current gain [which] is positive").

**Why open-loop unstable.** With m·ẍ = k_s·x + k_i·i, the characteristic equation m·s²−k_s=0 yields poles s = ±√(k_s/m): a right-half-plane pole. Physically, displacing the pod toward the rail increases attractive force, pulling it further in — positive feedback. Calnetix Technologies' "Magnetic Bearing Terminology" states it directly: "Because of the negative stiffness, AMBs are unstable without closed-loop control." (An equivalent operating-point form for a ball-on-gap reduces the poles to ±√(2g/x₀) in the ideal single-reluctance limit; with the PM's series reluctance folded in it is ±√(2gη/x₀), i.e., the unstable pole depends on gravity, operating gap, *and* the gap-reluctance fraction η — for this yoke ~4.3 Hz, not the ~13 Hz the η=1 form gives.) The unstable pole frequency √(k_s/m) sets the minimum closed-loop bandwidth; the electrical pole R/L (coil) and amplifier dynamics set the achievable inner-loop speed. The wide separation between fast electrical and slower mechanical timescales makes the plant stiff and the design a singular-perturbation/cascaded problem.

**Coil electrical dynamics.** V = Ri + d(Li)/dt with motional back-EMF from dL/dx·ẋ. Coil inductance L limits current-loop bandwidth (current lags voltage by L/R), and the EMS maglev literature explicitly notes the inductance-induced current delay is a core design constraint. Turn count N (still a free parameter for the user) trades force-per-amp (k_i ∝ N²) against inductance (L ∝ N²) and thus current-loop bandwidth — a key early design decision.

**MIMO plant and the 4→3 mapping.** Stacking the four corner gaps and currents and projecting onto rigid-body coordinates gives a coupled z/pitch/roll plant. Crucially, a rigid body has only 3 controllable DOF in this plane (heave + two tilts), but there are 4 independent magnet forces. This is the **"statically indeterminate" problem**: the 4th force is not uniquely determined by the 3 equilibrium equations, so the inter-magnet currents are coupled and can drift/diverge. Zhang et al., "Coupled Robust Constant-Power-Control Algorithm for Rigid Quadruple EMS Vehicle" (*IEEE Access*, 2023) describe exactly this — applications of "the small-size rigid quadruple counterpart are still restricted by the **==coupling problem or the so-called statically indeterminate problem among the four electromagnets==**" — and resolve it with "the robust constant-power-control algorithm with the **==augmented integral controller to compensate the current coupling among the four electromagnets==**," using "only three feedback control loops and four parameters." Cho et al., "Robust Zero Power Levitation Control of Quadruple Hybrid EMS System" (*Journal of Electrical Engineering and Technology*, 2013) document the same coupling: manufacturing/PM-equilibrium tolerance means conventional control "only satisfies the zero power levitation in one or two hybrid EMS system among the four," fixed by a per-axis gap-reference compensator. The takeaway: this must be resolved by allocation or a coupling compensator (see G).
	- ==**What is the coupling here? Are they not separate actuators (with presumably separate power sources?**
	- Can we consider a CENTRAL rear yoke (1x) and CORNER front yokes (2x)
		- *That would help control pitch and potentially reduce roll that is induced from lateral asymmetries -- which naive controller may exaggerate*== → [[Maglev - Coupling and Geometry]]

==**High-Level Modeling Question**: There are several approaches to simulating yoke dynamics. 
- Equivalent circuit model -> lumped reluctance estimate at actuator (+ Matlab, simple numerical sim)
- Finite element model -> discretize yoke and solve forcings on a parametric sweep (+ Ansys)
- Various others? What is the suggested way to go? ==

> **Answer — use both, in a hierarchy. They answer different questions, so it isn't either/or.**
>
> **Working model for control: the lumped magnetic-equivalent-circuit (MEC / reluctance network).** This is exactly what [[Maglev - PM Bias and Force Linearization]] §4b and the [[Maglev - Python Simulation Sandbox]] already are. It yields closed-form, differentiable F(i,x), k_i, k_s, L(x) → a low-order state-space you can run in real time and design controllers against. **A controller needs a low-order differentiable model; FEM is not one.** This is your primary tool.
> - Cheap to extend: nonlinear μ_r(B) per steel branch, PM as a Thévenin source (done), leakage/fringing permeances as extra network elements.
> - Blind spots: the 1-D flux assumption misses gap fringing, inter-leg leakage, the saturation *distribution*, and cross-yoke coupling.
>
> **Calibrator / validator: 2-D (then 3-D if needed) magnetostatic FEM, run once as a parametric sweep.** Not a runtime model — use it offline to pin the numbers the MEC cannot derive from first principles:
> - **Effective pole area** — fringing makes it larger than geometric A (more force, lower gap reluctance).
> - **Leakage fraction** across the window. *Worth checking here specifically:* with ℛ_pm dominating (η ≈ 0.11), flux may prefer a leakage path over the working gap — a parallel leakage permeance would further erode usable flux and shift k_i.
> - **Saturation knee** at the pole faces (B_b ≈ 1.15 T is close) → validates the μ_r assumed for ℛ_steel.
> - **F(i,x) and L(i,x) maps** → fit correction factors (or a lookup table) back into the MEC.
> - **Cross-yoke coupling** for the 4→3 MIMO problem: one multi-yoke solve tells you whether to add mutual-reluctance terms or treat neighbor flux as a bounded disturbance.
>
> **Tooling.** Stay in the Python stack: **FEMM + pyFEMM** (2-D, free, scriptable — sufficient for the extrusion cross-section and all the sweeps above). Step up to **Ansys Maxwell / COMSOL** only for genuine 3-D end effects, moving-mesh transient eddy-current loss, or coupled thermal. `magpylib` is useful for quick PM-field checks but is analytic (no saturation), so it does not replace FEM.
>
> **Others — skip for now:** conformal-mapping / Schwarz–Christoffel fringing models (FEM is easier and more general), and full transient eddy-current FEM (only if inner-loop lag from solid-steel eddies becomes a *measured* problem — laminating the yoke sidesteps it).
>
> **Suggested path:** analytic MEC now (controller bring-up) → one FEM sweep to calibrate effective A, leakage, saturation, and the F/L maps → FEM-corrected MEC or lookup-table sim → bench system-ID to reconcile both against the real hardware. Each stage feeds the next; FEM is never the thing you close the loop around.

### B. Classical / linear control (the proven baseline — defended)
**Cascaded architecture.** The standard, proven maglev structure is an inner current loop (fast, makes force≈k_i·i by holding current) wrapped by an outer gap/position loop. The EMS overview literature (*Energies* 2023, "Control Methods for Levitation System of EMS-Type Maglev Vehicles") confirms "the most typical linear control method is the state feedback method ... decomposition of the system into current and position loops through cascade design." A fast inner current loop also simplifies adaptive outer-loop design and is explicitly used to make load-adaptive maglev tractable.

**Lead-lag / loop shaping.** Because the plant has a RHP pole, phase lead is mandatory near crossover. Quantitative-feedback-theory / Nichols-plane loop shaping has been used to stabilize a real magnetic levitation system and improve gain/phase margins and sensitivity over a baseline controller.
	**==Discuss relevant theory. I am familiar with pole <-> stability and what gain/phase margins are. Not fluent in loop shaping -- how is it important here?==** → [[Maglev - Control Theory Fundamentals]]

**Decentralized vs centralized.** Per-corner SISO control is simple and is how many maglev modules are built (decoupling the bogie into single-electromagnet units). But for a single rigid pod with strong z/pitch/roll cross-coupling, centralized MIMO state feedback on the modal coordinates is better; AMB practice uses decentralized + decoupling control for identification then centralized MIMO for performance.
	**==Prefer MIMO, centralized. We have tried SISO with very limited success. There were other issues (like manufacturing consistency, etc), but I am interested in improving technical foundation in MIMO.==**

**LQR/LQG, pole placement.** State feedback with pole placement (the Manabe canonical-form / coefficient-diagram method has been applied specifically to the 4-pole hybrid electromagnet) and LQR/LQG with a Kalman filter are standard. For the 4-pole hybrid mover, centralized state-feedback-integral (SFI) controllers designed by pole assignment achieve stable multi-DOF levitation.

**Verdict:** Classical cascaded PID/state-feedback with a fast current loop is the correct first controller to bring the pod up. It is proven, debuggable, and the foundation everything else builds on.

### C. Nonlinear control
**Feedback / input-output linearization.** Cancels the (i/x)² nonlinearity analytically (exact linearization of PM-biased hybrid bearings has been demonstrated with a nonlinear Luenberger observer for a 5-DOF flywheel). Powerful but fragile: it depends on accurate k_i, k_s, gap and flux models, and degrades under saturation and parameter drift.

**Sliding-mode control (SMC).** The workhorse robust method for maglev. Variable-structure control is invariant to matched disturbances/parameter perturbations and handles the nonlinearity without an exact model. Higher-order/super-twisting SMC reduces chattering; terminal/integral-backstepping SMC and disturbance-observer-based SMC (where the switching gain need only exceed the disturbance *estimation error*, sharply reducing chattering) are all demonstrated on maglev. Chattering and sensor-noise amplification are the practical costs.

**Backstepping / adaptive backstepping.** Very common in maglev; recursively builds a Lyapunov-stable control law and naturally incorporates the cascaded electrical/mechanical structure. Adaptive and observer-based backstepping handle unknown load mass, track flexibility, and time delay with proven asymptotic/uniformly-ultimately-bounded stability (e.g., robust observer-based adaptive backstepping with magnetic-flux feedback achieving stable suspension under very low track stiffness).
	**==Tell me more about Lyapunov stability and what this means numerically==** → [[Maglev - Control Theory Fundamentals]]
	**==What is backstepping numerically?==** → [[Maglev - Control Theory Fundamentals]]

**Disturbance observers / ESO / ADRC.** Increasingly popular and well-suited here. ADRC lumps nonlinearity + disturbances into an extended state estimated by an ESO and cancels it, needing little model fidelity. Its linear variant (LADRC) reduces tuning to two parameters — the controller bandwidth ω_c and observer bandwidth ω_0 — via Gao's "bandwidth parameterization" (Gao, Z., 2003, "Scaling and Bandwidth-Parameterization Based Controller Tuning," *Proc. American Control Conf.*). Hybrid ADRC-SMC and cascaded-ESO+SMC schemes are demonstrated on EMS maglev with strong vibration/disturbance rejection. ADRC is arguably the best "modern, low-model" stabilizer to pair with the inner current loop.

### D. Optimal & predictive control
MPC handles the MIMO coupling, the 4→3 allocation, and hard constraints (coil current/voltage, slew, gap limits) in one optimization. For maglev specifically: explicit/piecewise-affine MPC and MPC-based reference governors run sub-millisecond on simple microcontrollers (encoded as a binary search tree over a PWA function); embedded NMPC for EMS maglev vehicles has been validated processor-in-the-loop — Kargl et al., "Embedded Model Predictive Control for EMS-type Maglev Vehicles" (arXiv:2603.09671) report that "model predictive control is capable to robustly stabilize the highly nonlinear and constrained system even at very high speed ... processor-in-the-loop studies are carried out to validate the designed control algorithms on a microcontroller." Two-level state-feedback MPC (Zhang, Zhou & Tao, 2020, "Model predictive control of a magnetic levitation system using two-level state feedback," *Measurement & Control*) uses measured air gap, electromagnet acceleration, and control current — a first-level nonlinear feedback linearizes the plant and a second-level linear feedback stabilizes it. Real-time feasibility is the main concern; explicit MPC (offline optimization, online lookup) and short horizons mitigate it.

### E. Adaptive & robust control
Load changes (pod payload) and parameter drift (resistance with temperature) motivate adaptation. Demonstrated on maglev: model-reference adaptive control (MRAC) and enhanced MRAC for tracking; real-time adaptive control across a *large* load-mass range using a fast inner current loop; adaptive control with fuzzy inversion (UUB-proven, DSP-implemented). L1 adaptive control (decoupling estimation speed from robustness) is widely used for fast uncertain plants and is a strong candidate for the outer loop, though direct maglev-specific L1 reports are thinner than SMC/ADRC.

### F. Learning-based control (substantial weight)
**Reinforcement learning.** RL is being applied to maglev but mostly as an *augmentation* of a model-based controller, not as the primary stabilizer:
- RL (DDPG) online self-tuning of a super-twisting SMC — "Reinforcement Learning-Based Super-Twisting Sliding Mode Control for Maglev Guidance System" (*Actuators*, 2026, 15(3):147) uses a "multi-objective hybrid reward function ... realizing the online self-tuning of core STSMC" parameters, so RL tunes while SMC guarantees structure.
- RL-based optimal tracking for the maglev levitation system with input time delay, handling external disturbance, input delay, and time-varying mass.
- Data-driven *model-free* policy-iteration derivative-feedback control on a real active maglev ("Optimal Derivative Feedback Control for an Active Magnetic Levitation System," 2026), compared against DMDc+PEM-identified optimal control — the model-free approach "consistently outperforms the indirect solution when multiple epochs are allowed."
- Deep-RL for maglev non-contact manipulation (Maglev-Pentabot) discovering effective stabilizing/transport policies in simulation.
- Q-learning and TD+GA fuzzy reinforcement learning have suspended real active magnetic bearing rotors.

**Neural-network control.** Neural feedback linearization, RBF-NN adaptive SMC (minimum-parameter-learning to approximate unknown model terms, Lyapunov-proven), and deep-CNN-SMC on 5-DOF magnetic bearings. Feedback-error-learning NN+PID is a classic stable hybrid.

**Data-driven models for control.** Koopman/EDMD-with-control lifts the nonlinear maglev into a linear model usable with linear MPC; DMDc and SINDy-with-control identify control-oriented models from data; LSTM-ARX pseudo-linear models feed predictive functional control on a real maglev ball. These give the "modern" nonlinear-MPC path without hand-deriving the model.

**Learning-augmented / GP-MPC.** Gaussian-process MPC learns residual dynamics with calibrated uncertainty and enforces chance constraints — a principled way to add learning to the MPC stabilizer with stochastic safety guarantees (recursive feasibility and closed-loop convergence shown for the static-uncertainty case).

**Iterative learning control (ILC).** For repetitive disturbances (e.g., periodic rail irregularity or unbalance-like effects), ILC and disturbance-observer-augmented ILC improve tracking on magnetic bearings cycle-over-cycle.

**Safety / sim-to-real / sample efficiency (the crux on an unstable plant).** You cannot let an untrained RL policy explore on a plant that destructively crashes within milliseconds of instability. The literature's answer:
- **Control-barrier-function safety layers** (RL-CBF, Cheng et al., AAAI 2019) guarantee safety *during* learning by projecting RL actions onto a safe set, using GP models of dynamics; safe-RL surveys formalize Lyapunov/barrier certificates.
- **Sim-to-real** with domain randomization + few-shot fine-tuning is the standard transfer recipe; the sim-to-real gap (sensor noise, delays, unmodeled dynamics) is the dominant risk.
- **Residual RL**: keep the classical/ADRC controller as the base policy and let RL learn only a corrective residual, bounding worst-case behavior.

### G. Control allocation / over-actuation
The 4→3 map B (3 generalized forces/torques = B · 4 coil forces) is fat, so infinitely many coil-force combinations realize a desired (heave, pitch, roll). Standard solutions, all transferable from aerospace/marine over-actuation:
- **Moore-Penrose / weighted pseudo-inverse**: minimum-norm (or minimum-energy) allocation, closed-form, cheap — the natural default.
- **Redistributed / enhanced-redistributed pseudo-inverse and weighted least squares**: respect coil current/force saturation by re-solving when limits are hit.
- **Optimization-based allocation** (QP): explicitly minimizes effort or balances flux headroom, and folds into MPC.
- **Exploit redundancy** for fault tolerance (lose one coil → re-allocate to remaining three for heave + limited tilt) and for keeping all coils away from flux saturation.
For the zero-power goal later, the redundant 4th DOF is also where bias-flux equilibrium-seeking lives — but per the user, that is deferred. The immediate need is to resolve the statically-indeterminate current coupling: either allocate explicitly, or add an augmented-integral coupling compensator as in the quadruple-EMS constant-power-control work (Zhang et al., *IEEE Access* 2023).

### H. State estimation & sensing (electrical/software interface — priority)
**Observers.** Velocity (ż, pitch rate, roll rate) is rarely measured cleanly; differentiating a noisy inductive gap sensor injects noise. Use a Luenberger observer (linear regime) or EKF/UKF (full nonlinear model) to estimate velocities and unmeasured states; nonlinear Luenberger observers are demonstrated for PM-biased hybrid bearings, and extended/virtual ESOs estimate lumped disturbance plus velocity while filtering noise (e.g., the adaptive virtual ESO backstepping work reporting a 56–69% reduction in settling time/steady-state error vs. traditional backstepping).

**Sensor fusion.** Fuse the 4 inductive gap sensors with the IMU: complementary filtering (gap sensor for low-frequency absolute position, IMU accelerometer/gyro for high-frequency motion) or a Kalman fusion gives a low-noise, low-latency state estimate and rejects the cheap sensors' noise. The pod's rigid-body IMU directly observes z-accel, pitch and roll rates — highly complementary to per-corner gaps.

**Why current and flux sensing materially help.** Maglev/AMB practice strongly supports measuring the magnetic state, not just the gap:
- **Per-coil current sensing** closes the fast inner loop (force≈k_i·i), linearizes the actuator, improves disturbance rejection, and is cheap. Many maglev controllers are explicitly built on current feedback.
- **Flux feedback (Hall sensors / flux observers)** enlarges the stable parameter region and improves anti-jamming vs gap-only or current-only feedback. The IEEE study "On both flux and current feedback control technique for maglev suspension system" finds current feedback and flux feedback each have "respective disadvantages," and the combined flux+current method "reject[s] the deficiencies of the two methods," validated by single-electromagnet suspension experiment. Flux-density observers further improve robustness, and for a PM-biased yoke where PM bias can drift with temperature and saturation, direct flux measurement is especially valuable.
- **Recommendation:** add per-coil current sensing (essential), add Hall flux sensors per yoke (high value for PM-biased units), keep/redundify the gap sensors, and fuse everything with the IMU through an EKF/UKF.
	- ==**What is the objective of flux feedback? Is it redudancy on current/gap sensing or to support fusing with the same? Power and gap govern controller requirements, why should I necessarily 'care' about flux = f(power, gap)**== → [[Maglev - Sensing and Flux Feedback]]

### I. Electrical / implementation interface
**Power stage.** Drive each coil from a current-controlled PWM H-bridge (4-quadrant, so the coil can be actively de-fluxed, not just energized) or a linear transconductance amplifier for lowest noise. The amplifier must supply voltage headroom to overcome back-EMF and L·di/dt during fast transients — slew-rate/voltage saturation is a real limit on closed-loop bandwidth and must be modeled in the loop.
	**==Currently using PWM H-bridges. Talk to me about linear transconductance amplifier. Any good analog methods for current control -- that we can custom design (PCB) without too much cost / knowledge overhead.==** → [[Maglev - Hardware and Implementation]]

**Current-loop bandwidth.** Per Microchip's MCAF current-loop tuning guidance, "Typical 3dB current bandwidth of industrial motor drives are 5% – 15% of the PWM frequency, or 1 – 3 kHz for a 20 kHz PWM." The current loop should be several times faster than the unstable mechanical mode √(k_s/m). Coil inductance is the limiting pole; lower N or higher bus voltage raises current bandwidth. Use double-update PWM to halve sample-to-update delay.

**Loop rate / discretization / latency.** Stiff unstable maglev plants are run at kHz position-loop rates (maglev nanopositioning examples run ~5 kHz; AMBs run multi-kHz). Budget total loop latency (ADC conversion+acquisition, compute, PWM update); anti-alias filter analog signals below Nyquist. Latency directly erodes the phase margin you need to hold a RHP pole.

**Compute target.** An MCU (e.g., C2000-class DSP/MCU) suffices for cascaded PID/state-feedback/ADRC/SMC and EKF at kHz; TI's C2000 approach, for instance, completes field-oriented processing and PWM update in under 500 ns to achieve >3 kHz control bandwidth. For the very fast inner current loop or sub-µs PWM update, FPGA offload is the proven route (FPGA current controllers run with MHz-class update rates). For NMPC/learned policies, an SoC (FPGA+CPU, e.g., Zynq-class) lets the FPGA run the kHz safety-critical inner loops while the CPU runs the slower (sub-kHz) MPC/learned outer loop. A practical split: FPGA = current loop + safety monitor; MCU/CPU = stabilizer + allocation + learning.
	**==This is a very meaningful suggestion. We have been running control loops on Arduino.** 
	**We are somewhat cost limited. Talk to me about different FPGA dev-board solutions + MCU solutions that don't cross $500. What advantages do the suggested MCU's provide over Arduino (is it primarily ADC performance)?==** → [[Maglev - Hardware and Implementation]]

**Magnetic non-idealities.** Flux saturation of the PM-biased yoke caps achievable force and breaks the linear k_i model at high current — keep operating flux below the knee and consider Hall feedback to detect it. Eddy currents in solid steel add lag and loss (laminated yokes/rails help). **Cross-coupling of flux between adjacent corners** is the magnetic analog of the statically-indeterminate problem and argues for either decoupling in the allocator/observer or a MIMO model that captures the mutual terms.

### J. Synthesis / recommended architecture & roadmap
**Recommended layered architecture (inside-out):**
1. **Inner current loop, per coil, on FPGA/fast MCU (kHz–tens of kHz):** PI current control on measured coil current; this linearizes each actuator to force≈k_i·i and isolates coil/back-EMF dynamics from the outer loop.
2. **MIMO stabilizer on z/pitch/roll modal coordinates (≈1–5 kHz):** start with state feedback + integral (pole placement / LQR) using EKF/IMU-fused states; this is the proven core. Plan a parallel **ADRC or super-twisting-SMC** variant for robustness to the (i/x)² nonlinearity, payload, and PM/thermal drift — the best modern-but-proven upgrade.
3. **Control allocation (same rate):** weighted/redistributed pseudo-inverse (upgradeable to QP) mapping the 3 modal force/torque demands to 4 coil-force commands, respecting current/flux-saturation limits and resolving the statically-indeterminate coupling.
4. **Optional outer learning/optimization layer (sub-kHz):** once the above flies, add either (a) constrained MPC (explicit/QP or Koopman-MPC / GP-MPC) for constraint handling and performance, or (b) a *residual* RL / RL-tuned-SMC policy, always behind a control-barrier-function safety filter and validated in sim with domain randomization before deployment.

**What to pursue first (honest assessment).** Given the user wants modern/learning methods but values robustness:
- **Do first:** fast current loop + EKF/IMU fusion + LQR/state-feedback stabilization + pseudo-inverse allocation. This *will* levitate the pod and is low-risk.
- **Do second (highest modern ROI):** swap/augment the stabilizer with **ADRC or super-twisting SMC** — biggest robustness gain for least model fidelity, both well-proven on maglev.
- **Do third:** **MPC (explicit or Koopman-based)** for principled constraint handling and to fold allocation into the optimizer.
- **Do last, carefully:** RL/learned control, only as a residual or auto-tuner on top of a stabilizing base, behind a safety filter, with sim-to-real domain randomization. Treat learning as performance optimization, not as the stabilizer.
- **Sensors:** add per-coil current sensing immediately; add Hall flux sensors and redundant gap sensors next; fuse with IMU. This is well-justified by the flux/current-feedback maglev literature and unlocks every advanced method above.

**I do not have enough control theory expertise to critique the suggested roadmap. However, key request -- plan out a scalable way to model, simulate, visualize, and iterate these stages (control loops, methods), effectively fashioning a sandbox for building up intuition for maglev and capturing insightful results. Like digital-twinning**. **Preferably in something accessible like Python, using OSS.** → [[Maglev - Python Simulation Sandbox]]

## Recommendations
1. **Lock the coil turn count against current-loop bandwidth.** Choose N so the current-loop 3-dB bandwidth (≈5–15% of PWM frequency, i.e., ~1–3 kHz at 20 kHz PWM per Microchip's MCAF guidance) is ≥5–10× the unstable mechanical pole √(k_s/m). If you cannot hit that, raise bus voltage or lower N. Benchmark: measure the actual open-loop unstable pole and current step response before committing.
2. **Instrument before you control.** Add per-coil current sensors and at least one Hall flux sensor per yoke now; wire the IMU into an EKF that estimates z/pitch/roll and their rates. Threshold to escalate: if gap-sensor noise forces derivative-gain reduction that costs phase margin, the observer/fusion is mandatory, not optional.
3. **Bring it up on classical control.** Implement inner current PI + outer LQR/state-feedback-integral on modal coordinates + weighted pseudo-inverse allocation. Success benchmark: stable hover with target gap and bounded current at all four corners, including a static-indeterminacy check (no slow current drift between opposite corners).
4. **Upgrade the stabilizer to ADRC or super-twisting SMC** once hovering, to gain robustness to payload/PM-thermal drift and the (i/x)² nonlinearity. Benchmark: maintain stability under a step payload change and a deliberate ±20% parameter mismatch.
5. **Add constrained MPC** (explicit/PWA for embedded feasibility, or Koopman-MPC if you go data-driven) when you need to respect current/voltage/gap limits during aggressive moves. Benchmark: no constraint violations during a commanded fast heave/tilt that saturates a naive controller.
6. **Only then explore learning** — residual RL or RL-tuned SMC behind a CBF safety filter, trained in a domain-randomized simulator and fine-tuned with few real samples. Benchmark/threshold to proceed: the safety filter must never be the active authority during normal operation; if it engages frequently, the learned policy is not ready.
7. **Defer zero-power.** Per your priorities, implement equilibrium-seeking/zero-power only after MIMO stabilization is robust; it lives naturally in the allocation/outer loop and the redundant 4th DOF.

## Caveats
- **Numbers are formula-level, not your hardware's.** k_i, k_s, the unstable pole √(k_s/m), and achievable bandwidths depend on your specific geometry, N52 bias point, gap, and mass — derive/identify them from your actual yoke (FEM + bench ID) before finalizing gains. The Schweitzer–Maslen textbook page text was not directly quotable here (paywalled); the formulation is corroborated by open peer-reviewed and lecture sources.
- **Much maglev literature is single-point or train-bogie**, not a free 4-corner rigid pod; the z/pitch/roll coupling and the statically-indeterminate 4→3 problem are specific to your geometry and the strongest reason to favor a centralized MIMO + explicit-allocation design over naive per-corner SISO loops.
- **Learning-based maglev results are largely simulation or lab-bench**, frequently SISO maglev balls, and several cited works are proposals/predictions rather than fielded systems; treat RL/NN claims as promising but unproven for primary stabilization of an unstable rigid pod.
- **Feedback linearization and exact decoupling are model-fragile**; do not rely on them as the sole stabilizer given PM-bias and thermal drift.
- **Your inductive gap sensors are noisy and the IMU has bias/drift**; the recommended observer/fusion mitigates but does not eliminate this — sensor quality ultimately bounds achievable closed-loop bandwidth on a RHP-pole plant.
- Some sources are vendor/educational/app-note pages (Calnetix, MIT course notes, TI/Microchip) used only for well-established engineering facts; the control-method claims rest on peer-reviewed IEEE/Elsevier/Springer/MDPI maglev and AMB papers.

## Questions
1. Reason with me about how the nested loop accomplishes certain design objectives. 
	1. Wouldn't both loops ultimately be actuating the current? That's the only knob. How would they not fight each other (differing targets?)
	→ [[Maglev - Control Theory Fundamentals]]
			**Great explanation @Claude. I'm in agreement with the nested controller architecture : )**
# Maglev - Control Theory Fundamentals

*Support doc for [[Levitation Research Claude]] — covers loop shaping for RHP-pole plants, Lyapunov stability, backstepping, and the nested-loop question (Section B/C + Questions §1).*

---

## 1. Loop Shaping — Why It Matters for a RHP-Pole Plant

### The Problem With an Unstable Pole

You understand that an RHP pole means the open-loop system is unstable. But what does this concretely impose on the *loop design*?

The Bode gain-phase integrals (Bode's sensitivity integral, Poisson integral) impose a fundamental constraint: **for a plant with a real RHP pole at p, the closed-loop loop gain L(jω) = C(s)P(s) must encircle the −1 point the right number of times (Nyquist), and the phase of L at gain crossover must be better than −180°.** More concretely, with a pole at p = √(k_s/m):

- The open-loop Bode magnitude plot *must* cross 0 dB (gain crossover) **above** the frequency p (otherwise you cannot stabilize it). This is a hard lower bound on bandwidth.
	- An RHP (unstable) pole at frequency `p = √(k_s/m)` means the plant is actively running away at that rate. To catch it, your feedback loop has to be "paying attention" — i.e., have loop gain > 1 (above 0 dB) — at frequencies at least up to `p`.
	- **Gain crossover** is where the open-loop gain drops through 0 dB; above it the loop gain is <1 and the controller effectively stops acting. So if crossover sits *below* p, the loop has already gone limp at the very frequency the plant diverges → it can't be stabilized.
	- Hence crossover **must** be above p. That's a *hard lower bound* on closed-loop bandwidth — not a tuning preference. (Upper bound comes from sensor noise, current-loop speed, delay.)
	- **Concretely for your pod: p ≈ 4.3 Hz, so the outer loop must cross over above ~4.3 Hz — practically you target several× that.**
- The phase at crossover must still be > −180° — you need positive phase margin.
- But the RHP pole contributes **phase lag** of its own at high frequency, which means the loop has less phase budget than a stable plant of the same order.

This combination — *must crossover above p* and *phase is eroded by the RHP pole* — means you have to carefully shape where the gain crosses and how much phase you have there.

### What Loop Shaping Does

Loop shaping is the engineering practice of **designing L(jω) = C(jω)P(jω)** in the frequency domain to meet stability margins and performance specs, rather than computing pole placements algebraically.

The idea is: you know what the closed-loop transfer function T = L/(1+L) needs to look like for good tracking. You also know what the plant P looks like. The controller C = L/P is then "whatever it takes" to make L(jω) have the desired shape. In practice:

- **High gain at low frequency** → small steady-state error (integral action gives −20 dB/dec roll-off toward DC)
- **Gain crossover around the target closed-loop bandwidth** with ≥ 45° phase margin
- **Steep roll-off at high frequency** → attenuate sensor noise

For the maglev plant, P(s) = k_i / (ms² − k_s):

```
|P(jω)| in dB:
        \         <- starts flat or rising at low ω
         \
          [crossover region: must have +phase here]
           \
            \     <- rolls off above
```

The plant already has a +20 dB/dec rise at low frequencies (the RHP pole adds phase lag, the double integrator adds phase lag) — meaning you need the controller C to add phase *lead* near crossover.

### Lead Compensation

A lead compensator adds phase near a target frequency:

$$C_{lead}(s) = K \frac{\tau s + 1}{\alpha \tau s + 1}, \quad \alpha < 1$$

Peak phase lead occurs at ω_m = 1/(τ√α), and the peak lead angle is sin⁻¹((1−α)/(1+α)). A single lead stage gives up to ~60°. The cost is a gain boost at high frequency (more noise amplification).

For maglev: place the peak lead near the gain crossover frequency (which must be > √(k_s/m)), and cascade lead stages if you need more phase. This is classical loop shaping by hand.

### Quantitative Feedback Theory (QFT) — the Systematic Version

QFT is loop shaping made rigorous for uncertain plants. It maps the uncertainty in k_i, k_s, m (your parameters will vary with payload and PM thermal drift) into "forbidden regions" on the Nichols chart (a log-magnitude vs. phase plot of L), then designs C to keep L outside those regions at all frequencies. The result is a controller that maintains specified gain/phase margins across the entire parameter uncertainty set — which is exactly what you need given PM thermal drift and payload changes.

QFT has been demonstrated on a real magnetic levitation system to improve gain/phase margins and sensitivity functions over a baseline design. It's more work than hand-designed lead compensation but directly certificates robustness.

---

## 2. Lyapunov Stability — What It Means Numerically

#### ==Note to self: Do not worry about this much. Gets too into the weeds of rigorous math; I think it will be a rabbit hole that detracts from crucial modeling/controller intuition==
### The Idea

Lyapunov's method is an energy-based way to prove stability *without solving the differential equations*. The insight: if you can find a function V(x) that (a) is always positive, (b) decreases along every trajectory of the system, then the system must converge to where V is minimized — the equilibrium.

Formally, V is a **Lyapunov function** for ẋ = f(x) if:
1. V(0) = 0 and V(x) > 0 for all x ≠ 0 (positive definite)
2. V̇(x) = ∇V · f(x) < 0 for all x ≠ 0 (negative definite derivative)

If such V exists, the equilibrium x=0 is **globally asymptotically stable**.

### Numerically: What V̇ < 0 Means

Take a simple example: a damped spring, ẋ₁ = x₂, ẋ₂ = −ω²x₁ − 2ζωx₂.

Let V = ½x₁² + ½x₂²/ω² (a weighted sum of squared states — quadratic Lyapunov function). Then:

$$\dot{V} = x_1 x_2 + \frac{x_2}{\omega^2}(-\omega^2 x_1 - 2\zeta\omega x_2) = x_1 x_2 - x_1 x_2 - \frac{2\zeta}{\omega} x_2^2 = -\frac{2\zeta}{\omega} x_2^2$$

V̇ ≤ 0 when ζ > 0 — confirming damping stabilizes. This is the Lyapunov proof of what you knew intuitively.

For a maglev system, the Lyapunov function is typically something like:

$$V = \frac{1}{2}m\dot{x}^2 + \frac{1}{2}k_i (i - i_{eq})^2 + \text{integral error term}$$

(Kinetic energy + coil energy + tracking error energy.) Proving V̇ < 0 under the proposed control law tells you the controller stabilizes the system even in the nonlinear regime — without needing to solve the nonlinear ODE.

### What "UUB" and "Asymptotic" Mean Numerically

- **Globally asymptotically stable (GAS):** every trajectory, regardless of initial condition, converges to zero. Strong claim, requires V̇ < −α(‖x‖) strictly.
- **Uniformly ultimately bounded (UUB):** trajectories enter and stay in a ball of radius ε around the origin. V̇ ≤ −α(‖x‖) + c outside the ball. In practice: the error stays bounded (doesn't blow up) but may not converge to exactly zero — due to disturbances or approximation error. Most nonlinear adaptive controllers on real hardware give UUB, not GAS.

For control design purposes: if your Lyapunov analysis gives UUB with a known bound ε, you know the pod will hover within ±ε of the target gap even in the worst case the analysis covers.

---

## 3. Backstepping — Numerically

Backstepping is a recursive control design procedure for *cascaded* nonlinear systems. It's perfectly suited to maglev because the plant is naturally cascaded: electrical dynamics (current) → mechanical dynamics (position).

### The Core Idea

Instead of designing one controller for the full nonlinear system, you design in *steps*, using virtual control inputs at each stage.

**Maglev has exactly two stages:**

**Stage 1 — Mechanical subsystem.** The gap x is controlled by the force F, which depends on current i. Treat i as the "virtual control" for x:

The gap error: e₁ = x − x_d (desired gap).

Choose a "virtual desired current" i_d(x, ẋ, x_d) such that if i actually equaled i_d, the gap dynamics would be stable. This is done by picking:

$$\dot{e}_1 = \dot{x} - \dot{x}_d$$

and choosing i_d so that:

$$m\ddot{x} = F(i_d, x) \Rightarrow \text{stable } e_1 \text{ dynamics}$$

For instance, i_d might be chosen as the current that would produce a force F = mg + m(-k_1 e_1 - k_2 ė_1) — i.e., cancel gravity and add damping. Then e₁ converges to zero *if i really equals i_d*.

**Stage 2 — Electrical subsystem.** The current i is controlled by coil voltage V. Define the current tracking error:

$$e_2 = i - i_d(x, \dot{x}, x_d, \ldots)$$

The voltage V is now chosen to drive e₂ → 0 (make the current follow the virtual reference i_d). The coil equation L·di/dt = V − Ri gives:

$$V = Ri + L\frac{di_d}{dt} - k_3 e_2$$

This makes ė₂ = −k_3 e₂/L, exponentially stable.

**Lyapunov function for the full system:**

$$V = V_1(e_1) + V_2(e_2)$$

You prove V̇ ≤ −c₁e₁² − c₂e₂² by choosing the gains k₁, k₂, k₃ appropriately — the two stages cooperate rather than fight, because Stage 2 is designed to serve Stage 1.

### Why This Is Different From Two Independent PID Loops

In naive cascaded PID, each loop independently minimizes its own error. Backstepping explicitly computes what the inner loop's reference *needs to be* (i_d) to make the outer loop stable. The inner reference is a **function of the outer-loop state**, not a separate setpoint. This means the two loops are mathematically consistent by design.

---

## 4. The Nested Loop Question (from §Questions)

> *Wouldn't both loops ultimately be actuating the current? That's the only knob. How would they not fight each other?*
### Structure of the Nested Loop

```
x_d (desired gap)
    ↓
[Outer loop: position/stabilizer]
    ↓ outputs: i_reference (desired current) 
[Inner loop: current controller]
    ↓ outputs: V_PWM (duty cycle)
[H-bridge + coil]
    ↓ actual current i
[Plant: gap dynamics]
    ↓ actual gap x
    ↑ (back to outer loop)
```

**There is only one actuator — the coil voltage (PWM duty cycle).** The outer loop never directly sets the voltage. It outputs a *current setpoint* i_ref. The inner loop then drives the actual current to i_ref. So:

- The **outer loop's output** is the **inner loop's reference input**. They do not have conflicting targets — the outer loop is literally telling the inner loop what it wants.
- The **inner loop's output** is the PWM voltage to the H-bridge. The outer loop never touches this.

There is one knob (voltage), and exactly one controller touching it (the inner loop). There is no conflict.

### Why Separate Them At All?

Couldn't you just run one outer loop that outputs voltage directly? Yes — that's the "single-loop" architecture. But it has serious problems:

1. **The coil dynamics (L di/dt) appear inside the outer loop.** The inductance L and resistance R change with temperature and saturation. Every time L changes, the outer loop's model is wrong. With the current loop, the outer loop sees F ≈ k_i·i — the inductance is "inside" the inner loop and doesn't appear in the outer loop's model.

2. **Bandwidth separation.** The current loop runs much faster (1–10 kHz) than the outer mechanical loop (100–1000 Hz). The separation (at least 5–10×) means the current loop appears "instantaneous" to the outer loop — by the time the outer loop tries to change i_ref, the actual current has already reached the setpoint. This is the singular-perturbation argument: the fast inner subsystem can be analyzed as algebraic (settled) from the outer loop's perspective.

3. **Saturation and current limiting.** The inner current loop can enforce hard current limits (the H-bridge has a max safe current). If the outer loop commands too high an i_ref, the inner loop clamps it. Without the current loop, a naive position controller could command a voltage that drives the coil to destructive current.

4. **The outer loop sees a linear actuator.** Because the current loop makes i ≈ i_ref, and F ≈ k_i·i, the outer loop effectively commands force directly — not voltage. This enormously simplifies outer loop design (it no longer needs to know L, R, or back-EMF).

### The Timescale Argument — Concrete Numbers

Say your unstable mechanical pole is at ω_mech ≈ 50 rad/s (~8 Hz). You need the outer loop bandwidth ~5–10× this, i.e., ~50–100 Hz. The current loop bandwidth needs to be ~5–10× *that*, i.e., ~500–1000 Hz. At 20 kHz PWM, a PI current loop can achieve 1–3 kHz bandwidth easily.

So the current loop settles in ~0.3–1 ms; the outer loop operates on a ~10 ms timescale. Every time the outer loop updates i_ref, the current loop has had 10–30 full control cycles to settle the current to that reference. From the outer loop's perspective, the current just *is* whatever it commanded — the inner dynamics are invisible.

### What Happens Without the Inner Loop?

Your Arduino-based single-loop likely directly commands PWM duty cycle. The observed problems are:
- Gain sensitivity: L, R variation changes the current for a given duty cycle, so the effective force-per-duty-cycle changes.
- Poor bandwidth: the outer loop's phase budget is eroded by the L/R electrical pole.
- No current limiting: you rely on the sense of the controller not commanding saturation.

Adding the inner current loop is the single most impactful control architecture change you can make before touching any of the other methods.

---

*See also:*
- *[[Maglev - LQR and State Feedback]] — full-state optimal alternative to the loop-shaping/lead approach here; same RHP-pole bandwidth floor applies*
- *[[Maglev - PM Bias and Force Linearization]] — derives the k_i, k_s stiffness terms the outer loop uses*
- *[[Maglev - Coupling and Geometry]] — MIMO extension of this single-actuator picture to 4 corners*
- *[[Maglev - Hardware and Implementation]] — discusses what hardware (MCU/FPGA) can close these loops at the required rates*

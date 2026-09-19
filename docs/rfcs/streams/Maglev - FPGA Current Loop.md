# Maglev - FPGA Current Loop

*Support doc for [[Maglev - Hardware and Implementation]] §4 — a short explainer of how an FPGA runs the inner current loop, and why that helps this system. Companion to [[Maglev - Control Theory Fundamentals]] (why the inner loop must be fast) and [[Maglev - Cytron MD25HV Motor Driver]] (the driver limitation this addresses).*

---

## Role: inner current loop only

The FPGA does one job — **regulate coil current and generate the PWM that drives the H-bridge.** Nothing above that. The stack splits cleanly:

| Layer | Runs on | Update rate |
|---|---|---|
| Current loop (PI) + PWM gen | **FPGA** | 100 kHz – 1 MHz |
| MIMO stabilizer + allocation | MCU / SoC CPU | ~1 kHz |

The MCU computes the 4 per-coil current setpoints and hands them down; the FPGA holds each coil at its setpoint. This is the same inner/outer separation as [[Maglev - Control Theory Fundamentals]] — the FPGA just makes the inner loop fast and deterministic enough that it never interferes with the outer one.

### Update rate ≠ bandwidth (reconciling with Sim Layer 2)

The column above is **update rate** — how often the PI datapath re-fires and PWM refreshes — *not* closed-loop bandwidth. Don't confuse it with the ~1 kHz current-loop figure in [[Maglev - Python Simulation Sandbox]] Layer 2, which is a *bandwidth*. Three distinct clocks:

| Quantity                                 | Value                                  | Set by                                           |
| ---------------------------------------- | -------------------------------------- | ------------------------------------------------ |
| Mechanical unstable pole                 | ~4.3 Hz                                | plant physics (η-corrected, see CLAUDE.md)       |
| Outer MIMO loop                          | ~1 kHz                                 | must sit ≫ the pole                              |
| Current-loop closed-loop **bandwidth**   | ~few hundred Hz – 1 kHz                | ≥5–10× the pole → **the Sim Layer 2 target**     |
| Current-loop **update / execution** rate | 16 kHz (MD25HV) → 100 kHz–1 MHz (FPGA) | switching + ADC-sync + jitter, **not** bandwidth |

- **Bandwidth** is a *control requirement*. The plant is slow (4.3 Hz pole), so the current loop only needs to be ~5–10× faster than that to be transparent to the outer loop — a few hundred Hz to ~1 kHz is plenty. The sim's `dt = 1e-3` is honest, not under-spec'd.
- **Update rate** is an *implementation rate*. You always want update ≫ bandwidth (~10–20×) so the discrete loop looks continuous and keeps phase margin, *and* so it ticks fast enough to regulate PWM ripple and sample the ADC at the switching midpoint. That's what forces tens-of-kHz-and-up, and where 100 kHz–1 MHz comes from.

## System block diagram

![[FPGA Group.png|529]]

- **FPGA is the only block in the fast inner loop** — it drives PWM into the H-bridge and reads coil current straight back, closing the current loop in µs without the MCU involved.
- **MCU never sees raw current** — it issues 4 current setpoints (`i_set[4]`) and reads pod position (gap/Hall/IMU), closing the mechanical loop at ~1 kHz.

## How it works — it's a circuit, not a program

An FPGA doesn't execute instructions in sequence like a CPU. You describe a digital **circuit** in HDL (Verilog/VHDL); the toolchain synthesizes it into physical logic — flip-flops, adders, DSP multiply blocks, wired together. **The PI controller becomes hardware**, not a software `for` loop.

The datapath for one coil, clocked at ~100 MHz:

```
ADC (coil current) ──► [ − setpoint ] ──► error
error ─► [ × Kp ]──────────────┐
error ─► [ × Ki ]──►[ accum ]──┤
                               ▼
                            [ sum ] ──► duty ──► [ PWM compare ] ──► gate sig.
```

Consequences that matter:

- **Deterministic + fast.** The whole error→duty path finishes in a handful of clock cycles (tens of ns), *every* cycle. No OS, no interrupt latency, no instruction fetch → no jitter, so no phase-margin loss from timing wobble. Loop updates at MHz rates instead of the few-kHz an MCU manages.
- **True parallelism.** 4 coils = 4 identical PI datapaths running literally simultaneously, not one ISR time-slicing between them.
- **Fixed-point, not float.** The datapath uses fixed-point arithmetic (chosen bit widths) for speed and resource efficiency — Kp, Ki, and the accumulator are scaled integers, not IEEE floats. This is a design step (pick scaling, check for overflow), not a limitation.

## Why it helps *this* project

Beyond raw speed, the concrete win is **ADC–PWM synchronization** — the exact thing the [[Maglev - Cytron MD25HV Motor Driver]] can't do (fixed 16 kHz switching, decoupled from input, no sync exposed).

Because the FPGA generates its own PWM, it knows precisely where the switching edges are, so it can trigger the current-sense ADC sample at the **PWM midpoint** — the quiet instant between switching transitions, where the ripple current is at its average. Sampling there gives a clean current reading without a filter delay in the loop. On the MD25HV you're sampling blind to the switching phase and fighting ripple noise. This sync capability is the strongest single argument for FPGA offload, more than the MHz loop rate itself.

## Two ways to package it

- **Standalone FPGA (Arty A7)** — FPGA runs current loops; a separate MCU (Teensy 4.1 / C2000) runs the outer stabilizer, setpoints crossing between them over SPI/parallel. See [[Maglev - Hardware and Implementation]] §4.
- **SoC FPGA (DE10-Nano)** — FPGA fabric *and* an ARM CPU on one chip. FPGA does the current loops, the on-chip ARM runs the outer MIMO loop (even under Linux). No inter-chip link for setpoints — they cross on-die.

## Status

Not committed. The open decision (carried from the last session) is whether the MD25HV's 16 kHz-fixed / no-sync limitation *alone* justifies going straight to FPGA offload, or whether the MD25HV is an acceptable interim OTS driver while a simpler MCU current loop is characterized first. The FPGA is the answer *if* that limitation proves to be the binding constraint — decide after the MD25HV characterization bench sequence produces real numbers.

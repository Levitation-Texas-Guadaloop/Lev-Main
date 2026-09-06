# Maglev - Hardware and Implementation

*Support doc for [[Levitation Research Claude]] — covers linear transconductance amplifiers, PCB-buildable current control, FPGA/MCU options under $500, and what they offer over Arduino.*

---

## 1. PWM H-Bridge vs Linear Transconductance Amplifier

### What You Have: PWM H-Bridge

A PWM H-bridge (L298, DRV8876, IFX007T, etc.) switches the full bus voltage across the coil at a duty cycle that averages to the desired voltage. The coil inductance low-pass filters the switching current, yielding a roughly smooth DC current. A current sense resistor + comparator or a PI controller closes the current loop.

**Pros:**
- High efficiency (MOSFET switches dissipate only switching losses)
- Easy to buy or build
- Can actively de-flux the coil (4-quadrant: current can be driven up or down quickly)
- PWM frequency sets the current ripple and current-loop bandwidth

**Cons:**
- PWM current ripple (at switching frequency). At 20 kHz, ripple can be a few percent of rated current — acceptable for most control loops but adds noise to the current sense signal.
- Switching noise couples into sdamense signals and adjacent circuits; requires careful PCB layout (ground planes, decoupling, filter caps).
- Current-loop bandwidth limited to ~5–15% of PWM frequency (per Microchip MCAF guidance): at 20 kHz PWM, you get ~1–3 kHz current bandwidth. Adequate for this application.

**Decision: OTS preferred for the H-bridge stage.** Custom PCB is only in scope if we end up going the linear transconductance/VCCS route below, which is unlikely near-term. Candidate part evaluated: **Cytron MD25HV** — see [[Maglev - Cytron MD25HV Motor Driver]] for spec summary and frequency-related concerns (output PWM is fixed at 16 kHz and decoupled from input command frequency, no ADC-PWM sync).

### Linear Transconductance Amplifier (Voltage-Controlled Current Source)

A transconductance amplifier (or VCCS — voltage-controlled current source) takes a voltage input and produces a proportional output current, regardless of load impedance. No switching — the output transistor(s) operate in the linear region.

$$I_{out} = G_m \cdot V_{in}$$

where G_m (transconductance, in A/V) is the design parameter.

**Pros:**
- Zero switching noise — very clean current waveform
- Bandwidth limited only by op-amp GBW and transistor f_T, not PWM frequency. Achievable bandwidth: 10–100 kHz easily
- No current ripple → cleaner Hall/gap sensor readings
- Simple control: current is directly proportional to a DAC or analog command voltage

**Cons:**
- Poor efficiency: the output transistor dissipates (V_supply − V_coil) × I continuously. For a 24V supply and a coil at 5V × 2A = 10W coil power, the transistor might dissipate (24−5)×2 = 38W — requiring a substantial heatsink.
- Not suitable for high-power applications. Fine for small research coils (< 50W); impractical for large drives.
- Cannot actively reverse current without a bipolar supply or additional circuitry.

### The Howland Current Pump — PCB-Buildable

The Howland current pump is the classic op-amp VCCS circuit. A standard (non-improved) Howland pump:

```
          R1      R2
 Vin ----[R1]----+----[R2]---- Output (to coil)
                 |
                [R3]         R1 = R3, R2 = R4 (for ideal operation)
                 |
        +--------+--------+
        |                 |
       [+]   Op-amp      [-]
        |                 |
        +---[R4]----------+---[Rsense]--- GND
```

When the resistors satisfy R1/R2 = R3/R4, the output current through the load is:

$$I_{load} = \frac{V_{in}}{R_2} \cdot \frac{R_1}{R_3}$$

Independent of load voltage (within the op-amp's output swing). This is a true VCCS.

**The improved Howland pump** adds one more resistor to correct output impedance error from resistor mismatch — important for driving inductive loads.

**Practical implementation for a maglev coil:**
- Use a rail-to-rail output op-amp (OPA549, OPA547, or OPA544 for higher current) capable of the coil current.
- The OPA549 can source/sink up to 8A continuously, has GBW of ~0.9 MHz, and costs ~$15–20. It runs from ±15V (or single 30V supply) and has a current limit pin — perfect for protection.
- For 2A coils: use OPA544 (~$10, 3A peak), single-supply friendly.
- PCB layout: keep the sense resistor (Rsense) close to the output, use 4-wire Kelvin sense if Rsense < 0.1Ω, minimize trace inductance on the output path.

**Bill of materials per channel (rough):**
- OPA549T op-amp: ~$15
- 4× matched resistors (0.1% tolerance): ~$2
- Heatsink + thermal pad: ~$3
- Sense resistor (0.05–0.1Ω, 1W): ~$1
- Decoupling caps, protection diode: ~$2
- **Total: ~$25/channel** + PCB cost

For 4 channels (one per corner): ~$100 in components. Feasible.

### Recommendation

For a research prototype where **signal cleanliness and bandwidth are more important than efficiency**: build a linear VCCS per channel. For a system where you'll be running continuous hover for extended periods and coil power is significant (> 20W per coil), stick with PWM H-bridges and put effort into good current-loop design and noise filtering.

A hybrid is also possible: use PWM H-bridges for the bulk current control, but add analog compensation (feedforward + analog filter on the sense signal) to smooth the loop.

---

## 2. Arduino Limitations — What You're Hitting

The limitations are not primarily ADC performance (though that is one factor). The full picture:

| Constraint | Arduino Uno/Mega | Impact on Maglev |
|---|---|---|
| **Loop rate** | ~1–10 kHz realistic with ADC + compute | Outer loop OK; inner current loop marginal |
| **ADC resolution** | 10-bit (0–1023 counts) | 1 LSB = ~5 mV at 5V ref; acceptable for gap, marginal for current |
| **ADC sample time** | ~100 µs per conversion (default, up to 10 channels muxed) | Limits multi-sensor sampling rate |
| **Floating-point** | Software float on 8-bit AVR: ~50–200 cycles/op | Complex controller (state-feedback, EKF) is too slow |
| **No hardware PWM synced to ADC** | PWM and ADC run asynchronously | Noise injection: ADC sampling during PWM transitions |
| **Single core, no DMA** | All computation serialized | Can't overlap ADC sampling with control computation |
| **No hardware interrupt-driven current loop** | Interrupt latency varies | Current loop jitter → phase margin loss |
| **Memory** | 2–8 KB SRAM | Not enough for state-space matrices + EKF covariance |

The ADC resolution is actually acceptable for most maglev applications. The real killers are: **loop rate** (too slow for an inner current loop at 1+ kHz alongside a MIMO outer loop), **floating-point speed** (state-feedback + EKF is computationally intensive), and **lack of hardware-synchronized sampling** (ADC during PWM switching introduces noise).

---

## 3. MCU Options Under $500

These are development boards with genuine performance advantages. Prices are approximate retail (2024–2025).

### TI C2000 — LaunchXL-F28379D (~$40–50)

The gold standard for embedded power-electronics control. Used in motor drives, AMBs, and power converters professionally.

- **Dual-core 200 MHz C28x DSP** — both cores can run simultaneously (one for current loop, one for outer stabilizer)
- **16-bit ADC** at up to 3.5 MSPS — 16-channel, with hardware ADC-triggered-by-PWM synchronization (sample exactly at PWM period midpoint to minimize switching noise)
- **ePWM modules** — up to 16 PWM channels, dead-band insertion, trip-zone protection, synchronized across channels
- **CLA (Control Law Accelerator)** — a secondary real-time processor that runs control code independently, freeing the main CPU
- **TI MotorControl library** — includes current-loop PI, Park/Clarke transforms, all usable for maglev inner loop

This is the board the research doc implicitly refers to when it mentions "sub-500 ns FOC processing." It's the best choice if you want to eventually implement MPC or EKF alongside a fast current loop on a single board.

### STM32 Nucleo-F767ZI (~$25) or Nucleo-H743ZI (~$30)

ARM Cortex-M7, 216–480 MHz with hardware FPU.

- **Floating-point:** single and double precision FPU, 1–4 clock cycles per operation → state-feedback and EKF are feasible
- **12-bit ADC** (F767), **16-bit ADC** (H7 series with sigma-delta peripheral) at up to ~5 MSPS
- **Advanced timers** synchronized with ADC for low-noise current sensing
- Large ecosystem (STM32CubeIDE, HAL, FreeRTOS)
- Not as specialized for power control as C2000, but much easier to program

Good choice if you want flexibility and Python/C++ familiarity. The H743 in particular is powerful enough to run a full EKF + MIMO state-feedback + 4-channel current loops.

### Teensy 4.1 (~$30)

600 MHz ARM Cortex-M7 (NXP iMXRT1062). Extremely popular in hobbyist advanced control projects.

- Very fast FPU — state-feedback and EKF are easily real-time at 1 kHz
- 12-bit ADC (oversampled to 16-bit with software averaging)
- Up to ~100 kHz PWM frequency (FlexPWM peripheral)
- Arduino-compatible ecosystem (familiarity) but with real MCU performance
- No hardware ADC-PWM sync (compared to C2000), but manageable with careful ISR design
- **Best starting point if you're coming from Arduino** — same IDE, same syntax, 100× more performance

### ESP32-S3 / ESP32-P4 (~$15–25 dev boards)

Dual-core 240 MHz Xtensa or RISC-V. Not ideal for primary control (no hardware FPU on most variants, ADC is mediocre), but useful as a companion processor for telemetry, WiFi data logging, or running higher-level optimization. Not recommended as the primary control MCU.

---

## 4. FPGA Options Under $500

For the inner current loop or high-speed PWM generation, an FPGA can close loops in the microsecond range — far beyond any MCU. For *how* an FPGA actually runs a control loop (why it's a circuit, not software) and what it buys this project specifically, see [[Maglev - FPGA Current Loop]].

### AMD/Xilinx Arty A7-35T or A7-100T (~$130–160)

Artix-7 FPGA, 33,280–101,440 logic cells.

- Industry-standard toolchain (Vivado, free for Artix-7)
- 6 ns routing delay → ~166 MHz logic, achievable current-loop update rates of 1–10 MHz
- DDR3 memory, Ethernet, USB-JTAG
- **Recommended for current-loop FPGA offload** if you go that route

### Intel/Altera DE10-Nano (~$130)

Cyclone V SoC FPGA: an FPGA fabric + ARM Cortex-A9 HPS (Hard Processor System) on one chip.

- FPGA runs the inner current loop at MHz rates
- ARM CPU runs Linux and can execute the outer stabilizer / MPC / Python-based optimization
- This is the architecture the research doc alludes to (FPGA + CPU SoC)
- Used in the Terasic FPGA ecosystem; OpenCL and hard floating-point DSP blocks

### Lattice iCEBreaker (~$40) or OrangeCrab (~$80)

Open-source FPGA ecosystems (iCE40 or ECP5). Less capable than Artix-7/Cyclone V (fewer resources, no hard DSP blocks on iCE40), but radically simpler toolchains (fully open: Yosys + nextpnr).

- Good for learning FPGA development without Vivado complexity
- iCE40: good for PWM generation and basic state machines; ECP5: has DSP blocks, usable for a real current loop

### Practical Split for Your System

**Near-term (< $200 total):**
- **Teensy 4.1 × 1** ($30): runs outer MIMO stabilizer + allocation + EKF at 1 kHz
- **TI DRV8876 H-bridge × 4** (~$5 each, $20): one per coil, hardware current limiting
- **Allegro ACS711 or ACS712 current sensors × 4** (~$3 each, $12): per-coil current measurement
- **Hall sensors × 4** (~$5): per-gap flux measurement
- **IMU** (MPU-6050, ~$5): fused with gaps

Total: ~$100–150. This is a real system.

**Medium-term (once you need faster current loop or MPC):**
- Add **Arty A7-35T** ($130) for FPGA-based current control at 100 kHz+ rates
- Use **LaunchXL-F28379D** ($45) as the main stabilizer MCU (it handles current + outer loop natively)

---

## 5. What the MCU Upgrade Buys You (Summary)

| Feature | Arduino Uno | Teensy 4.1 | TI C2000 F28379D |
|---|---|---|---|
| CPU speed | 16 MHz | 600 MHz | 200 MHz (×2) |
| FPU | None | Hardware (SP+DP) | Hardware (SP) |
| ADC resolution | 10-bit | 12-bit (OS to 16) | 16-bit |
| ADC-PWM sync | No | Partial | Yes (native) |
| Current loop bandwidth | < 1 kHz | 10–50 kHz | 3–10 kHz |
| EKF + state-feedback | No | Yes | Yes |
| Outer loop at 1 kHz | Barely | Yes | Yes |
| Cost | $25 | $30 | $45 |

The primary gains are **floating-point speed** (enabling state-feedback + EKF), **ADC quality**, and **hardware-synchronized sampling** (critical for clean current sense in a PWM environment).

---

*See also:*
- *[[Maglev - Control Theory Fundamentals]] — explains why the inner current loop needs to run much faster than the outer mechanical loop*
- *[[Maglev - Sensing and Flux Feedback]] — Hall sensor integration referenced here*
- *[[Maglev - Python Simulation Sandbox]] — once hardware is chosen, the sim validates controller design before deployment*

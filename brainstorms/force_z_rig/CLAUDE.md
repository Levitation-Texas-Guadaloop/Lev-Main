# force_z_rig: single-yoke F(z) characterization rig

## Problem / context

- We have good force models but no trustworthy measurements for a single small 1" yoke. The models are the Ansys Maxwell script (`scripts/yoke_model.py`, see `brainstorms/pyaedt-yoke-handoff.md`) and the reluctance model (`Magnetic-Circuit-Model/`).
- The only prior dataset, from Dec 2025, is unusable (Linear doc *Maglev - Actuator Characterization*, §8):
  - the zero drifted, including negative force at wide gaps
  - gaps were typed in by hand
  - tilt was not controlled
  - PWM was logged instead of current
- This rig is a side sprint while the two-yoke mechanical infrastructure is being refined. Linear: project *Two Yoke Test Rig*, stream S2 (LEV-44), with load cells in LEV-88 and lasers in LEV-11/LEV-91. LEV-90, the big-yoke rig, inspired the concepts.

## Objectives

- Produce a calibrated, reproducible **zero-current F(z)** curve for one small yoke, with the **laser as the gap reference**. No hand-typed gaps.
- Hold **roll** within limits at every point (roll is the priority axis). Pitch is locked mechanically and yaw is ignored.
- Sweep the regime **3 mm → crossover (~9.7 mm)**, where the magnet's pull F ≥ W, the weight of the moving parts. Gaps past the crossover are deferred.
- Accept the data only if F is positive and monotonic in gap, repeats over 3 up/down sweeps, and shows bounded zero drift. Then compare it with Ansys and the reluctance model.

## Key decisions so far

- **Axes (side view):** pitch = horizontal axis, yaw = vertical axis, roll = into-the-page axis.
- **Load cells:** keep the YZC-133 20 kg aluminum bar cells + HX711 (specs and wiring in LEV-88).
  - Calibrate each cell in place (rated output varies ±15%).
  - Safe overload is only 235 N per cell, so hard stops are required.
  - Mount each cell with its label arrow along the working pull.
  - The HX711 output is digital (DOUT/PD_SCK on GPIO), not analog.
- **Magnet near the cells:** the field doesn't affect the strain gauges. The risk is ferromagnetic hardware on the frame side of the cells, which adds a gap-dependent force a tare can't remove. Use non-magnetic hardware within about 150 mm of the poles.
- **Gap sensing:** 2× Baumer OM20-P0026 (16–26 mm, 1 µm repeatability, 4–20 mA output). Two lasers give exactly gap + roll, which is why pitch is locked rather than measured. The target must be **white matte**, not dark.
- **Actuation:** stepper + Tr8×2 lead screw (StepperOnline 17LS19-0406E-300Y, about 10 µm per step, self-locking), with an MGN12 rail for anti-rotation. Ball-screw stages and Actuonix P16 are parked.
- **Orientation:** right-side up, as on the pod. The crossover is set by the rig's ~6 kg moving mass, not by the pod. A 3 kg counterweight on pulleys keeps the sweep preloaded up to 9.7 mm.
- **Open items:**
  - weigh the moving parts
  - get Ansys results at 2–4 mm
  - settle the ~2× disagreement between the new Ansys script and the §8 "per-yoke" curve
  - check the laser cables and analog scaling

## Artifacts

### ★ `Single Yoke - Upright Roll Rig.html`: ACCEPTED DESIGN, start prototyping here
Live: https://claude.ai/artifact/ANqGeCG2LEzZvbXt2naJvg
- Concept D right-side up. Two stepper lead-screw actuators under an aluminum beam set gap and roll, with a pin joint on one end and a pin-in-slot on the other so pitch is locked. Load cells sit in series, in tension. Two lasers recessed 13.5 mm below the pole faces close a slow, step-by-step control loop. A 3 kg counterweight preloads the 3 → 9.7 mm sweep.
- Covers laser mounting and wiring, the actuator thrust and self-locking check, load tables, Nucleo wiring, the control-loop pseudo-code, and calibration through the counterweight pulleys.
- BOM is about $300–360 (about $150–180 per side, under the $200 cap). Includes an 8-step bring-up sequence and open items.

### `Single Yoke - Inverted Roll Rig.html`: superseded alternative
Live: https://claude.ai/artifact/6w2WHMEAc51wB9DNjf6bPa
- Concept D flipped: the yoke hangs poles-down over a fixed plate, so weight and magnetic pull point the same way and the load never reverses.
- Contains the reasoning about where the load reverses (net load crosses zero at ~9.7 mm when upright), plus the same actuator and BOM.
- Rejected because right-side up is more representative and the regime of interest ends at the crossover.

### `Single Yoke - F(z) Rig Concepts.html`: original exploration
Live: https://claude.ai/artifact/EdJgNUxt55UUnGAGm4f3A9
- Answers the first three questions: is the load cell right (yes, with the YZC-133 datasheet caveats), how does the magnet affect the cells, and what rig layouts are possible.
- Concepts A (Z-carriage), B (kinematic 3-point hang, a 1/10-scale LEV-90), C (shim posts), and D (two-actuator roll rig, upright), with a comparison table.
- Calibration protocol and early flags. D's details are superseded by the Upright Roll Rig page.

## Notes for agents

- The HTML files are snapshots of the live artifacts above. Edit the live artifact, then re-snapshot it here. Don't let the two drift apart.
- Force numbers come from `scripts/yoke_model.py` (0 A, 5–15 mm). Values below 5 mm are estimates until the Ansys 2–4 mm points are solved.

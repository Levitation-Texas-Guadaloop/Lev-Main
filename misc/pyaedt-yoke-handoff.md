# pyaedt + Maxwell yoke model — handoff (2026-09-30)

## Goal
Drive Ansys Maxwell 3D from Python (pyaedt) and rebuild the `1_Yoke_Forcings - Copy.aedt` yoke model as a parametric script.

## Environment (done, working)
- **Ansys:** Student 2025 R2 at `F:\Ansys2\ANSYS Inc\ANSYS Student\v252\AnsysEM`.
- **Env var:** removed stale `ANSYSEM_ROOT222` (pointed to a nonexistent v222); set user var `ANSYSEM_ROOT252` to the path above. Open a new terminal to pick it up.
- **Python:** `.venv/` in repo root (Python 3.11, not conda), `pyaedt 1.7.0`. `.venv/` and `sim/` are gitignored.
- **Run scripts with:** `.\.venv\Scripts\python <script>` from `Lev-Main`.
- **Student license = one AEDT session at a time.** Close all AEDT windows before running pyaedt, or it hangs/dies silently. If a run crashes, kill leftover `ansys*` processes.
- **Smoke test:** `scripts/pyaedt_smoke_test.py` (headless Maxwell 3D, draws a box) passes.

## Model: `scripts/yoke_model.py`
Rebuilds the original from code. Constants at the top; design variables `GapHeight`, `currL`, `currR`, `rollDeg`.
- Geometry: 5"x1" base block, two 1" N52 magnets (opposite polarity, Hc 955 kA/m, mu_r 1.07) with 0.5" steel caps, square copper coil around each magnet (`curr*250` amp-turns), steel track on a CS that rolls with `rollDeg`, vacuum region, `YokeForce` and `YokeTorque` (about -Y).
- Setup1: magnetostatic, 15 passes, 1% error, nonlinear residual 1e-3.
- Usage: `python scripts/yoke_model.py [--sweep] [--cores N] [--gpus N]` (default 4 cores). Rebuilds `sim/yoke.aedt` from scratch each run.

### Results (zero current, roll 0)
Fz at 5 mm = 120.3 N (pull toward track), torque ~0. Sweep (N): 5mm 120.3, 6 100.6, 7 85.8, 8 73.9, 9 64.3, 10 56.7, 11 50.1, 12 44.7, 13 40.1, 14 36.0, 15 32.6. Whole sweep ~11.5 min (~49 s/point). Not yet compared against the original model's results.

### Deviations from the original (flag if they matter)
- Steel is library `steel_1010`, not the original `1018 CS` / `1020 CS` (those live in PersonalLib). Change `STEEL` to swap.
- Coil starts at z=39.05 (on the base top), 8 mm shorter than original; the original overlapped the base and the solver rejects that. Amp-turns unchanged.
- `GapHeight` measured from yoke top (77.15); original used 77 + gap (~0.15 mm difference).
- Coils are plain square loops (no fillets). Force uses the global CS. Only the track rolls with `rollDeg` (unclear what the original rotated).

## Open issues / next steps
1. **Gap sweep has no stored results for 2, 3, 4 mm** (5-15 mm fine). Cause unknown: solver failure or unsaved results. Check AEDT messages / solve those points singly.
2. `print_results()` in the script still prints only the nominal point; needs a per-gap loop (the loop used to read results: `get_solution_data(..., variations={"GapHeight": ["8mm"]})`).
3. Add a current sweep (`currL`, `currR`) for the control model (original had -15..15 A, 5 A steps, plus roll 0-4 deg).
4. Verify magnet polarity (left = +z, right = -z, taken from "SouthUp" naming) and validate Fz against the original file.

## HPC / GPU findings
- **Cores:** Student caps at 4. AEDT defaults to 8 tasks and dies with an FNP license error; the script passes `cores=4, tasks=1`.
- **GPU (RTX 5060 Ti):** unlikely to work. Ansys GPU support for Maxwell 3D magnetostatic is for NVIDIA workstation/data-center cards, and each GPU needs 8 HPC tasks unlocked (Student has 4). Not tested directly with `--gpus 1`.
- **Parallel parametric sweeps:** need HPC Pack licenses (one per extra concurrent variation); Student has none, so points run serially on 4 cores. Practical speedups: fewer adaptive passes / looser error target, coarser mesh.
- Sources: [Ozen GPU in Maxwell3D](https://support.ozeninc.com/help-center/maxwell3d-gpu-acceleration), [Ansys student limits](https://ansys.synopsys.com/academic/students/ansys-electronics-desktop-student), [Ansys HPC parametric](https://www.ansys.com/blog/perform-parametric-studies-hpc2).

## Files
- `scripts/pyaedt_smoke_test.py`, `scripts/yoke_model.py` (new, uncommitted)
- Source models: `F:\Ansys2\OneDrive_1_9-30-2026\` (`1_Yoke_Forcings - Copy.aedt` is the full model; the other `.aedt` files there are older/simpler variants). Nothing there was modified.

# scripts/ — what each file models

Context for humans and agents. Units are mm unless stated; forces are N at 0 A coil current and zero roll unless a
column says otherwise. Ansys runs need Maxwell 3D (Student 2025 R2) driven through pyaedt in the repo `.venv`.
Student allows **one AEDT session at a time**: close AEDT (or `Get-Process ansys* | Stop-Process -Force`) before running.

## The model: `yoke_model.py`
Parametric single-yoke Maxwell 3D magnetostatic model, a rebuild of `1_Yoke_Forcings - Copy.aedt`.
- **Yoke:** 5" x 1" base, 2" tall at the legs with a 3" x 0.5" pocket between them (1.5" thick underneath). Two 1" legs,
  each a 1" N52 magnet plus a 0.5" steel cap. One rectangular copper coil per leg, 250 turns (`curr*250` amp-turns),
  tied to the pocket floor and pole face. Steel is `steel_1010` (library stand-in for the project's `1018 CS`).
- **Track:** steel bar above the yoke, default 12" (x, across the legs) x 36" (y, along the rail) x 1/4", rolled about Y
  by `rollDeg`. `GapHeight` is measured from the pole face to the track.
- **Design variables:** `GapHeight`, `currL`, `currR`, `rollDeg`. Force (`YokeForce`) and torque (`YokeTorque`, about -Y)
  are taken on the yoke body, magnets and coils.
- **Options on `build()`:**
  - `magnet`: `legacy` (Br 1.284 T, the original project's values, ~N35-class), `linear` (Br 1.45 T, mu_r 1.04, custom
    N52), `arnold` (library `Arnold_Magnetics_N52_20C` demag table). Default `legacy`; the other scripts use `linear`.
  - `track`: (x, y, thickness) in mm.
  - `slices`: list of y-intervals for the steel parts. Default one 1" slice. Magnets and each coil span the whole
    envelope, so one coil wraps the entire leg. Helpers: `stack_slices` (n 1" slices) and `lamination_sheets`.
  - `lam_sf`: homogenized lamination (stacking factor) for the yoke steel, not the track.
- **CLI:** `python scripts/yoke_model.py [--gap MM] [--sweep] [--magnet legacy|linear|arnold] [--cores N]` solves one
  point (or the 2-15 mm gap sweep) and prints Fz and torque. It recreates `sim/yoke.aedt` every run.
- Helpers used by the study scripts: `solve_point(m, gap_mm)` returns (Fz, peak |B| in the track).

## Study scripts (each writes a CSV into `sim/`, which is gitignored)
| Script | Question | Output |
|---|---|---|
| `magnet_crosscheck.py` | Does a custom linear magnet match the library nonlinear N52, and how far off is the old magnet? | `sim/magnet_crosscheck.csv` |
| `track_thickness_sweep.py` | Does a 1/4", 3/8" or 1/2" track change force or saturate, at 4/8/12 mm? `--thicknesses` picks which to solve; rows for other thicknesses already in the CSV are kept. | `sim/track_thickness_sweep.csv` |
| `stack_vs_single.py` | 1" yoke vs three 1" slices stacked along the rail with one coil around the whole leg (the real 9" yoke's build), plus an optional solid-extrusion diagnostic (`--extrude-in`). **Run once at 8 mm; see `HANDOFF_stack_vs_single.md`.** | `sim/stack_vs_single.csv` |
| `yoke_laminated.py` | Laminated 1" yoke with parametric sheet thickness: Ansys-style homogenized stacking factor, or explicit sheets. **Written, not yet run.** | `sim/yoke_laminated.csv` |

### Ansys lamination modeling (what `yoke_laminated.py` relies on)
Maxwell models laminations as a homogenized material: Stacking Type = Lamination, a stacking factor SF (0..1) and a
stacking direction V(1)/V(2)/V(3) = x/y/z. It works in magnetostatic, eddy-current and transient solvers. Sheet
thickness enters only through SF = t / (t + coating) and, in the eddy/transient solvers, the eddy paths. Plotted B is
the average over steel and insulation, so steel B = plotted B / SF. Core-loss coefficients need manual rescaling
(Kh/SF, Kc/SF, Ke/sqrt(SF)). A magnetostatic force run is therefore mostly insensitive to *thickness* and sensitive to
SF; eddy lag needs the eddy-current or transient solver. Source: Maxwell help, "Lamination Modeling".

## CSV columns
Common: `Fz_N` vertical force (positive = pull toward the track), `B_track_peak_T` maximum |B| anywhere in the track
volume (a local peak, not a section average; NaN means the field read failed), `gap_mm` = `GapHeight`.

- **`magnet_crosscheck.csv`:** `magnet` (legacy / linear / arnold), `gap_mm`, `Fz_N`, `vs_arnold_pct` (force relative to
  the Arnold row). Result so far at 3 mm: linear 239.9 N, arnold 240.1 N, legacy 187.3 N.
- **`track_thickness_sweep.csv`:** `magnet`, `steel`, `track_x_in`, `track_y_in`, `track_t_in`, `gap_mm`, `mmf_At` (0),
  `roll_deg` (0), `Fz_N`, `B_track_peak_T`. Nine rows (3 thicknesses x 3 gaps). Result: thickness changes force by
  under 1% (1/4" to 1/2"); peak track |B| falls from about 1.0 T (1/4") to 0.78 T (1/2") at 4 mm, so the track is not
  near saturation for the 1" yoke.
- **`stack_vs_single.csv`:** `build` (stack / extrusion), `n_slices`, `steel_in`, `depth_in`, `glue_mm`, `gap_mm`,
  `Fz_N`, `Fz_per_in_N`, `B_track_peak_T`, `ratio_vs_n_x_single` = Fz / (steel_in x Fz of the 1-slice stack).
  Result at 8 mm: 1" 94.4 N, 3" stack 479.6 N, 3" extrusion 479.9 N, so force per inch is 1.69x higher at 3" and the
  stack build is not the cause (cause hypothesised as end leakage, unconfirmed). CSV holds the latest run's cases only.
- **`yoke_laminated.csv`:** `case` (solid reference / laminated), `mode`, `t_mm`, `coat_mm`, `n_sheets`, `sf`, `gap_mm`,
  `Fz_N`, `B_track_peak_T`, `vs_solid_pct`.

## Other files
- **`list_materials.py` / `materials_list.txt`:** dump every material name AEDT knows (library and project). `--bh REGEX`
  tags matches with their permeability type. Comma-named structural entries (e.g. the Granta A36) are skipped because
  pyaedt cannot load them.
- **`pyaedt_smoke_test.py`:** minimal check that pyaedt can launch Maxwell 3D headless and draw a box.
- **`gen_lamination_dxfs.py`:** generates the SendCutSend lamination DXFs and acrylic jigs for the 1" laminated test
  yoke (A1008, 0.048" sheets). Not an Ansys script.

## Housekeeping
- `sim/*.csv` result files are tracked in git; everything else under `sim/` (AEDT projects, results folders) is ignored.
- `list_materials.py`, `stack_vs_single.py` and the sweeps refuse to start if an `ansysedt*` process is already running.
- Handoff for the stack study: `HANDOFF_stack_vs_single.md`. `yoke_laminated.py` has not been run.

## Known caveats
- All force numbers so far use `steel_1010`, not the project's own `1018 CS` / `1020 CS` curves (whose source is unknown).
- Magnet model matters: with the `legacy` magnet the 3 mm force is 187 N, with N52 (`linear`) 240 N.
- The Student license caps runs at 4 cores, serial solves, no GPU.
- Explicit-sheet lamination makes a very large mesh; prefer the homogenized mode unless validating.

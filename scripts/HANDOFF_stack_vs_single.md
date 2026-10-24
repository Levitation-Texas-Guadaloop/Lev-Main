# Handoff: `scripts/stack_vs_single.py`

**Status: run once (8 mm gap) plus a 3" extrusion diagnostic. The stack builds correctly; the surprising per-inch force increase with depth is reproducible but its cause is a hypothesis, not confirmed.** The Linear ticket LEV-109 was deliberately not edited; the results so far are investigative and inconclusive.

## Purpose
Compare a single 1" yoke with a **stack of 1" slices** (the "pseudo-laminated" yoke) at a fixed gap, to see whether the 3" yoke behaves like 3 × the 1" yoke. The real 9" yoke is built this way: nine 1" slices of cut 1018/1020 glued face to face along the rail, with one PM bar and one coil per leg. Background is in the Linear doc "Laminating steel yokes", section 0.

## What it builds
- **Slices:** `n` steel slices, each 1" thick along y (the rail direction), centred on y = 0. `yoke_model.stack_slices(n, glue_mm)` makes the y-intervals.
- **Per slice:** one steel base body (slab plus leg blocks united) and two steel caps. Names are `Base_1..n`, `CapL_i`, `CapR_i` (single slice keeps `Base`, `CapL`, `CapR`).
- **Shared across slices:** one magnet bar per leg spanning the whole stack, and **one rectangular coil per leg wrapping all slices**. The coil is not duplicated per slice. Its current sheet is a single YZ rectangle on the front wall.
- **Force and torque** are taken over every slice body, both magnets and both coils.
- **Track:** 12" (x) × 36" (y) × 1/4", the same for every case. Yoke steel and track are both `steel_1010`. Magnets are the `linear` N52 model (Br 1.45 T, μr 1.04). Gap 8 mm by default, 0 A, no roll.

## Parameters (CLI)
`python scripts/stack_vs_single.py [--gap 8] [--glue-mm 0] [--slices 1 3] [--cores 4]`
- `--slices 1 3 9` would also give the full 9" yoke (the coil volume and mesh grow with it).
- `--glue-mm` puts an air gap between slices to stand in for the epoxy line. Default 0, so slices touch.

## Output
`sim/stack_vs_single.csv` (CSVs under `sim/` are tracked; the project files are not), one row per case: `build` (stack / extrusion), `n_slices`, `steel_in` (inches of steel), `depth_in` (overall depth including any glue gaps), `glue_mm`, `gap_mm`, `Fz_N`, `Fz_per_in_N`, `B_track_peak_T`, `ratio_vs_n_x_single`. The ratio is Fz / (steel_in × Fz of the 1-slice stack). Each case runs in a fresh AEDT session and its project is saved as `sim/stack_<n>.aedt` or `sim/stack_ext<depth>.aedt`. `--extrude-in N` adds a solid N-inch body. Each run rewrites the whole CSV, so it only holds the cases from the latest run.

## How to read the result
- With `--glue-mm 0` the slices touch, so magnetically this equals a 3" extrusion: flux runs inside each slice and never crosses a joint. Any difference from 3 × the single yoke should be **end fringing** only. Fringing adds force and is a larger share of a short yoke, so the ratio should be **at or a little below 1** (an earlier version of this note said above 1; that was backwards).

## Results (8 mm gap, 1/4" track x 36", `steel_1010`, linear N52, 0 A) in `sim/stack_vs_single.csv`
| build | steel depth (in) | Fz (N) | per inch (N) | peak track \|B\| (T) | ratio vs depth x single | adaptive passes |
|---|---|---|---|---|---|---|
| stack, n=1 | 1 | 94.41 | 94.41 | 0.81 | 1.000 | 13 |
| stack, n=3 | 3 | 479.59 | 159.86 | 1.39 | **1.693** | 13 |
| extrusion | 3 | 479.90 | 159.97 | 1.39 | **1.694** | 14 |

- **The stack is fine.** A solid 3" extrusion gives the same force as three stacked 1" slices (0.07% apart), so slicing, shared faces and the single wrap-around coil are not the cause. The earlier single-slice number reproduced exactly (94.409 N), and it matches the 1/4" sweep at 8 mm (94.51 N, 0.1%).
- **Converged:** 13, 13 and 14 adaptive passes, all under the 15-pass limit. Counted from the `*_P<n>.adp` files in each project's results folder (pyaedt has no simple convergence call here).
- **Force per inch rises 69% going from 1" to 3" of depth.** This is real in the model, not an artifact of the build. Mesh noise is about 1%.
- **Hypothesis (unverified): end leakage.** Flux that leaves a magnet's end faces and returns through the base without crossing the gap scales with the end area, not with depth, so it is a bigger share of a 1" yoke than of a 3" one. That would make long yokes more efficient per inch. An ideal 1-D estimate (no leakage) is roughly 600 N per inch at 8 mm, far above both numbers, so leakage is large. Fringing at the gap works the other way, which is why the sign was not obvious.
- **Why it matters:** if it holds, force per inch from the 1" test yoke does not carry over to the 9" yoke; per-inch force could be about 1.7x or more. Check the trend before relying on it: solve extrusions at 1, 2, 3, 6 and 9 inches (`--extrude-in`, one depth per run) and see whether per-inch force levels off.
- **A note on the old guess:** an earlier version of this doc said the ratio should be at or below 1 because fringing adds force. That ignored end leakage and was too confident.
- The track peak |B| at 3" tells whether the 1/4" track starts to saturate as the yoke lengthens. That is the main reason to run this before the 9" case.
- Do not expect lamination or eddy information. A magnetostatic run cannot show it.

## Changes this depends on (in `scripts/yoke_model.py`, uncommitted)
- `build(..., slices=None, lam_sf=None)`: y-slices list and optional homogenized lamination. Default is one 1" slice, which should reproduce the earlier single-yoke results (not re-verified after the refactor).
- `stack_slices`, `lamination_sheets`, `make_lamination_material`, `solve_point(m, gap_mm)` (returns Fz and peak track |B|).
- `TRACK` default is now 12" × 36" × 1/4", and `build()` takes a `track` tuple.
- `magnet` option (`legacy` / `linear` / `arnold`), default `legacy`. This script passes `linear`.

## Untested assumptions and risks
1. **Run only at one gap (8 mm), 0 A, one steel and magnet model.** The depth trend at other gaps and with current is unknown.
2. **Touching slices** share faces; the extrusion comparison shows this causes no measurable difference.
3. **Rectangular coil** built with box minus box. At 0 A it is inert, but it enlarges the mesh as the depth grows. Coil behavior under current in the stack case is untested.
4. **Peak track |B|** comes from a best-effort field-calculator call (`Mag_B`, maximum over the `Track` volume). It returns NaN if the call fails. It is a local peak, not a section average.
5. **Student limits:** 4 cores, serial solves, and an unknown mesh cap for Maxwell. A 9" case may hit it.
6. **Material:** `steel_1010` is a library stand-in. The project's `1018 CS` / `1020 CS` curves have unknown provenance, and A36 has no B-H data in Maxwell's library.

## To run
Close AEDT first (Student allows one session; `Get-Process ansys* | Stop-Process -Force`). The script refuses to start if an `ansysedt*` process is running. Two cases take roughly 2 to 4 minutes in total.

## Related
- `scripts/README.md`: what every script and CSV does.
- `scripts/yoke_laminated.py`: the laminated 1" yoke (also written, not run).
- Earlier results: `sim/magnet_crosscheck.csv`, `sim/track_thickness_sweep.csv`.

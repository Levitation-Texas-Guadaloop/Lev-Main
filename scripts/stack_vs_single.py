"""Single 1" yoke vs. a stack of 1" slices (the "pseudo-laminated" 3" yoke), fixed gap, 1/4" track.

The stack is built the way the real 9" yoke is: n 1-inch steel slices side by side along the rail (y), not one 3"
extrusion. One magnet bar and ONE coil per leg span all slices, so the coil wraps the whole leg and is not
duplicated per slice (see yoke_model.build). Optional --glue-mm puts an air gap between slices to stand in for the
epoxy line. With --glue-mm 0 the slices touch; magnetically that is the same as an extrusion, because flux runs
inside each slice and never crosses a joint, so any difference to the single yoke is end-effect (fringing) only.

Metrics: Fz, Fz per inch of depth, and the ratio Fz / (steel inches * Fz(1)). The first run gave 1.69 for 3 inches;
a solid 3-inch extrusion (--extrude-in 3) matched it, so the stack build is not the cause. Hypothesis: end leakage
around the magnets is a larger share of a short yoke (see HANDOFF_stack_vs_single.md).

Run:  .venv\\Scripts\\python scripts\\stack_vs_single.py [--gap MM] [--glue-mm MM] [--slices 1 3] [--extrude-in N] [--cores N]
Close any open AEDT window first (Student license = one session). One AEDT session per case.
Writes sim/stack_vs_single.csv. Magnet: linear N52. Steel: yoke_model.STEEL. Track 12" x 36" x 1/4".
"""
import argparse
import csv
import math
import os

import psutil

import yoke_model as ym

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sim")
TRACK = (12 * ym.IN, 36 * ym.IN, 0.25 * ym.IN)


def run_case(n, gap_mm, glue_mm, cores):
    project = os.path.abspath(os.path.join(ROOT, f"stack_{n}.aedt"))
    m = ym.build(project, cores=cores, magnet="linear", track=TRACK, slices=ym.stack_slices(n, glue_mm=glue_mm))
    try:
        fz, b = ym.solve_point(m, gap_mm)
        m.save_project()
    finally:
        m.release_desktop(close_projects=True, close_desktop=True)
    depth_in = (n * ym.IN + (n - 1) * glue_mm) / ym.IN
    return {"build": "stack", "n_slices": n, "steel_in": float(n), "depth_in": round(depth_in, 3), "glue_mm": glue_mm,
            "gap_mm": gap_mm, "Fz_N": round(fz, 3), "Fz_per_in_N": round(fz / n, 3), "B_track_peak_T": round(b, 3)}


def run_extrusion(depth_in, gap_mm, cores):
    """One solid steel body `depth_in` deep (no slices): the diagnostic for the stack result."""
    project = os.path.abspath(os.path.join(ROOT, f"stack_ext{depth_in:g}.aedt"))
    half = depth_in * ym.IN / 2
    m = ym.build(project, cores=cores, magnet="linear", track=TRACK, slices=[(-half, half)])
    try:
        fz, b = ym.solve_point(m, gap_mm)
        m.save_project()
    finally:
        m.release_desktop(close_projects=True, close_desktop=True)
    return {"build": "extrusion", "n_slices": 1, "steel_in": float(depth_in), "depth_in": float(depth_in),
            "glue_mm": 0.0, "gap_mm": gap_mm, "Fz_N": round(fz, 3), "Fz_per_in_N": round(fz / depth_in, 3),
            "B_track_peak_T": round(b, 3)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--gap", type=float, default=8.0)
    ap.add_argument("--glue-mm", type=float, default=0.0, help="air gap between slices (epoxy line), default 0")
    ap.add_argument("--slices", type=int, nargs="+", default=[1, 3])
    ap.add_argument("--extrude-in", type=float, help="also solve one solid steel body this many inches deep "
                    "(diagnostic: compare with the stack of the same depth)")
    ap.add_argument("--cores", type=int, default=4, help="Student license caps at 4")
    a = ap.parse_args()

    running = [p for p in psutil.process_iter(["name", "pid"]) if (p.info["name"] or "").lower().startswith("ansysedt")]
    if running:
        raise SystemExit("AEDT is already running (PID " + ", ".join(str(p.info["pid"]) for p in running) +
                         "). Close it first: Get-Process ansys* | Stop-Process -Force")

    os.makedirs(ROOT, exist_ok=True)
    rows = []
    for n in a.slices:
        r = run_case(n, a.gap, a.glue_mm, a.cores)
        rows.append(r)
        print(f"n={n}  depth={r['depth_in']} in  Fz={r['Fz_N']} N  per inch={r['Fz_per_in_N']} N  "
              f"B_track_peak={r['B_track_peak_T']} T", flush=True)
    if a.extrude_in:
        r = run_extrusion(a.extrude_in, a.gap, a.cores)
        rows.append(r)
        print(f"extrusion  depth={r['depth_in']} in  Fz={r['Fz_N']} N  per inch={r['Fz_per_in_N']} N  "
              f"B_track_peak={r['B_track_peak_T']} T", flush=True)
    ref = next((r for r in rows if r["build"] == "stack" and r["n_slices"] == 1), None)
    for r in rows:
        r["ratio_vs_n_x_single"] = round(r["Fz_N"] / (r["steel_in"] * ref["Fz_N"]), 4) if ref else math.nan
    out = os.path.join(ROOT, "stack_vs_single.csv")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("wrote", out)

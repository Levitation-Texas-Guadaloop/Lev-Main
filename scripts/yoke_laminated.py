"""Laminated version of the 1" yoke: same geometry, magnets and coil as yoke_model, parametric lamination thickness.

How Ansys models laminations (Maxwell help, "Lamination Modeling"): as a homogenized material, not as individual
sheets. A material gets a stacking factor SF (0..1) and a stacking direction (V(1)/V(2)/V(3) = x/y/z in Cartesian);
magnetostatic, eddy-current and transient solvers honour it. SF scales the steel's effective cross-section, so the
real steel flux density is B_plotted / SF (plots show the average over steel and insulation). Sheet *thickness*
only enters through SF = t / (t + coating) and, in the eddy/transient solvers, the eddy paths. Core-loss
coefficients must be rescaled by the user (Kh/SF, Kc/SF, Ke/sqrt(SF)); not needed here (force only).

Modes
  homogenized  yoke steel (base + caps) is a clone of the library steel with Stacking Type = Lamination,
               SF = t / (t + coat), direction V(2) = y (sheets stacked along the rail). Cheap, the Ansys-native way.
  explicit     real sheets: n = round((depth + coat) / (t + coat)) separate steel bodies, the gap stretched so the stack
               fills the 1" depth exactly, air between sheets. Expensive (mesh) and meant to validate the homogenized
               result at a coarse thickness, e.g. --t-mm 3.2 gives 7 sheets. Guarded by --max-sheets.
The track is plain solid steel in both modes (the laminating doc keeps it unlaminated). Magnets and coil are unchanged.

Run:  .venv\\Scripts\\python scripts\\yoke_laminated.py [--mode homogenized|explicit] [--t-mm 1.2192] [--coat-mm 0.1]
          [--gap 8] [--plan-only] [--no-solid-ref] [--max-sheets 60] [--cores N]
--plan-only prints the sheet count, gap and SF and exits without starting AEDT.
Close any open AEDT window first (Student license = one session). Writes sim/yoke_laminated.csv, including a solid
(unlaminated) reference row unless --no-solid-ref. Magnet: linear N52. Track 12" x 36" x 1/4".
"""
import argparse
import csv
import math
import os

import psutil

import yoke_model as ym

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sim")
TRACK = (12 * ym.IN, 36 * ym.IN, 0.25 * ym.IN)


def plan(mode, t_mm, coat_mm):
    """Return dict(slices, lam_sf, n, gap_mm, sf) for the chosen mode."""
    depth = ym.DEPTH
    if mode == "homogenized":
        sf = t_mm / (t_mm + coat_mm)
        return {"slices": None, "lam_sf": sf, "n": round(depth / (t_mm + coat_mm)), "gap_mm": coat_mm, "sf": sf}
    slices, n, gap, sf = ym.lamination_sheets(depth, t_mm, coat_mm)
    return {"slices": slices, "lam_sf": None, "n": n, "gap_mm": gap, "sf": sf}


def solve(label, p, gap_mm, cores):
    project = os.path.abspath(os.path.join(ROOT, f"lam_{label}.aedt"))
    m = ym.build(project, cores=cores, magnet="linear", track=TRACK, slices=p["slices"], lam_sf=p["lam_sf"])
    try:
        fz, b = ym.solve_point(m, gap_mm)
        m.save_project()
    finally:
        m.release_desktop(close_projects=True, close_desktop=True)
    return fz, b


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["homogenized", "explicit"], default="homogenized")
    ap.add_argument("--t-mm", type=float, default=1.2192,
                    help="lamination (sheet) thickness; default 0.048 in, the SendCutSend A1008 sheet in gen_lamination_dxfs.py")
    ap.add_argument("--coat-mm", type=float, default=0.1,
                    help="insulation / epoxy line between sheets (assumed 0.1 mm; measure the real bond line)")
    ap.add_argument("--gap", type=float, default=8.0, help="GapHeight in mm")
    ap.add_argument("--plan-only", action="store_true", help="print the lamination plan and exit (no AEDT)")
    ap.add_argument("--no-solid-ref", action="store_true", help="skip the unlaminated reference solve")
    ap.add_argument("--max-sheets", type=int, default=60, help="refuse explicit mode above this sheet count")
    ap.add_argument("--cores", type=int, default=4, help="Student license caps at 4")
    a = ap.parse_args()

    p = plan(a.mode, a.t_mm, a.coat_mm)
    print(f"mode={a.mode}  t={a.t_mm} mm  coat={a.coat_mm} mm  ->  sheets={p['n']}  "
          f"gap between sheets={p['gap_mm']:.4f} mm  stacking factor={p['sf']:.4f}")
    if a.mode == "explicit" and p["n"] > a.max_sheets:
        raise SystemExit(f"{p['n']} sheets exceeds --max-sheets {a.max_sheets}: explicit sheets this thin make an "
                         "enormous mesh. Use --mode homogenized, a thicker --t-mm, or raise --max-sheets.")
    if a.plan_only:
        raise SystemExit(0)

    running = [q for q in psutil.process_iter(["name", "pid"]) if (q.info["name"] or "").lower().startswith("ansysedt")]
    if running:
        raise SystemExit("AEDT is already running (PID " + ", ".join(str(q.info["pid"]) for q in running) +
                         "). Close it first: Get-Process ansys* | Stop-Process -Force")

    os.makedirs(ROOT, exist_ok=True)
    rows = []
    if not a.no_solid_ref:
        fz, b = solve("solid", {"slices": None, "lam_sf": None}, a.gap, a.cores)
        rows.append({"case": "solid", "mode": "-", "t_mm": "", "coat_mm": "", "n_sheets": 1, "sf": 1.0,
                     "gap_mm": a.gap, "Fz_N": round(fz, 3), "B_track_peak_T": round(b, 3)})
        print(f"solid reference  Fz={fz:.3f} N  B_track_peak={b:.3f} T", flush=True)
    fz, b = solve(a.mode, p, a.gap, a.cores)
    rows.append({"case": "laminated", "mode": a.mode, "t_mm": a.t_mm, "coat_mm": a.coat_mm, "n_sheets": p["n"],
                 "sf": round(p["sf"], 4), "gap_mm": a.gap, "Fz_N": round(fz, 3), "B_track_peak_T": round(b, 3)})
    print(f"{a.mode}  Fz={fz:.3f} N  B_track_peak={b:.3f} T", flush=True)
    ref = rows[0]["Fz_N"] if not a.no_solid_ref else math.nan
    for r in rows:
        r["vs_solid_pct"] = round((r["Fz_N"] / ref - 1) * 100, 2) if not math.isnan(ref) else ""
    out = os.path.join(ROOT, "yoke_laminated.csv")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("wrote", out)

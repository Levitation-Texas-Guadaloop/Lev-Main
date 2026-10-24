"""Track thickness comparison: 1/4" vs 3/8" steel track at 4, 8 and 12 mm gaps (1" yoke, 0 A, no roll).

Track: 12" wide (x, across the legs) x 36" long (y, along the rail), thickness swept. Magnet: "linear" N52
(Br 1.45 T, mu_r 1.04). Steel: yoke_model.STEEL (steel_1010) for yoke and track.

Run:  .venv\\Scripts\\python scripts\\track_thickness_sweep.py [--cores N]
Close any open AEDT window first (Student license = one session). One AEDT session per thickness, one solve
per gap. Writes sim/track_thickness_sweep.csv (Fz plus the track's peak |B|, NaN if the field read fails).
"""
import argparse
import csv
import math
import os

import psutil

import yoke_model as ym

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sim")
THICKNESSES_IN = [0.25, 0.375, 0.5]
GAPS_MM = [4, 8, 12]
TRACK_X_IN, TRACK_Y_IN = 12, 36
MAGNET = "linear"


def run_thickness(t_in, cores):
    project = os.path.abspath(os.path.join(ROOT, f"track_t{int(t_in * 1000):04d}.aedt"))
    track = (TRACK_X_IN * ym.IN, TRACK_Y_IN * ym.IN, t_in * ym.IN)
    m = ym.build(project, cores=cores, magnet=MAGNET, track=track)
    rows = []
    try:
        for gap in GAPS_MM:
            m["GapHeight"] = f"{gap}mm"
            if not m.analyze_setup("Setup1"):
                msgs = list(m.odesktop.GetMessages(m.project_name, m.design_name, 2))
                raise RuntimeError(f"solve failed at t={t_in} in, gap={gap} mm: {msgs}")
            d = m.post.get_solution_data(["YokeForce.Force_z"], setup_sweep_name="Setup1 : LastAdaptive")
            fz = float(d.get_expression_data("YokeForce.Force_z")[1][0])
            try:
                b_peak = float(m.post.get_scalar_field_value("Mag_B", scalar_function="Maximum",
                                                             solution="Setup1 : LastAdaptive",
                                                             object_name="Track", object_type="volume"))
            except Exception as exc:   # field read is best effort; the force is the deliverable
                print(f"  (B read failed: {exc})")
                b_peak = math.nan
            rows.append({"magnet": MAGNET, "steel": ym.STEEL, "track_x_in": TRACK_X_IN, "track_y_in": TRACK_Y_IN,
                         "track_t_in": t_in, "gap_mm": gap, "mmf_At": 0, "roll_deg": 0,
                         "Fz_N": round(fz, 3), "B_track_peak_T": round(b_peak, 3)})
            print(f"t={t_in} in  gap={gap:2d} mm  Fz={fz:8.3f} N  B_track_peak={b_peak:.3f} T", flush=True)
        m.save_project()
    finally:
        m.release_desktop(close_projects=True, close_desktop=True)
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cores", type=int, default=4, help="Student license caps at 4")
    ap.add_argument("--thicknesses", type=float, nargs="+", default=THICKNESSES_IN,
                    help="track thicknesses in inches to solve; rows for other thicknesses already in the CSV are kept")
    a = ap.parse_args()

    running = [p for p in psutil.process_iter(["name", "pid"]) if (p.info["name"] or "").lower().startswith("ansysedt")]
    if running:
        raise SystemExit("AEDT is already running (PID " + ", ".join(str(p.info["pid"]) for p in running) +
                         "). Close it first: Get-Process ansys* | Stop-Process -Force")

    os.makedirs(ROOT, exist_ok=True)
    out = os.path.join(ROOT, "track_thickness_sweep.csv")
    kept = []                                           # rows from earlier runs at thicknesses we are not re-solving
    if os.path.isfile(out):
        with open(out, newline="") as f:
            kept = [r for r in csv.DictReader(f) if not any(abs(float(r["track_t_in"]) - t) < 1e-9 for t in a.thicknesses)]
    new_rows = []
    for t in a.thicknesses:
        new_rows += run_thickness(t, a.cores)
        merged = sorted(kept + new_rows, key=lambda r: (float(r["track_t_in"]), float(r["gap_mm"])))
        with open(out, "w", newline="") as f:          # rewrite after each thickness so a crash keeps partial data
            w = csv.DictWriter(f, fieldnames=list(new_rows[0].keys()))
            w.writeheader()
            w.writerows(merged)
    print("wrote", out)

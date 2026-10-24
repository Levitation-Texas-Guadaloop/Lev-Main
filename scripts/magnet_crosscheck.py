"""Cross-check the magnet material model: same yoke, same gap, three magnet definitions.

legacy  Br 1.284 T (mu_r 1.07, Hc 955 kA/m), the values the script used so far
linear  Br 1.45 T, mu_r 1.04, Hc derived (custom linear N52)
arnold  library Arnold_Magnetics_N52_20C nonlinear demag table

Expectation: linear vs arnold agree to well under 1% (the real curve is straight to H = -700 kA/m at 20 C);
legacy comes out roughly (1.45 / 1.284)^2 = 1.28x weaker.

Run:  .venv\\Scripts\\python scripts\\magnet_crosscheck.py [--gap MM] [--cores N]
Close any open AEDT window first (Student license = one session). Three solves, one fresh AEDT session each,
about 1 minute apiece. Writes sim/magnet_crosscheck.csv.
"""
import argparse
import csv
import os

import psutil

from yoke_model import build

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sim")
MAGNETS = ["linear", "arnold", "legacy"]


def solve_one(magnet, gap_mm, cores):
    project = os.path.abspath(os.path.join(ROOT, f"xc_{magnet}.aedt"))
    m = build(project, cores=cores, magnet=magnet)
    try:
        m["GapHeight"] = f"{gap_mm}mm"
        if not m.analyze_setup("Setup1"):
            msgs = list(m.odesktop.GetMessages(m.project_name, m.design_name, 2))
            raise RuntimeError(f"solve failed for {magnet}: {msgs}")
        d = m.post.get_solution_data(["YokeForce.Force_z"], setup_sweep_name="Setup1 : LastAdaptive")
        fz = float(d.get_expression_data("YokeForce.Force_z")[1][0])
        m.save_project()
        return fz
    finally:
        m.release_desktop(close_projects=True, close_desktop=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--gap", type=float, default=3.0, help="GapHeight in mm (default 3, the design point)")
    ap.add_argument("--cores", type=int, default=4, help="Student license caps at 4")
    a = ap.parse_args()

    running = [p for p in psutil.process_iter(["name", "pid"]) if (p.info["name"] or "").lower().startswith("ansysedt")]
    if running:
        raise SystemExit("AEDT is already running (PID " + ", ".join(str(p.info["pid"]) for p in running) +
                         "). Close it first: Get-Process ansys* | Stop-Process -Force")

    os.makedirs(ROOT, exist_ok=True)
    rows = []
    for magnet in MAGNETS:
        fz = solve_one(magnet, a.gap, a.cores)
        rows.append({"magnet": magnet, "gap_mm": a.gap, "Fz_N": round(fz, 3)})
        print(f"{magnet:7s} gap {a.gap} mm  Fz = {fz:9.3f} N", flush=True)

    ref = next(r["Fz_N"] for r in rows if r["magnet"] == "arnold")
    for r in rows:
        r["vs_arnold_pct"] = round((r["Fz_N"] / ref - 1) * 100, 2)
    out = os.path.join(ROOT, "magnet_crosscheck.csv")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["magnet", "gap_mm", "Fz_N", "vs_arnold_pct"])
        w.writeheader()
        w.writerows(rows)
    print("\n".join(f"{r['magnet']:7s} {r['Fz_N']:9.3f} N  ({r['vs_arnold_pct']:+.2f}% vs arnold)" for r in rows))
    print("wrote", out)

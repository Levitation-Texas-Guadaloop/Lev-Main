"""
Tiny stdlib JSON API for the web UI. Reuses the real models (reluctance_model, coil_model,
power_model) so the browser UI and the matplotlib UIs can never drift apart.

    guadaloop_lev_control/.venv/bin/python3 Magnetic-Circuit-Model/web/api_server.py [port]

POST /api/model  -> everything both tabs need, in one round trip (see `compute`).
GET  /api/health -> {"ok": true}
"""

import json
import math
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import coil_model  # noqa: E402
import power_model  # noqa: E402
from reluctance_model import YokeGeometry, equilibrium_gap_mm, total_force  # noqa: E402

DEFAULTS = {
    "N_turns": 250.0,
    "ydepth_in": 6.0,
    "mass_kg": 226.0,
    "currents": [-10, -9, -8, 0, 8, 9, 10],
    "gap_min_mm": 5.0,
    "gap_max_mm": 10.0,
    "s0_mm": 6.0,
    "r_coil_ohm": None,  # None == auto from coil_model(D, N)
    "ceiling_w": 1500.0,
}
N_FORCE_PTS = 300
N_SWEEP_PTS = 60


def _clean(x):
    """JSON-safe: NaN/inf -> None, numpy -> python."""
    if isinstance(x, dict):
        return {k: _clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    if isinstance(x, np.ndarray):
        return _clean(x.tolist())
    if isinstance(x, (np.floating, float)):
        return None if not math.isfinite(x) else float(x)
    if isinstance(x, np.integer):
        return int(x)
    return x


def _validate(p):
    q = {**DEFAULTS, **{k: v for k, v in p.items() if k in DEFAULTS}}
    for k in ("N_turns", "ydepth_in", "mass_kg", "gap_min_mm", "gap_max_mm", "ceiling_w"):
        q[k] = float(q[k])
    if not (q["N_turns"] > 0 and q["ydepth_in"] > 0 and q["mass_kg"] > 0):
        raise ValueError("turns, depth and mass must be > 0")
    if not (q["gap_max_mm"] > q["gap_min_mm"] > 0):
        raise ValueError("gap range needs max > min > 0")
    if q["ceiling_w"] <= 0:
        raise ValueError("power ceiling must be > 0")
    q["currents"] = [float(c) for c in q["currents"]] or [0.0]
    q["s0_mm"] = None if q["s0_mm"] in (None, "") else float(q["s0_mm"])
    q["r_coil_ohm"] = None if q["r_coil_ohm"] in (None, "") else float(q["r_coil_ohm"])
    if q["r_coil_ohm"] is not None and q["r_coil_ohm"] <= 0:
        raise ValueError("R coil must be > 0")
    return q


def compute(params):
    q = _validate(params)
    geom = YokeGeometry(**{**YokeGeometry().__dict__, "N_turns": q["N_turns"],
                           "ydepth_in": q["ydepth_in"], "mass_kg": q["mass_kg"]})
    auto = q["r_coil_ohm"] is None
    R = power_model.coil_resistance(geom, q["r_coil_ohm"])
    out = {"params": q, "r_auto": auto, "R_ohm": R, "weight_n": geom.mass_kg * 9.8}

    # coil-resistance derivation breakdown (always the auto/geometry value)
    c = coil_model
    r_bar = c.mean_radial_offset_in(c.WINDING_HEIGHT_IN, c.WIRE_DIAM_IN, geom.N_turns)
    out["coil"] = {
        "R_auto_ohm": c.resistance(D=geom.ydepth_in, N=geom.N_turns),
        "mlt_in": c.mean_length_per_turn_in(geom.ydepth_in, c.LEG_WIDTH_IN, c.BOBBIN_WALL_IN,
                                            c.WINDING_HEIGHT_IN, geom.N_turns, c.WIRE_DIAM_IN,
                                            c.K_BULGE_DEFAULT),
        "r_bar_in": r_bar,
        "layers": len(c._layer_turn_counts(c.WINDING_HEIGHT_IN, c.WIRE_DIAM_IN, geom.N_turns)),
        "turns_per_layer": max(int(c.WINDING_HEIGHT_IN // c.WIRE_DIAM_IN), 1),
        "k": c.K_BULGE_DEFAULT,
        "c": c.C_SCALE_DEFAULT,
    }

    # force curves
    gap_mm = np.linspace(q["gap_min_mm"], q["gap_max_mm"], N_FORCE_PTS)
    out["force"] = {
        "gap_mm": gap_mm,
        "curves": [{"i_amp": i, "force_n": total_force(gap_mm * 1e-3, i, geom)} for i in q["currents"]],
    }

    try:
        g_eq = equilibrium_gap_mm(geom, 0.0, (0.05, 200.0))  # wide: independent of the plot range
    except Exception:
        g_eq = None
    out["g_eq_mm"] = g_eq

    # budget at the ceiling
    out["budget"] = power_model.power_budget(geom, q["ceiling_w"], q["r_coil_ohm"])

    # release at s0
    s0 = q["s0_mm"]
    rel = {"status": "unset", "message": "enter s0"}
    if s0 is not None:
        if s0 <= 0:
            rel = {"status": "error", "message": "s0 must be > 0"}
        elif g_eq is not None and s0 >= g_eq:
            rel = {"status": "error", "message": f"s0 must be < eq. gap ({g_eq:.3f} mm)"}
        else:
            try:
                r = power_model.release_current_power(geom, s0 * 1e-3, q["r_coil_ohm"])
                b = out["budget"]
                r.update(status="ok", s0_mm=s0, headroom_a=b["i_coil_amp"] - r["i_release_amp"],
                         covered=b["i_coil_amp"] >= r["i_release_amp"])
                rel = r
            except Exception as e:  # noqa: BLE001
                rel = {"status": "error", "message": str(e)}
    out["release"] = rel

    # power vs s0 sweep + smallest covered s0
    sweep = {"s_mm": [], "p_total_w": [], "s_min_mm": None, "all_covered": False}
    if g_eq is not None:
        s = np.linspace(0.3, g_eq * 0.995, N_SWEEP_PTS)
        p = np.array([power_model.release_current_power(geom, v * 1e-3, q["r_coil_ohm"])
                      ["total"]["peak_power_w"] for v in s])
        ok = p <= q["ceiling_w"]
        sweep.update(s_mm=s, p_total_w=p, all_covered=bool(ok.all()))
        if ok.any() and not ok.all():
            k = int(np.argmax(ok))
            sweep["s_min_mm"] = float(np.interp(q["ceiling_w"], [p[k], p[k - 1]], [s[k], s[k - 1]]))
    out["sweep"] = sweep
    return _clean(out)


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in (("Access-Control-Allow-Origin", "*"), ("Access-Control-Allow-Headers", "Content-Type"),
                     ("Access-Control-Allow-Methods", "GET,POST,OPTIONS")):
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/health":
            return self._send(200, {"ok": True, "defaults": DEFAULTS})
        self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/api/model":
            return self._send(404, {"error": "not found"})
        try:
            n = int(self.headers.get("Content-Length", 0))
            self._send(200, compute(json.loads(self.rfile.read(n) or b"{}")))
        except (ValueError, TypeError, KeyError) as e:
            self._send(400, {"error": str(e)})
        except Exception as e:  # noqa: BLE001
            self._send(500, {"error": f"{type(e).__name__}: {e}"})

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    print(f"HEMS API on http://127.0.0.1:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()

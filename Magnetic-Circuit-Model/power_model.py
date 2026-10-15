"""
Electrical power helper for the HEMS yoke: coil current -> power / voltage / supply current,
for one yoke and for the whole pod (N_YOKES yokes on the battery).

Kept out of `reluctance_model.py` (a pure Maple transcription) because none of this has a
worksheet origin. Two directions:

- forward:  `release_current_power(geom, gap_m)`  -- release current at gap s0 -> power/V/I
- inverse:  `power_budget(geom, power_ceiling_w)` -- battery power ceiling -> max coil
  current and the 2-coil series/parallel V/I that stays under it

Wiring model (same as the interactive plot): each of a yoke's 2 leg coils must carry
`i_coil` (the reluctance model uses one shared `i`), so dissipation is `2 * i_coil^2 * R`
per yoke whatever the wiring. Only what the supply sees differs:

- series:   supply current = i_coil,      supply voltage = 2 * i_coil * R
- parallel: supply current = 2 * i_coil,  supply voltage = i_coil * R

Whole-pod figures multiply the per-yoke series/parallel numbers by N_YOKES (yokes assumed
wired the same way and fed in parallel from the battery bus, so for the *total* current
that's N_YOKES x the per-yoke supply current at the same voltage).

R_coil: auto-derived from yoke depth/turns via `coil_model.resistance` unless a manual
`coil_resistance_ohm` is passed.
"""

import math

import coil_model
from reluctance_model import YokeGeometry, required_release_current_amp

N_YOKES = 4


def coil_resistance(geom: YokeGeometry, coil_resistance_ohm=None):
    """Per-leg coil resistance [ohm]: manual override if given, else coil_model(D, N)."""
    if coil_resistance_ohm is not None:
        return coil_resistance_ohm
    return coil_model.resistance(D=geom.ydepth_in, N=geom.N_turns)


def power_for_coil_current(i_coil_amp, R_ohm, n_yokes=N_YOKES):
    """Power and series/parallel supply V/I for `i_coil_amp` in every leg coil."""
    per_yoke = {
        "peak_power_w": 2.0 * i_coil_amp**2 * R_ohm,
        "series": {"voltage_v": 2.0 * i_coil_amp * R_ohm, "current_a": i_coil_amp},
        "parallel": {"voltage_v": i_coil_amp * R_ohm, "current_a": 2.0 * i_coil_amp},
    }
    total = {
        "peak_power_w": n_yokes * per_yoke["peak_power_w"],
        "series": {
            "voltage_v": per_yoke["series"]["voltage_v"],
            "current_a": n_yokes * per_yoke["series"]["current_a"],
        },
        "parallel": {
            "voltage_v": per_yoke["parallel"]["voltage_v"],
            "current_a": n_yokes * per_yoke["parallel"]["current_a"],
        },
    }
    return {
        "i_coil_amp": i_coil_amp,
        "R_coil_ohm": R_ohm,
        "n_yokes": n_yokes,
        "per_yoke": per_yoke,
        "total": total,
    }


def release_current_power(geom: YokeGeometry, gap_m, coil_resistance_ohm=None, n_yokes=N_YOKES):
    """Forward: power/V/I (per yoke and total) to drive the release current at `gap_m`."""
    R = coil_resistance(geom, coil_resistance_ohm)
    out = power_for_coil_current(required_release_current_amp(geom, gap_m), R, n_yokes)
    out["i_release_amp"] = out["i_coil_amp"]
    return out


def power_budget(geom: YokeGeometry, power_ceiling_w, coil_resistance_ohm=None,
                 n_yokes=N_YOKES, gap_m=None):
    """
    Inverse: given a total (all-yokes) peak power ceiling, back out the max coil current
    `i = sqrt(P / (n_yokes * 2 * R))` and the series/parallel V/I that implies, per yoke
    and total. If `gap_m` is given, also reports the release current needed there and
    whether the ceiling covers it (`headroom_a` > 0 means yes).
    """
    if power_ceiling_w <= 0:
        raise ValueError("power ceiling must be > 0")
    R = coil_resistance(geom, coil_resistance_ohm)
    i_max = math.sqrt(power_ceiling_w / (n_yokes * 2.0 * R))
    out = power_for_coil_current(i_max, R, n_yokes)
    out["power_ceiling_w"] = power_ceiling_w
    out["max_ampere_turns_per_coil"] = i_max * geom.N_turns
    if gap_m is not None:
        i_need = required_release_current_amp(geom, gap_m)
        out["i_release_amp"] = i_need
        out["headroom_a"] = i_max - i_need
        out["covers_release"] = i_max >= i_need
    return out


def format_result(res):
    """Plain-text table of a `power_for_coil_current`-shaped result (same layout as the UI)."""
    lines = [f"R_coil = {res['R_coil_ohm']:.3f} ohm/leg, coil current = {res['i_coil_amp']:.3f} A"]
    for key, title in (("per_yoke", "per yoke"), ("total", f"TOTAL (x{res['n_yokes']} yokes)")):
        d = res[key]
        lines.append(f"  {title}: peak power {d['peak_power_w']:9.1f} W")
        lines.append(f"    2 coils SERIES:    V = {d['series']['voltage_v']:7.2f} V"
                     f"   I(supply) = {d['series']['current_a']:7.3f} A")
        lines.append(f"    2 coils PARALLEL:  V = {d['parallel']['voltage_v']:7.2f} V"
                     f"   I(supply) = {d['parallel']['current_a']:7.3f} A")
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="HEMS power helper")
    ap.add_argument("--ceiling-w", type=float, help="total peak power ceiling [W]; back-calculates V/I")
    ap.add_argument("--s0-mm", type=float, help="starting gap [mm]; forward release-current power, "
                    "and release-vs-ceiling check when --ceiling-w is given")
    ap.add_argument("--depth-in", type=float, default=YokeGeometry().ydepth_in)
    ap.add_argument("--turns", type=float, default=YokeGeometry().N_turns)
    ap.add_argument("--mass-kg", type=float, default=226.0)
    ap.add_argument("--r-coil", type=float, default=None, help="manual R per leg [ohm]; default auto")
    a = ap.parse_args()

    g = YokeGeometry(ydepth_in=a.depth_in, N_turns=a.turns, mass_kg=a.mass_kg)
    gap = a.s0_mm * 1e-3 if a.s0_mm is not None else None
    if a.ceiling_w is not None:
        r = power_budget(g, a.ceiling_w, a.r_coil, gap_m=gap)
        print(f"Ceiling {a.ceiling_w:g} W total -> max coil current {r['i_coil_amp']:.3f} A "
              f"({r['max_ampere_turns_per_coil']:.0f} A-turns/coil)")
        print(format_result(r))
        if gap is not None:
            print(f"Release current @ s0={a.s0_mm:g} mm: {r['i_release_amp']:.3f} A -> "
                  f"{'OK' if r['covers_release'] else 'NOT COVERED'} (headroom {r['headroom_a']:+.3f} A)")
    elif gap is not None:
        r = release_current_power(g, gap, a.r_coil)
        print(f"Release current @ s0={a.s0_mm:g} mm: {r['i_release_amp']:.3f} A")
        print(format_result(r))
    else:
        ap.error("give --ceiling-w and/or --s0-mm")

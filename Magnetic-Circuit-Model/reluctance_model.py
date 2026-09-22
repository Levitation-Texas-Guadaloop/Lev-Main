"""
Python transcription of `full_hems.mw` (Maple 2023.2) -- the HEMS yoke
reluctance-network model.

Source worksheet: OneDrive/Levitation 2024-2025/Code/hems_models/full_hems.mw
Physics background: docs/rfcs/knowledge/Maglev - PM Bias and Force Linearization.md (S4b)

Cross-section modeled (see the user-supplied yoke diagram / Diagram_1 in the PM
Bias doc): a U-shaped 1018 steel yoke, one 1"-square NdFeB PM per leg, a 5"x1.5"
steel base, an N-turn coil wound on the legs, with flux closing through a steel
"track" (rail) across the working air gap. The cross-section is 1" thick and
extrudes `ydepth` inches deep -- `ydepth > 1` models several 1"-deep cores
stacked side by side to support a heavier pod.

This is a line-for-line transcription of the worksheet's symbolic derivation
(reluctance network -> MMF -> flux -> co-energy force). Every literal length,
material property, and turns count in the .mw file is now a field of
`YokeGeometry` instead of a hard-coded number, and the symbolic force
expression is built once with sympy (mirroring Maple's `diff`/`unapply`) and
then lambdified for fast repeated numeric evaluation.

No physics has been changed or corrected -- including known approximations
(no eddy-current or lamination losses; the reluctance network neglects flux
leakage). One inherited quirk worth flagging: the worksheet's `Rel[leg]` uses
a 1" steel leg length, while the diagram shows only 0.5" of 1018 steel per leg
above the base (the other 1" is the PM). That mismatch is preserved as-is
since verifying/fixing the model is explicitly out of scope for this pass.
"""

from dataclasses import dataclass

import numpy as np
import sympy as sp
from scipy.optimize import brentq

IN_TO_M = 0.0254  # Maple: m := (25.4*a)/1000  ==  len(a) is `a` inches, in meters
OERSTED_TO_A_PER_M = 79.577471546  # Maple literal in `PM := ...`: 1 Oe = 1000/(4*pi) A/m


def length_m(inches):
    """Maple `len(a)` -- inches to meters."""
    return inches * IN_TO_M


@dataclass
class YokeGeometry:
    """Every literal from the .mw worksheet, now a knob. Defaults == the .mw file."""

    ydepth_in: float = 6.0  # Maple `ydepth` -- stacked extrusion depth [in]
    pole_width_in: float = 1.0  # leg cross-section width [in] (1" in the diagram)
    pm_len_in: float = 1.0  # PM length per leg [in]                 (Rel[mag]: len(1))
    leg_len_in: float = 1.0  # steel leg length per leg [in]         (Rel[leg]: len(1);
    #   diagram shows 0.5" of 1018 per leg -- unreconciled, kept as the .mw had it)
    base_len_in: float = 5.0  # base length [in]                     (Rel[base]: len(5))
    base_height_in: float = 1.5  # base cross-section height [in]    (Rel[base]: len(1.5))
    track_len_in: float = 6.0  # steel track/rail return path [in]   (Rel[track]: len(6))
    track_thick_in: float = 0.25  # track cross-section thickness [in]  (Rel[track]: len(0.25))
    N_turns: float = 250.0  # Maple `NN`
    mu_r_steel: float = 100.0  # Maple `usteel` (lumped 1018 relative permeability)
    mu_rec_pm: float = 1.05  # PM recoil permeability                (literal in Rel[mag])
    H_c_oersted: float = 11000.0  # PM coercivity [Oe]                (Maple `H[c]`, ~N52)
    mass_kg: float = 180.0  # Maple `mass` -- target mass for the equilibrium gap solve


# ---------------------------------------------------------------------------
# Symbolic derivation -- mirrors the .mw worksheet cell by cell.
# ---------------------------------------------------------------------------

_g, _N, _i = sp.symbols("g N i", real=True)
_ydepth, _pole_w, _pm_len, _leg_len = sp.symbols("ydepth pole_w pm_len leg_len", positive=True)
_base_len, _base_h, _track_len, _track_t = sp.symbols(
    "base_len base_h track_len track_t", positive=True
)
_mu_r_steel, _mu_rec_pm, _Hc = sp.symbols("mu_r_steel mu_rec_pm Hc", positive=True)

_mu0 = 4 * sp.pi * sp.Float(1e-7)  # Maple: u0 := 4*Pi*1e-7


def _Relf(l, ur, A):
    """Maple `Relf := unapply(l/(ur*u0*A), l, ur, A)`."""
    return l / (ur * _mu0 * A)


def _len_expr(a):
    """Symbolic Maple `len(a) = 25.4*a/1000` (a may be a symbol or expression)."""
    return sp.Float(25.4) * a / 1000


# Rel[...] terms, one-for-one with the worksheet's Rel[air]/Rel[mag]/Rel[leg]/Rel[base]/Rel[track]
_A_pole = _len_expr(_ydepth) * _len_expr(_pole_w)  # Maple: len(ydepth)*len(1)
_Rel_air = _Relf(_g, 1, _A_pole)
_Rel_mag = _Relf(_len_expr(_pm_len), _mu_rec_pm, _A_pole)
_Rel_leg = _Relf(_len_expr(_leg_len), _mu_r_steel, _A_pole)
_Rel_base = _Relf(_len_expr(_base_len), _mu_r_steel, _len_expr(_ydepth) * _len_expr(_base_h))
_Rel_track = _Relf(_len_expr(_track_len), _mu_r_steel, _len_expr(_track_t) * _len_expr(_ydepth))

_RelT = 2 * (_Rel_air + _Rel_leg + _Rel_mag) + _Rel_base + _Rel_track  # Maple: RelT

_PM_mmf = sp.Float(OERSTED_TO_A_PER_M) * _Hc * _len_expr(_pm_len)  # Maple: PM
_Mmf = 2 * (_PM_mmf - _N * _i)  # Maple: Mmf := 2*(PM - N*i)
_phi = _Mmf / _RelT  # Maple: phi := Mmf/RelT

# Maple: Frel1 := diff((1/2)*(Rel[air]*phi^2), g)
_Frel1 = sp.diff(sp.Rational(1, 2) * _Rel_air * _phi**2, _g)

_PARAM_SYMS = (
    _g,
    _N,
    _i,
    _ydepth,
    _pole_w,
    _pm_len,
    _leg_len,
    _base_len,
    _base_h,
    _track_len,
    _track_t,
    _mu_r_steel,
    _mu_rec_pm,
    _Hc,
)

# Maple: Frel11 := unapply(Frel1, g, N, i)  -- generalized here over all geometry too.
_force_per_leg_pair_numeric = sp.lambdify(_PARAM_SYMS, _Frel1, "numpy")


def force_per_leg_pair(g_m, N_turns, i_amp, geom: YokeGeometry):
    """Maple `Frel11(g, N, i)` -- the co-energy force from the air-gap reluctance term."""
    return _force_per_leg_pair_numeric(
        g_m,
        N_turns,
        i_amp,
        geom.ydepth_in,
        geom.pole_width_in,
        geom.pm_len_in,
        geom.leg_len_in,
        geom.base_len_in,
        geom.base_height_in,
        geom.track_len_in,
        geom.track_thick_in,
        geom.mu_r_steel,
        geom.mu_rec_pm,
        geom.H_c_oersted,
    )


def total_force(g_m, i_amp, geom: YokeGeometry):
    """Maple `4*Frel11(g, NN, i)` -- the worksheet's scale-up to total yoke force."""
    return 4.0 * force_per_leg_pair(g_m, geom.N_turns, i_amp, geom)


def equilibrium_gap_mm(geom: YokeGeometry, i_amp=0.0, bracket_mm=(0.1, 30.0)):
    """
    Maple `sol := fsolve(4*Frel11(g,NN,0)-Fw=0, g)*1000` -- the gap [mm] at which
    the yoke supports `geom.mass_kg` at the given coil current (0 A by default,
    matching the worksheet).
    """
    Fw = geom.mass_kg * 9.8  # Maple: Fw := mass*9.8  (note: 9.8, not 9.81)
    residual = lambda g_m: total_force(g_m, i_amp, geom) - Fw
    lo, hi = bracket_mm[0] * 1e-3, bracket_mm[1] * 1e-3
    return brentq(residual, lo, hi) * 1000.0


if __name__ == "__main__":
    geom = YokeGeometry()  # exact .mw defaults

    pm_mmf = OERSTED_TO_A_PER_M * geom.H_c_oersted * length_m(geom.pm_len_in)
    print(f"PM MMF (per leg)     = {pm_mmf:.5f} A-turns      (worksheet: 22233.94555)")

    f_check = force_per_leg_pair(5e-3, 250, 0, geom)
    print(f"Frel11(5mm, 250, 0)  = {f_check:.6f} N            (worksheet: 772.597343436)")

    gap_check = equilibrium_gap_mm(geom, i_amp=0.0)
    print(f"Equilibrium gap @180kg,i=0 = {gap_check:.6f} mm    (worksheet: 9.184990200)")

    print()
    print(f"Total force at 3mm, +/-16A: "
          f"{total_force(3e-3, -16, geom):.2f} N .. {total_force(3e-3, 16, geom):.2f} N")

"""
Small-signal linearization about the bias point (I_b ~= 0, s0).

Stiffnesses use the FULL-reluctance forms (PM Bias doc §4b): both are the ideal
single-gap values scaled by the gap-reluctance fraction eta = R_gap/R_total.
Because the PM dominates (eta ~ 0.11) they are ~9x smaller than the naive
single-gap formulas, and the unstable pole is ~4.3 Hz, not ~13 Hz.

Linear plant handed to the outer loop (in up-displacement dz = s0 - x):
    dZ(s)/dI_ref(s) = k_i / (m*s^2 - k_s)
k_i enters with a + sign *because* of the dz coordinate; k_s is a positive
magnitude that sits as +k_s here, giving the RHP pole s = +sqrt(k_s/m).
"""

import numpy as np

from . import params as P
from .plant import reluctance, phi_bias


def compute_stiffnesses(s0=P.S0):
    """
    Return (k_i, k_s) at gap s0 [N/A, N/m].

    k_i : current stiffness, positive & controllable  (dF/di)
    k_s : gap stiffness MAGNITUDE, destabilizing negative spring (|dF/dx|)
    """
    Rtot = reluctance(s0)
    phi0 = phi_bias(s0)                             # coil-off bias flux at s0
    k_i = 2.0 * phi0 * P.N / (P.MU0 * P.A * Rtot)
    k_s = 4.0 * phi0**2 / ((P.MU0 * P.A)**2 * Rtot)
    return k_i, k_s


def unstable_pole_hz(s0=P.S0, m=P.M):
    """Open-loop RHP pole frequency sqrt(k_s/m) in Hz."""
    _, k_s = compute_stiffnesses(s0)
    return np.sqrt(k_s / m) / (2.0 * np.pi)


def eta_gap_fraction(s0=P.S0):
    """Gap-reluctance fraction eta = R_gap / R_total at s0 (the §4b correction)."""
    R_gap = 2.0 * s0 / (P.MU0 * P.A)
    return R_gap / reluctance(s0)


def linear_plant_tf(s0=P.S0, m=P.M):
    """
    python-control TransferFunction dZ/dI_ref = k_i / (m*s^2 - k_s).
    Imported lazily so the plant/params modules don't require `control`.
    """
    import control

    k_i, k_s = compute_stiffnesses(s0)
    s = control.tf("s")
    return k_i / (m * s**2 - k_s), (k_i, k_s)


def linear_state_space(s0=P.S0, m=P.M):
    """
    State-space [dz, dzdot] with input i_ref (up-displacement coordinate).
    Prep for the Layer-4 LQR; both k_s/m and k_i/m enter positive here.
    """
    k_i, k_s = compute_stiffnesses(s0)
    A_mat = np.array([[0.0, 1.0], [k_s / m, 0.0]])
    B_mat = np.array([[0.0], [k_i / m]])
    return A_mat, B_mat, (k_i, k_s)

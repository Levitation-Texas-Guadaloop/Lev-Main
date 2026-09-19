"""
Single-actuator nonlinear plant — the shared physics used by every layer.

Magnetic model (reluctance / Thevenin-MMF form, from PM Bias doc §4b):
  - Two working air gaps of length x, in series with the PM + steel reluctance R0.
  - The PM is a constant MMF source (loadline), so the coil-off flux at gap x is
    phi_bias(x) = MMF_PM / reluctance(x).
  - Force is two-gap Maxwell stress:  F = phi^2 / (mu0 * A),  phi = (N*i + MMF_PM)/R.

COORDINATE / SIGN CONVENTION (this is the one that bit the project before):
  state gap `x` is POSITIVE when the gap is OPEN (pod hanging below the rail).
  Gravity OPENS the gap; the always-attractive magnet CLOSES it. So the EoM is
      m * xddot = m*g - F(i, x)
  which is UNSTABLE (an F - m*g sign would be a stable oscillator and is wrong).
  Controllers are designed in up-displacement dz = s0 - x; the flip is applied at
  the sim<->controller boundary, never inside the plant. See CLAUDE.md conventions.
"""

import numpy as np

from . import params as P


def reluctance(x):
    """Total loop reluctance at gap x [A/Wb]: two air gaps + PM + steel."""
    return 2.0 * x / (P.MU0 * P.A) + P.R0


def phi_bias(x):
    """Coil-off (PM-only) flux through the loop at gap x [Wb]."""
    return P.MMF_PM / reluctance(x)


def inductance(x):
    """Gap-dependent coil inductance L(x) = N^2 / reluctance(x) [H]."""
    return P.N**2 / reluctance(x)


def force(i, x):
    """Attractive force [N] (positive = toward the rail, closing the gap)."""
    phi = (P.N * i + P.MMF_PM) / reluctance(x)
    return phi**2 / (P.MU0 * P.A)


def equilibrium_current(x, m=P.M):
    """
    Coil current holding mass m against gravity at gap x:  force(i, x) = m*g.

    With the PM sized to carry the weight near S0 this is ~0 (the zero-power
    point). Solved in closed form since force is quadratic in i.
    """
    phi_needed = np.sqrt(m * P.G * P.MU0 * P.A)     # phi such that phi^2/(mu0 A) = m g
    return (phi_needed * reluctance(x) - P.MMF_PM) / P.N


def plant_ode(t, state, v_coil, m=P.M):
    """
    Full single-actuator ODE for scipy.solve_ivp / RK4.

    state  = [x, xdot, i]
      x    = air gap [m]        (positive = gap open)
      xdot = gap rate [m/s]
      i    = coil current [A]
    v_coil = applied coil voltage [V] (control input, zero-order-held per step)

    Returns [xdot, xddot, idot].

    NOTE: omits motional back-EMF (i*dL/dx*xdot and the PM-flux motional term).
    Those are inner-current-loop disturbances; add them for high-fidelity
    electrical studies. Kept out here so Layers 1-3 stay legible.
    """
    x, xdot, i = state
    x = max(x, 1e-4)                       # guard the 1/x singularity at contact

    F = force(i, x)
    L = inductance(x)

    xddot = (m * P.G - F) / m              # gap coord: gravity opens, magnet closes
    idot = (v_coil - P.R_COIL * i) / L     # coil electrical eq: V = R i + L di/dt

    return [xdot, xddot, idot]


def rk4_step(state, v_coil, dt, m=P.M):
    """Fixed-step RK4 advance of plant_ode by dt (used by the nested-loop sims)."""
    s = np.asarray(state, dtype=float)
    k1 = np.array(plant_ode(0.0, s, v_coil, m))
    k2 = np.array(plant_ode(0.0, s + 0.5 * dt * k1, v_coil, m))
    k3 = np.array(plant_ode(0.0, s + 0.5 * dt * k2, v_coil, m))
    k4 = np.array(plant_ode(0.0, s + dt * k3, v_coil, m))
    return s + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)

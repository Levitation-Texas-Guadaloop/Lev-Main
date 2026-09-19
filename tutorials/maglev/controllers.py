"""
Discrete-time controllers for the nested loop.

  PICurrentLoop        -- inner loop (Layer 2): tracks i_ref by commanding v_coil.
  PIDPositionLoop      -- outer loop (Layer 3): tracks a gap set-point, outputs i_ref.

The outer loop lives in up-displacement dz = s0 - x_gap (see plant.py convention).
It is the caller's job to pass measurements already flipped into dz; the sign flip
belongs at the sim<->controller boundary, not buried in the controller.
"""

import numpy as np

from . import params as P


class PICurrentLoop:
    """Discrete PI current controller: (i_ref, i_meas) -> v_coil."""

    def __init__(self, Kp, Ki, dt, i_max=P.I_MAX, v_max=P.V_MAX):
        self.Kp = Kp
        self.Ki = Ki
        self.dt = dt
        self.i_max = i_max
        self.v_max = v_max
        self.integrator = 0.0

    def reset(self):
        self.integrator = 0.0

    def update(self, i_ref, i_meas):
        e = np.clip(i_ref, -self.i_max, self.i_max) - i_meas
        # provisional output, then anti-windup: only integrate if not saturated
        v_unsat = self.Kp * e + self.Ki * (self.integrator + e * self.dt)
        v = np.clip(v_unsat, -self.v_max, self.v_max)
        if v == v_unsat:                      # inside linear range -> commit integral
            self.integrator += e * self.dt
        return v


class PIDPositionLoop:
    """
    Discrete PID with filtered derivative, in up-displacement dz.
    (dz_ref, dz_meas) -> i_ref.

    C(s) = Kp + Ki/s + Kd*s / (tau*s + 1)
    Positive gains stabilize because dZ/dI_ref = +k_i/(m*s^2 - k_s) in this coord.
    """

    def __init__(self, Kp, Ki, Kd, dt, tau=1e-3, i_max=P.I_MAX):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.dt = dt
        self.tau = tau
        self.i_max = i_max
        self.integrator = 0.0
        self.d_state = 0.0                    # filtered-derivative state
        self._prev_e = None

    def reset(self):
        self.integrator = 0.0
        self.d_state = 0.0
        self._prev_e = None

    def update(self, dz_ref, dz_meas):
        e = dz_ref - dz_meas
        if self._prev_e is None:
            self._prev_e = e

        # filtered derivative of the error (first-order low-pass on de/dt)
        de = (e - self._prev_e) / self.dt
        alpha = self.dt / (self.tau + self.dt)
        self.d_state += alpha * (de - self.d_state)
        self._prev_e = e

        i_unsat = self.Kp * e + self.Ki * (self.integrator + e * self.dt) + self.Kd * self.d_state
        i_ref = np.clip(i_unsat, -self.i_max, self.i_max)
        if i_ref == i_unsat:                  # anti-windup
            self.integrator += e * self.dt
        return i_ref

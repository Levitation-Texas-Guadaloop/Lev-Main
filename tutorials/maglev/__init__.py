"""
maglev — shared single-actuator digital-twin core for the Matam maglev sandbox.

Layered per `Maglev - Python Simulation Sandbox.md`:
  Layer 1  single-actuator nonlinear ODE + open-loop crash   (plant.py)
  Layer 2  inner PI current loop / bandwidth                  (controllers.PICurrentLoop)
  Layer 3  SISO PID outer gap loop, Bode/margins, nested sim  (controllers.PIDPositionLoop)

Everything imports its physics from `params` and `plant`, so the layers can
never drift out of sync.
"""

from . import params, plant, linearization, controllers  # noqa: F401

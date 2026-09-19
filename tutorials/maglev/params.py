"""
Physical parameters for the single-actuator maglev core — the ONE place these
live. Every layer imports from here so the plant, linearization, and controllers
can never drift out of sync.

Source of the numbers: the Maglev research vault
  - `Maglev - PM Bias and Force Linearization.md` (§4b series-reluctance model, §7 numbers)
  - `Maglev - Python Simulation Sandbox.md`   (Layer 1 parameter block)

Values are ILLUSTRATIVE (s0 = 3 mm design point, single 1"-deep core). Per the
project handoff the model *formulation* is what matters here, not committed
hardware numbers. Swap them freely; the formulas downstream are what count.
"""

import numpy as np

# --- Fundamental constants ---------------------------------------------------
MU0 = 4 * np.pi * 1e-7          # vacuum permeability [H/m]
G = 9.81                        # gravitational acceleration [m/s^2]

# --- Magnetic circuit geometry (single core) ---------------------------------
A = 6.45e-4                     # pole-face area [m^2]  (1 in^2)
N = 250                         # coil turns (loop total)
R_COIL = 2.0                    # coil resistance [ohm]

# --- Series (x-independent) reluctance -- the PM DOMINATES, do not neglect ----
# The PM is magnetically ~an air gap of its own length (mu_rec ~ 1.05). For the
# real 1"-per-leg yoke the gap is only ~11% of the loop reluctance (eta ~ 0.11).
MU_REC = 1.05                   # NdFeB recoil permeability
L_PM = 2 * 0.0254              # total PM length in the loop [m] (1" per leg x 2)
MU_R = 800                      # 1018 steel relative permeability (unsaturated)
L_IRON = 0.15                   # mean steel path length [m]

R_PM = L_PM / (MU0 * MU_REC * A)      # PM reluctance (the dominant term)
R_STEEL = L_IRON / (MU0 * MU_R * A)    # steel reluctance (small)
R0 = R_PM + R_STEEL                    # x-independent series reluctance

# --- PM as a Thevenin MMF source (loadline), NOT a fixed flux offset ----------
BR = 1.3                        # NdFeB N42 remanence [T]
HC = BR / (MU0 * MU_REC)        # normal-curve coercivity [A/m]
MMF_PM = HC * L_PM              # PM magnetomotive force [A-turns]

# --- Mechanical --------------------------------------------------------------
M = 69.0                        # supported mass per core [kg] (F0 = M*g ~ 680 N)

# --- Nominal operating point -------------------------------------------------
S0 = 3e-3                       # design air gap [m] (3 mm)

# --- Actuator / driver limits (used by the current loop) ---------------------
I_MAX = 5.0                     # coil current clamp [A]
V_MAX = 24.0                    # bus / driver voltage clamp [V]

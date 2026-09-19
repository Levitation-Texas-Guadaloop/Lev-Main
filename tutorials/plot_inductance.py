"""
Quick look: coil inductance L(x) = N^2 / reluctance(x) vs air gap.

Because the PM series reluctance dominates the loop, L barely changes with gap
(~1.0 mH at 1 mm down to ~0.57 mH at 20 mm) -- a useful sanity check that the
current-loop plant is nearly gap-independent.

Run:  python3 plot_inductance.py   ->  figures/inductance_vs_gap.png
"""

import os

import numpy as np
import matplotlib.pyplot as plt

from maglev import params as P
from maglev.plant import inductance

FIGDIR = os.path.join(os.path.dirname(__file__), "figures")
os.makedirs(FIGDIR, exist_ok=True)

gaps_mm = np.arange(1, 21, 1)                  # 1..20 mm, step 1
L_mH = inductance(gaps_mm * 1e-3) * 1e3        # convert m->L, H->mH

fig, ax = plt.subplots(figsize=(7, 4))
ax.plot(gaps_mm, L_mH, "-o", ms=5, lw=1.5, color="#2563eb")
ax.axvline(P.S0 * 1e3, color="crimson", ls=":", lw=1.5,
           label=f"s0 = {P.S0*1e3:.0f} mm  (L = {inductance(P.S0)*1e3:.3f} mH)")

ax.set_xlabel("air gap [mm]")
ax.set_ylabel("inductance L [mH]")
ax.set_title("Coil inductance vs. air gap (PM reluctance flattens it)")
ax.set_xlim(0, 21)
ax.set_xticks(np.arange(0, 21, 2))
ax.set_ylim(0, L_mH.max() * 1.1)              # start at 0 so the small variation reads honestly
ax.legend(fontsize=9)
ax.grid(True, alpha=0.3)

fig.tight_layout()
out = os.path.join(FIGDIR, "inductance_vs_gap.png")
fig.savefig(out, dpi=150)
plt.close(fig)
print(f"L(1mm)  = {L_mH[0]:.3f} mH")
print(f"L(20mm) = {L_mH[-1]:.3f} mH")
print(f"saved {out}")

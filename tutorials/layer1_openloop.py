"""
Layer 1 — Single-Actuator Open-Loop Crash
==========================================

Goal: confirm the open-loop instability is real and that its growth rate matches
the RHP pole predicted by the linearization. This is the sanity check that the
force model and the (unstable) sign convention are right before any control.

We hold the coil at its constant equilibrium voltage (no feedback), nudge the
gap by 1%, and integrate. The gap runs away exponentially; one direction crashes
to contact. We then fit the early-time growth rate and compare it to the
predicted pole sqrt(k_s/m).

Run:  python3 layer1_openloop.py
Out:  figures/layer1_openloop.png
"""

import os

import numpy as np
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt

from maglev import params as P
from maglev.plant import plant_ode, equilibrium_current, force
from maglev.linearization import compute_stiffnesses, unstable_pole_hz, eta_gap_fraction

FIGDIR = os.path.join(os.path.dirname(__file__), "figures")
os.makedirs(FIGDIR, exist_ok=True)


def main():
    s0 = P.S0
    k_i, k_s = compute_stiffnesses(s0)
    p_hz = unstable_pole_hz(s0)
    p_rad = 2 * np.pi * p_hz                     # predicted growth rate [1/s]

    # Equilibrium: PM carries the weight, so the trim current is small.
    i_eq = equilibrium_current(s0)
    v_eq = P.R_COIL * i_eq                        # constant voltage -> constant current

    print("=== Layer 1: open-loop plant ===")
    print(f"eta (gap/total reluctance) = {eta_gap_fraction(s0):.3f}")
    print(f"k_i = {k_i:.2f} N/A,  k_s = {k_s:.3e} N/m")
    print(f"equilibrium force check    = {force(i_eq, s0):.1f} N   (weight = {P.M*P.G:.1f} N)")
    print(f"trim current i_eq          = {i_eq:.3f} A")
    print(f"predicted RHP pole         = {p_hz:.2f} Hz  ({p_rad:.1f} rad/s)")
    print(f"predicted e-folding time   = {1/p_rad*1e3:.1f} ms")

    # Inward 1% gap perturbation, constant voltage, integrate until near contact.
    # Perturbing the gap CLOSED raises the force above gravity -> the gap keeps
    # closing -> crash to the rail. (Perturbing it open gives the mirror-image
    # runaway where the pod falls away; either branch proves the instability.)
    state0 = [s0 * 0.99, 0.0, i_eq]

    def hit_contact(t, s, *a):
        return s[0] - 1e-4                        # stop when gap -> 0.1 mm
    hit_contact.terminal = True
    hit_contact.direction = -1

    def rhs(t, s):
        return plant_ode(t, s, v_eq)

    sol = solve_ivp(rhs, (0, 0.5), state0, max_step=1e-4,
                    dense_output=True, events=hit_contact, rtol=1e-9, atol=1e-12)

    t = sol.t
    gap_mm = sol.y[0] * 1e3
    cur = sol.y[2]
    t_crash = t[-1] if sol.t_events[0].size == 0 else sol.t_events[0][0]
    print(f"time to (near) contact     = {t_crash*1e3:.1f} ms")

    # --- Verify the early growth rate matches the RHP pole -------------------
    # Perturbation dx = |gap - s0| grows ~ exp(p_rad * t) in the linear regime.
    # Fit a TIGHT small-signal window: outside it the stiffness k_s(x) stiffens
    # as the gap closes and the growth accelerates past the linear pole.
    dx = np.abs(sol.y[0] - s0)
    lin = (dx > 0.02 * s0) & (dx < 0.12 * s0)     # small-signal band

    slope = None
    if np.count_nonzero(lin) >= 2:
        slope, _ = np.polyfit(t[lin], np.log(dx[lin]), 1)
        print(f"fitted growth rate         = {slope:.1f} rad/s "
              f"(predicted {p_rad:.1f}, error {100*abs(slope-p_rad)/p_rad:.1f}%)")
    else:
        # Pod never left the small-signal band in this window: it was started at
        # (or too near) the unstable equilibrium, so there is simply no divergence
        # to fit. Correct outcome for a zero/tiny perturbation -- report it plainly
        # rather than fabricate a slope. Perturb the gap (e.g. state0 x = s0*0.99)
        # or lengthen t_span to see the crash.
        print("fitted growth rate         = n/a  (pod held at the unstable "
              "equilibrium; no divergence in window)")

    # --- Plot ----------------------------------------------------------------
    fig, (ax_g, ax_i) = plt.subplots(1, 2, figsize=(11, 4))

    ax_g.plot(t * 1e3, gap_mm, lw=2, color="#2563eb")
    ax_g.axhline(s0 * 1e3, color="gray", ls="--", lw=1, label=f"s0 = {s0*1e3:.0f} mm")
    ax_g.set_xlabel("time [ms]")
    ax_g.set_ylabel("air gap [mm]")
    ax_g.set_title("Open-loop gap: diverges to contact (RHP pole)")
    ax_g.legend(fontsize=9)
    ax_g.grid(True, alpha=0.3)

    # log-magnitude of the perturbation with the predicted slope overlaid.
    # Floor dx so an exact-equilibrium start (dx == 0) doesn't hit log(0).
    ax_i.semilogy(t * 1e3, np.maximum(dx, 1e-9) * 1e3, lw=2, color="#2563eb",
                  label="|gap - s0| (sim)")
    if slope is not None:
        t_ref = t[lin]
        ax_i.semilogy(t_ref * 1e3, dx[lin][0] * 1e3 * np.exp(p_rad * (t_ref - t_ref[0])),
                      "k--", lw=1.5, label=f"exp(+{p_rad:.0f} t): predicted pole")
    ax_i.set_xlabel("time [ms]")
    ax_i.set_ylabel("gap perturbation [mm]")
    ax_i.set_title("Growth rate matches sqrt(k_s/m)")
    ax_i.legend(fontsize=9)
    ax_i.grid(True, which="both", alpha=0.3)

    fig.tight_layout()
    out = os.path.join(FIGDIR, "layer1_openloop.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"saved {out}")


if __name__ == "__main__":
    main()

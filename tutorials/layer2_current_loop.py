"""
Layer 2 — Inner PI Current Loop
===============================

Goal: close the coil current loop cleanly and measure its bandwidth. The current
loop is the innermost of the nested architecture; for the outer gap loop to see
"F = k_i * i_ref" it must be far faster than everything mechanical. Target here
is ~1 kHz -- roughly 200x the ~4.3 Hz unstable mechanical pole and comfortably
past the "5-10x" minimum from the plan.

Electrical plant (gap frozen at s0, the standard current-loop assumption since
the gap moves far slower than the current):
    i / v = 1 / (L*s + R),   L = L(s0),   pole at R/L.

We tune the PI by pole-zero cancellation (Ki/Kp = R/L), which makes the loop
gain Kp/(L*s) and the closed loop a clean first-order lag with bandwidth Kp/L.
We then verify with an empirical closed-loop frequency sweep using the *actual
discrete* controller, not just the continuous formula.

Run:  python3 layer2_current_loop.py
Out:  figures/layer2_current_loop.png
"""

import os

import numpy as np
import matplotlib.pyplot as plt

from maglev import params as P
from maglev.plant import inductance
from maglev.linearization import unstable_pole_hz
from maglev.controllers import PICurrentLoop

FIGDIR = os.path.join(os.path.dirname(__file__), "figures")
os.makedirs(FIGDIR, exist_ok=True)

FS = 40e3                      # inner-loop sample rate [Hz] (in the 1-10 kHz band)
DT = 1.0 / FS


def pi_gains_for_bandwidth(f_bw, L, R):
    """PI gains by pole-zero cancellation for a target closed-loop bandwidth."""
    w = 2 * np.pi * f_bw
    Kp = w * L                 # closed-loop bandwidth = Kp / L
    Ki = w * R                 # = Kp * (R/L): cancels the electrical pole
    return Kp, Ki


def sim_current_response(i_ref_fn, Kp, Ki, L, R, t_end, i0=0.0):
    """
    Discrete PI + exact first-order electrical update, gap frozen.
    Exact ZOH update of i' = (v - R i)/L avoids integration error entirely.
    Returns (t, i_ref, i).
    """
    ctrl = PICurrentLoop(Kp, Ki, DT)
    n = int(t_end / DT)
    t = np.arange(n) * DT
    i = np.empty(n)
    iref = np.empty(n)
    ik = i0
    decay = np.exp(-R / L * DT)
    for k in range(n):
        r = i_ref_fn(t[k])
        v = ctrl.update(r, ik)
        ik = ik * decay + (v / R) * (1 - decay)     # exact linear-RL ZOH step
        i[k] = ik
        iref[k] = r
    return t, iref, i


def measure_bandwidth(Kp, Ki, L, R, freqs, amp=0.3):
    """Empirical closed-loop |i/i_ref| vs frequency; return (mag_db, f_3db)."""
    mag = []
    for f in freqs:
        n_settle = 6                                  # periods to reach steady state
        t_end = max(n_settle / f, 20 * DT)
        t, iref, i = sim_current_response(
            lambda tt, f=f: amp * np.sin(2 * np.pi * f * tt), Kp, Ki, L, R, t_end)
        keep = t > 0.5 * t_end                        # drop the transient
        out_amp = (i[keep].max() - i[keep].min()) / 2
        mag.append(out_amp / amp)
    mag = np.array(mag)
    mag_db = 20 * np.log10(mag)
    # first crossing below -3 dB
    below = np.where(mag_db < -3.0)[0]
    f_3db = freqs[below[0]] if below.size else np.nan
    return mag_db, f_3db


def main():
    s0 = P.S0
    L = inductance(s0)
    R = P.R_COIL
    f_elec = R / L / (2 * np.pi)
    f_mech = unstable_pole_hz(s0)

    print("=== Layer 2: inner current loop ===")
    print(f"L(s0)               = {L*1e3:.3f} mH")
    print(f"R                   = {R:.1f} ohm")
    print(f"open electrical pole= {f_elec:.0f} Hz")
    print(f"mechanical pole     = {f_mech:.2f} Hz  (loop must dwarf this)")
    print(f"sample rate         = {FS/1e3:.0f} kHz")

    # --- step responses at three target bandwidths --------------------------
    targets = [500, 1000, 2000]
    colors = {500: "#16a34a", 1000: "#2563eb", 2000: "#dc2626"}
    step_data = {}
    for f_bw in targets:
        Kp, Ki = pi_gains_for_bandwidth(f_bw, L, R)
        t, iref, i = sim_current_response(lambda tt: 1.0 * (tt >= 0), Kp, Ki, L, R,
                                          t_end=4e-3)
        # 10-90% rise time
        i_ss = i[-1]
        try:
            t10 = t[np.where(i >= 0.1 * i_ss)[0][0]]
            t90 = t[np.where(i >= 0.9 * i_ss)[0][0]]
            tr = t90 - t10
        except IndexError:
            tr = np.nan
        overshoot = 100 * (i.max() - i_ss) / i_ss
        print(f"  target {f_bw:>4d} Hz: Kp={Kp:.3f}, Ki={Ki:.0f}, "
              f"rise(10-90%)={tr*1e6:.0f} us, overshoot={overshoot:.1f}%")
        step_data[f_bw] = (t, iref, i)

    # --- empirical bandwidth of the 1 kHz design ----------------------------
    Kp, Ki = pi_gains_for_bandwidth(1000, L, R)
    freqs = np.logspace(1, np.log10(FS / 4), 40)     # 10 Hz .. Nyquist/2
    mag_db, f_3db = measure_bandwidth(Kp, Ki, L, R, freqs)
    print(f"empirical -3 dB bandwidth (1 kHz design) = {f_3db:.0f} Hz")
    print(f"  -> {f_3db/f_mech:.0f}x the mechanical pole")

    # --- plots --------------------------------------------------------------
    fig, (ax_s, ax_b) = plt.subplots(1, 2, figsize=(11, 4))

    for f_bw in targets:
        t, iref, i = step_data[f_bw]
        ax_s.plot(t * 1e3, i, lw=2, color=colors[f_bw], label=f"{f_bw} Hz target")
    ax_s.plot(step_data[targets[0]][0] * 1e3, step_data[targets[0]][1],
              "k--", lw=1, label="i_ref (1 A step)")
    ax_s.set_xlabel("time [ms]")
    ax_s.set_ylabel("coil current [A]")
    ax_s.set_title("Current-loop step response vs. target bandwidth")
    ax_s.legend(fontsize=9)
    ax_s.grid(True, alpha=0.3)

    ax_b.semilogx(freqs, mag_db, "-o", ms=3, lw=1.5, color="#2563eb",
                  label="closed-loop |i / i_ref| (sim)")
    ax_b.axhline(-3, color="gray", ls="--", lw=1, label="-3 dB")
    ax_b.axvline(1000, color="#2563eb", ls=":", lw=1, label="design 1 kHz")
    ax_b.axvline(f_mech, color="crimson", ls=":", lw=1.5,
                 label=f"mech pole {f_mech:.1f} Hz")
    if np.isfinite(f_3db):
        ax_b.axvline(f_3db, color="green", ls=":", lw=1,
                     label=f"measured -3 dB {f_3db:.0f} Hz")
    ax_b.set_xlabel("frequency [Hz]")
    ax_b.set_ylabel("magnitude [dB]")
    ax_b.set_title("Inner-loop bandwidth dwarfs the mechanical pole")
    ax_b.set_ylim(-20, 5)
    ax_b.legend(fontsize=8, loc="lower left")
    ax_b.grid(True, which="both", alpha=0.3)

    fig.tight_layout()
    out = os.path.join(FIGDIR, "layer2_current_loop.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"saved {out}")


if __name__ == "__main__":
    main()

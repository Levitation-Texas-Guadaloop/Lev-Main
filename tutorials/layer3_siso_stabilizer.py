"""
Layer 3 — SISO Outer Gap Stabilizer (nested loop)
=================================================

Goal: stabilize a single actuator and see the design tradeoffs. Two parts:

  (A) Linear loop-shaping with python-control on the up-displacement plant
        dZ(s)/dI_ref(s) = k_i / (m*s^2 - k_s).
      Read gain/phase margins off the Bode plot and confirm the one constraint
      an RHP-pole plant cannot escape (see bode_poles/): the gain crossover must
      sit ABOVE the unstable-pole frequency.

  (B) Full nonlinear NESTED-loop sim: outer PD gap loop (2 kHz) -> i_ref ->
      inner PI current loop (40 kHz) -> v_coil -> nonlinear plant (RK4, 200 kHz).
      Start from a large gap perturbation, then hit it with a payload-force step,
      and watch it hold the gap.

Design note: we use a PD stabilizer, not the doc's illustrative PID. Two reasons:
  * Kp must exceed k_s/k_i (~7340 A/m) just to turn the negative spring positive;
    the doc's Kp=500 is ~15x too small and does not stabilize at all.
  * The PM carries the weight (i_eq ~= 0), so there is no steady gravity offset to
    integrate out. Adding an integrator here drags a closed-loop pole to the
    origin (slow drift mode) and makes the loop conditionally stable. A slow
    integral trim can be layered on later for disturbance rejection if needed.

Run:  python3 layer3_siso_stabilizer.py
Out:  figures/layer3_bode.png, figures/layer3_nonlinear.png
"""

import os

import numpy as np
import control
import matplotlib.pyplot as plt

from maglev import params as P
from maglev.plant import force, inductance, equilibrium_current, rk4_step
from maglev.linearization import compute_stiffnesses, unstable_pole_hz
from maglev.controllers import PICurrentLoop, PIDPositionLoop

FIGDIR = os.path.join(os.path.dirname(__file__), "figures")
os.makedirs(FIGDIR, exist_ok=True)

# --- PD stabilizer gains (up-displacement dz = s0 - x) -----------------------
KP = 25000.0        # A/m   (> k_s/k_i so closed-loop stiffness is positive)
KD = 600.0          # A/(m/s)
KI = 0.0            # off: PM carries the weight, no steady offset to null
TAU_D = 1e-3        # derivative filter time constant

# --- loop rates --------------------------------------------------------------
FS_PLANT = 200e3;  DT_PLANT = 1 / FS_PLANT
FS_INNER = 40e3;   N_INNER = int(FS_PLANT / FS_INNER)     # inner PI every 5 steps
FS_OUTER = 2e3;    N_OUTER = int(FS_PLANT / FS_OUTER)     # outer PD every 100 steps


def linear_design():
    """Part A: build the loop, print margins, plot the Bode with the pole marked."""
    s0 = P.S0
    k_i, k_s = compute_stiffnesses(s0)
    m = P.M
    f_p = unstable_pole_hz(s0)

    s = control.tf("s")
    plant = k_i / (m * s**2 - k_s)
    C = KP + KD * s / (TAU_D * s + 1) + (KI / s if KI else 0)
    L = C * plant

    gm, pm, wpc, wgc = control.margin(L)
    # gain crossover (|L| = 1), found directly for a clean readout
    w = np.logspace(-1, 4, 40000)
    mag = np.abs(control.frequency_response(L, w).frdata.squeeze())
    cross = w[np.where(np.diff(np.sign(mag - 1)))[0]]
    f_gc = cross[-1] / (2 * np.pi) if cross.size else np.nan

    T = control.feedback(L, 1)
    cl_poles = control.poles(T)
    stable = np.all(cl_poles.real < 0)

    print("=== Layer 3A: linear loop shaping ===")
    print(f"unstable pole            = {f_p:.2f} Hz")
    print(f"gain crossover f_gc      = {f_gc:.2f} Hz  "
          f"({'ABOVE' if f_gc > f_p else 'BELOW'} the pole -> "
          f"{'OK' if f_gc > f_p else 'CANNOT STABILIZE'})")
    print(f"phase margin             = {pm:.1f} deg")
    print(f"closed-loop stable       = {stable}  (max Re pole = {cl_poles.real.max():.1f})")

    # --- Bode plot ----------------------------------------------------------
    resp = control.frequency_response(L, w)
    magdb = 20 * np.log10(np.abs(resp.frdata.squeeze()))
    phase = np.unwrap(np.angle(resp.frdata.squeeze())) * 180 / np.pi

    fig, (ax_m, ax_p) = plt.subplots(2, 1, figsize=(8, 7), sharex=True)
    ax_m.semilogx(w / (2 * np.pi), magdb, lw=2, color="#2563eb", label="loop L=C·P")
    ax_m.axhline(0, color="gray", ls="--", lw=1)
    ax_m.axvline(f_p, color="crimson", ls=":", lw=1.5, label=f"RHP pole {f_p:.1f} Hz")
    ax_m.axvline(f_gc, color="green", ls=":", lw=1.5, label=f"gain crossover {f_gc:.1f} Hz")
    ax_m.set_ylabel("magnitude [dB]")
    ax_m.set_title("Layer 3A: loop gain — crossover placed above the RHP pole")
    ax_m.legend(fontsize=8, loc="upper right")
    ax_m.grid(True, which="both", alpha=0.3)

    ax_p.semilogx(w / (2 * np.pi), phase, lw=2, color="#2563eb")
    ax_p.axhline(-180, color="gray", ls="--", lw=1)
    ax_p.axvline(f_p, color="crimson", ls=":", lw=1.5)
    ax_p.axvline(f_gc, color="green", ls=":", lw=1.5)
    ax_p.annotate(f"PM = {pm:.0f}°", xy=(f_gc, -180 + pm),
                  xytext=(f_gc * 1.5, -180 + pm + 20),
                  arrowprops=dict(arrowstyle="->", color="black"))
    ax_p.set_ylabel("phase [deg]")
    ax_p.set_xlabel("frequency [Hz]")
    ax_p.grid(True, which="both", alpha=0.3)

    fig.tight_layout()
    out = os.path.join(FIGDIR, "layer3_bode.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"saved {out}")


def nonlinear_nested_sim():
    """
    Part B: outer PD (dz) -> inner PI (i) -> nonlinear plant, with a payload-force
    disturbance partway through. Returns the logged trajectories.
    """
    s0 = P.S0
    m = P.M
    L0 = inductance(s0)
    R = P.R_COIL

    # inner PI tuned in Layer 2 for ~1 kHz bandwidth
    w_bw = 2 * np.pi * 1000
    inner = PICurrentLoop(Kp=w_bw * L0, Ki=w_bw * R, dt=1 / FS_INNER)
    outer = PIDPositionLoop(KP, KI, KD, dt=1 / FS_OUTER, tau=TAU_D)

    # start 15% open (pod dropped), currents/rates at rest
    i_eq = equilibrium_current(s0)
    state = np.array([s0 * 1.15, 0.0, i_eq])

    t_end = 0.6
    t_dist = 0.3                      # payload-force step at 0.3 s
    # Extra downward (gap-opening) force. Kept within actuator authority: holding
    # dF needs di ~ dF/k_i, and the 5 A clamp caps that at ~34 N. 60 N would
    # saturate the coil and drop the pod -- authority, not tuning, is the limit.
    F_dist = 20.0                     # ~2 kg payload, ~3 A of extra current
    n = int(t_end / DT_PLANT)

    log_t = np.empty(n); log_x = np.empty(n); log_i = np.empty(n)
    log_iref = np.empty(n); log_v = np.empty(n)

    i_ref = i_eq
    v_coil = R * i_eq
    for k in range(n):
        t = k * DT_PLANT
        F_d = F_dist if t >= t_dist else 0.0

        if k % N_OUTER == 0:
            dz_meas = s0 - state[0]          # SIGN FLIP at the sim<->controller boundary
            i_ref = outer.update(0.0, dz_meas)
        if k % N_INNER == 0:
            v_coil = inner.update(i_ref, state[2])

        # RK4 with the disturbance force folded into the gap EoM
        def ode(_t, sv):
            x, xd, i = sv
            x = max(x, 1e-4)
            F = force(i, x)
            Lc = inductance(x)
            return np.array([xd, (m * P.G + F_d - F) / m, (v_coil - R * i) / Lc])

        k1 = ode(0, state)
        k2 = ode(0, state + 0.5 * DT_PLANT * k1)
        k3 = ode(0, state + 0.5 * DT_PLANT * k2)
        k4 = ode(0, state + DT_PLANT * k3)
        state = state + (DT_PLANT / 6) * (k1 + 2 * k2 + 2 * k3 + k4)

        log_t[k] = t; log_x[k] = state[0]; log_i[k] = state[2]
        log_iref[k] = i_ref; log_v[k] = v_coil

    settled = log_x[log_t > t_dist - 0.02]
    print("\n=== Layer 3B: nonlinear nested-loop sim ===")
    print(f"start gap                = {s0*1.15*1e3:.2f} mm (15% open)")
    print(f"recovered gap (pre-dist) = {log_x[np.argmin(np.abs(log_t-0.28))]*1e3:.3f} mm")
    print(f"final gap                = {log_x[-1]*1e3:.3f} mm  (target {s0*1e3:.2f} mm)")
    print(f"steady offset from dist  = {(log_x[-1]-s0)*1e6:.1f} um  ({F_dist:.0f} N payload)")
    print(f"peak current             = {np.max(np.abs(log_i)):.2f} A  (clamp {P.I_MAX} A)")
    return log_t, log_x, log_i, log_iref, t_dist


def plot_nonlinear(log_t, log_x, log_i, log_iref, t_dist):
    s0 = P.S0
    fig, (ax_g, ax_i) = plt.subplots(1, 2, figsize=(11, 4))

    ax_g.plot(log_t * 1e3, log_x * 1e3, lw=1.5, color="#2563eb")
    ax_g.axhline(s0 * 1e3, color="gray", ls="--", lw=1, label=f"target {s0*1e3:.0f} mm")
    ax_g.axvline(t_dist * 1e3, color="crimson", ls=":", lw=1.5, label="payload step")
    ax_g.set_xlabel("time [ms]")
    ax_g.set_ylabel("air gap [mm]")
    ax_g.set_title("Stabilized gap: recovers from 15% drop, holds through disturbance")
    ax_g.legend(fontsize=9)
    ax_g.grid(True, alpha=0.3)

    ax_i.plot(log_t * 1e3, log_iref, lw=1, color="#dc2626", alpha=0.7, label="i_ref (outer)")
    ax_i.plot(log_t * 1e3, log_i, lw=1.5, color="#16a34a", label="i (measured)")
    ax_i.axvline(t_dist * 1e3, color="crimson", ls=":", lw=1.5)
    ax_i.set_xlabel("time [ms]")
    ax_i.set_ylabel("coil current [A]")
    ax_i.set_title("Inner loop tracks i_ref; current holds against the load")
    ax_i.legend(fontsize=9)
    ax_i.grid(True, alpha=0.3)

    fig.tight_layout()
    out = os.path.join(FIGDIR, "layer3_nonlinear.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"saved {out}")


def main():
    linear_design()
    data = nonlinear_nested_sim()
    plot_nonlinear(*data)


if __name__ == "__main__":
    main()

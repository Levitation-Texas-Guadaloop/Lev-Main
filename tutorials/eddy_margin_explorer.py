"""
Eddy-Margin Explorer — what solid/thick yoke slices do to the gap loop
======================================================================

Companion to `docs/U-Core - Lamination.md` §0.2. Builds intuition for:

  * what "magnitude" and "phase" of the eddy factor mean,
  * how a magnitude < 1 pulls the gain crossover DOWN, toward the RHP pole,
  * how the eddy phase lag subtracts from phase margin,
  * why an open-loop-unstable plant has TWO gain margins (you can fail by
    turning the gain down, not just up).

Loop (outer gap loop, up-displacement dz, same plant as Layer 3):

    L(jw) = C(jw) · Gi(jw) · E(jw) · D(jw) · k_i / (m s^2 - k_s)

    C  = Kp + Kd·s/(tau·s + 1)          PD stabilizer (Layer 3)
    Gi = 1 / (s/w_i + 1)                inner current loop, first-order
    D  = exp(-s·T)                      compute / sample delay
    E  = R_dc / (R_gap + R_PM + R_Fe(jw))
         R_Fe(jw) = R_Fe,dc · x/tanh(x),  x = (1+j)·d/(2·delta)

E is the eddy factor: gap flux per amp at frequency w, relative to DC. It is
1 at DC by construction, so k_i and k_s stay exactly the repo's values. Only
the lengths matter for E, not the area: the iron share of the circuit is
(l_Fe/mu_r) / (2·s0 + l_PM/mu_rec + l_Fe/mu_r).

E is not rational (tanh of sqrt(s)), so everything here is computed
numerically from the frequency response: margins by crossing search, and
stability by counting Nyquist encirclements (one RHP pole means you need
exactly one CCW encirclement of -1).

Run:
    python3 eddy_margin_explorer.py              # interactive GUI
    python3 eddy_margin_explorer.py --selftest   # checks numerics vs python-control
    python3 eddy_margin_explorer.py --snapshot figures/eddy_margins.png
"""

import argparse
import sys

import numpy as np

from maglev import params as P
from maglev.linearization import compute_stiffnesses, unstable_pole_hz

# --- defaults (Layer 3 PD + lamination-doc geometry) ------------------------
KP0, KD0, TAU_D = 25000.0, 600.0, 1e-3
D0_MM = 25.4               # current build: 1" JB-Welded slices
MUR0 = 500.0               # incremental mu_r under PM bias (assumed)
LFE0 = 0.33                # iron path length of the big yoke [m]
FI0 = 1000.0               # inner current-loop bandwidth [Hz]
DELAY0_MS = 0.25           # ~half a 2 kHz outer-loop sample
RHO = {"1018 (15.9 µΩ·cm)": 1.59e-7, "Si steel (~50 µΩ·cm)": 5.0e-7}

F = np.logspace(-1, 4.5, 6000)            # Hz
W = 2 * np.pi * F

K_I, K_S = compute_stiffnesses(P.S0)
F_POLE = unstable_pole_hz(P.S0)


# ===========================================================================
# Frequency-domain pieces
# ===========================================================================
def eddy_factor(w, d, mur, l_fe, rho):
    """E(jw): gap flux per amp relative to DC, for slice thickness d [m]."""
    sigma = 1.0 / rho
    delta = np.sqrt(2.0 / (w * mur * P.MU0 * sigma))
    x = (1 + 1j) * d / (2 * delta)
    # x/tanh(x) -> 1 as x -> 0, -> x for |x| large (tanh -> 1, avoid overflow)
    t = np.where(np.abs(x) > 20, 1.0 + 0j, np.tanh(np.where(np.abs(x) > 20, 1, x)))
    fac = np.where(np.abs(x) < 1e-6, 1.0 + 0j, x / t)
    r_air = 2 * P.S0 + P.L_PM / P.MU_REC          # equivalent-air lengths [m]
    r_fe = l_fe / mur
    return (r_air + r_fe) / (r_air + r_fe * fac)


def loop(w, kp, kd, fi, delay, E=1.0):
    s = 1j * w
    C = kp + kd * s / (TAU_D * s + 1)
    Gi = 1.0 / (s / (2 * np.pi * fi) + 1)
    D = np.exp(-s * delay)
    Pl = K_I / (P.M * s**2 - K_S)
    return C * Gi * D * E * Pl


def margins(L):
    """Gain crossover, PM, low/high gain margins, Nyquist stability."""
    mag = np.abs(L)
    ph = np.unwrap(np.angle(L))
    ph -= 2 * np.pi * np.round((ph[0] + np.pi) / (2 * np.pi))   # DC phase = -180°
    ph_deg = np.degrees(ph)

    up = np.where(np.diff(np.sign(mag - 1)) != 0)[0]
    f_gc = pm = np.nan
    if up.size:
        k = up[-1]
        f_gc = np.interp(1, [mag[k + 1], mag[k]], [F[k + 1], F[k]])
        pm = np.interp(f_gc, F[k:k + 2], ph_deg[k:k + 2]) + 180

    gm_low = 20 * np.log10(mag[0])          # how far you can turn gain DOWN
    gm_high = f_pc = np.nan                 # how far you can turn gain UP
    above = F > (f_gc if np.isfinite(f_gc) else 0)
    cr = np.where(above[:-1] & (np.diff(np.sign(ph_deg + 180)) != 0))[0]
    if cr.size:
        k = cr[0]
        f_pc = F[k]
        gm_high = -20 * np.log10(mag[k])

    # Nyquist: arg(1+L) from w=0+ to inf; half-turn change -> total encirclements
    a = np.unwrap(np.angle(1 + L))
    n_ccw = int(np.round(2 * (a[-1] - a[0]) / (2 * np.pi)))
    stable = n_ccw == 1                      # P = 1 RHP open-loop pole
    return dict(f_gc=f_gc, pm=pm, gm_low=gm_low, gm_high=gm_high, f_pc=f_pc,
                stable=stable, mag_db=20 * np.log10(mag), ph_deg=ph_deg)


def analyse(kp, kd, d_mm, mur, l_fe, fi, delay_ms, rho, eddy_on=True):
    E = eddy_factor(W, d_mm * 1e-3, mur, l_fe, rho) if eddy_on else np.ones_like(W)
    L_ref = loop(W, kp, kd, fi, delay_ms * 1e-3)
    L = loop(W, kp, kd, fi, delay_ms * 1e-3, E)
    return E, margins(L_ref), margins(L)


# ===========================================================================
# GUI
# ===========================================================================
def launch_gui(snapshot=None):
    import matplotlib
    if snapshot:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.widgets import Slider, RadioButtons, Button

    fig = plt.figure(figsize=(13.5, 8.6))
    fig.canvas.manager.set_window_title("Eddy-Margin Explorer")
    gs = fig.add_gridspec(3, 2, width_ratios=[2.2, 1], height_ratios=[1.3, 1.3, 0.9],
                          left=0.07, right=0.985, top=0.93, bottom=0.36,
                          hspace=0.12, wspace=0.12)
    ax_m = fig.add_subplot(gs[0, 0])
    ax_p = fig.add_subplot(gs[1, 0], sharex=ax_m)
    ax_e = fig.add_subplot(gs[2, 0], sharex=ax_m)
    ax_t = fig.add_subplot(gs[:, 1]); ax_t.axis("off")
    fig.suptitle("How thick yoke slices eat gain crossover and phase margin", fontsize=14)

    for ax in (ax_m, ax_p, ax_e):
        ax.set_xscale("log"); ax.grid(True, which="both", alpha=0.3)
        ax.axvline(F_POLE, color="crimson", ls=":", lw=1.4)
    ax_m.axhline(0, color="gray", ls="--", lw=1)
    ax_p.axhline(-180, color="gray", ls="--", lw=1)
    ax_m.text(F_POLE * 1.05, 0.97, f"RHP pole {F_POLE:.1f} Hz", color="crimson",
              fontsize=8, transform=ax_m.get_xaxis_transform(), va="top")
    ax_m.set_ylabel("|L| [dB]"); ax_p.set_ylabel("∠L [deg]")
    ax_e.set_ylabel("eddy E"); ax_e.set_xlabel("frequency [Hz]")
    ax_m.set_ylim(-40, 40); ax_p.set_ylim(-300, -60); ax_e.set_ylim(0.4, 1.05)
    ax_m.set_xlim(F[0], F[-1])
    plt.setp(ax_m.get_xticklabels(), visible=False)
    plt.setp(ax_p.get_xticklabels(), visible=False)

    (m_ref,) = ax_m.plot([], [], color="#9ca3af", ls="--", lw=1.6, label="no eddy")
    (m_ed,) = ax_m.plot([], [], color="#2563eb", lw=2, label="with eddy")
    (p_ref,) = ax_p.plot([], [], color="#9ca3af", ls="--", lw=1.6)
    (p_ed,) = ax_p.plot([], [], color="#2563eb", lw=2)
    (e_mag,) = ax_e.plot([], [], color="#0f766e", lw=2, label="|E|  (magnitude)")
    ax_e2 = ax_e.twinx(); ax_e2.set_ylim(-25, 1); ax_e2.set_ylabel("∠E [deg]")
    (e_ph,) = ax_e2.plot([], [], color="#b45309", lw=1.6, label="∠E  (lag)")
    gc_ref = ax_m.axvline(1, color="#9ca3af", ls="-.", lw=1)
    gc_ed = ax_m.axvline(1, color="#16a34a", ls="-.", lw=1.4)
    pm_ref = ax_p.vlines(1, -180, -180, color="#9ca3af", lw=5, alpha=0.5)
    pm_ed = ax_p.vlines(1, -180, -180, color="#16a34a", lw=3)
    ax_m.legend(loc="upper right", fontsize=8)
    ax_e.legend(loc="lower left", fontsize=8); ax_e2.legend(loc="lower center", fontsize=8)
    txt = ax_t.text(0, 1, "", va="top", ha="left", family="monospace", fontsize=9.6,
                    transform=ax_t.transAxes)

    def _ax(col, row):
        return fig.add_axes([0.10 + col * 0.42, 0.265 - row * 0.05, 0.20, 0.028])

    s_kp = Slider(_ax(0, 0), "Kp [A/m]", 2000, 80000, valinit=KP0, valstep=500)
    s_kd = Slider(_ax(0, 1), "Kd [A·s/m]", 0, 2000, valinit=KD0, valstep=10)
    s_fi = Slider(_ax(0, 2), "inner BW [Hz]", 50, 3000, valinit=FI0, valstep=10)
    s_dl = Slider(_ax(0, 3), "delay [ms]", 0, 2.0, valinit=DELAY0_MS, valstep=0.05)
    s_d = Slider(_ax(1, 0), "slice d", np.log10(0.3), np.log10(40),
                 valinit=np.log10(D0_MM))
    s_mu = Slider(_ax(1, 1), "μr (incremental)", 50, 2000, valinit=MUR0, valstep=10)
    s_lf = Slider(_ax(1, 2), "l_Fe [m]", 0.05, 0.8, valinit=LFE0, valstep=0.01)
    radio = RadioButtons(fig.add_axes([0.80, 0.19, 0.17, 0.09]), list(RHO), active=0)

    presets = {
        '1" slices (now)': (25.4, 0),
        '1/16" mild': (1.6, 0),
        "0.5 mm Si": (0.5, 1),
    }
    btns = []
    for k, (name, (dmm, ri)) in enumerate(presets.items()):
        b = Button(fig.add_axes([0.80, 0.135 - k * 0.045, 0.17, 0.038]), name)
        def _cb(_evt, dmm=dmm, ri=ri):
            radio.set_active(ri); s_d.set_val(np.log10(dmm))
        b.on_clicked(_cb); btns.append(b)

    def _pm_bar(coll, f, pm, ph):
        if np.isfinite(f):
            y = np.interp(f, F, ph)
            coll.set_segments([[[f, -180], [f, y]]])
        else:
            coll.set_segments([])

    def update(_=None):
        d_mm = 10 ** s_d.val
        s_d.valtext.set_text(f"{d_mm:.2f} mm")
        rho = RHO[radio.value_selected]
        E, a, b = analyse(s_kp.val, s_kd.val, d_mm, s_mu.val, s_lf.val,
                          s_fi.val, s_dl.val, rho)
        m_ref.set_data(F, a["mag_db"]); m_ed.set_data(F, b["mag_db"])
        p_ref.set_data(F, a["ph_deg"]); p_ed.set_data(F, b["ph_deg"])
        e_mag.set_data(F, np.abs(E)); e_ph.set_data(F, np.degrees(np.angle(E)))
        for line, r in ((gc_ref, a), (gc_ed, b)):
            line.set_xdata([r["f_gc"]] * 2 if np.isfinite(r["f_gc"]) else [np.nan] * 2)
        _pm_bar(pm_ref, a["f_gc"], a["pm"], a["ph_deg"])
        _pm_bar(pm_ed, b["f_gc"], b["pm"], b["ph_deg"])

        Egc = eddy_factor(np.array([2 * np.pi * a["f_gc"]]), d_mm * 1e-3, s_mu.val,
                          s_lf.val, rho)[0] if np.isfinite(a["f_gc"]) else np.nan
        share = (s_lf.val / s_mu.val) / (2 * P.S0 + P.L_PM / P.MU_REC + s_lf.val / s_mu.val)

        def row(k, fmt, unit=""):
            va, vb = a[k], b[k]
            dv = vb - va if np.isfinite(va) and np.isfinite(vb) else np.nan
            return f"{fmt.format(va):>8} {fmt.format(vb):>8} {fmt.format(dv):>8} {unit}"

        txt.set_text(
            f"slice d = {d_mm:6.2f} mm   iron share = {share * 100:.2f} %\n"
            f"Kp·k_i/k_s = {s_kp.val * K_I / K_S:.2f}  (must be > 1)\n\n"
            f"{'':12}{'no eddy':>8} {'eddy':>8} {'Δ':>8}\n"
            f"{'f_gc':12}{row('f_gc', '{:.1f}', 'Hz')}\n"
            f"{'PM':12}{row('pm', '{:.1f}', '°')}\n"
            f"{'GM (down)':12}{row('gm_low', '{:.1f}', 'dB')}\n"
            f"{'GM (up)':12}{row('gm_high', '{:.1f}', 'dB')}\n"
            f"{'stable':12}{str(a['stable']):>8} {str(b['stable']):>8}\n\n"
            f"E at old crossover:\n"
            f"  |E| = {abs(Egc):.3f}  ({20 * np.log10(abs(Egc)):+.2f} dB)\n"
            f"  ∠E  = {np.degrees(np.angle(Egc)):+.1f}°\n\n"
            "Read it like this:\n"
            " |E|<1 → whole |L| curve sinks\n"
            "   → crossover slides left\n"
            "   → toward the RHP pole.\n"
            " ∠E<0 → phase curve sinks\n"
            "   → PM shrinks directly.\n"
            " GM(down) = how much gain\n"
            "   you can LOSE before the\n"
            "   negative spring wins.\n"
            " Green bar = phase margin.\n")
        fig.canvas.draw_idle()

    for s in (s_kp, s_kd, s_fi, s_dl, s_d, s_mu, s_lf):
        s.on_changed(update)
    radio.on_clicked(update)
    update()

    if snapshot:
        fig.savefig(snapshot, dpi=130)
        print(f"saved {snapshot}")
        return 0
    plt.show()
    return 0


# ===========================================================================
# Self-test: numeric margins/stability agree with python-control (no eddy)
# ===========================================================================
def selftest():
    import control
    ok = True
    s = control.tf("s")
    print(f"k_i = {K_I:.1f} N/A   k_s = {K_S:.0f} N/m   RHP pole = {F_POLE:.2f} Hz")
    for kp in (5000.0, 12000.0, KP0, 60000.0):
        L_tf = ((kp + KD0 * s / (TAU_D * s + 1)) / (s / (2 * np.pi * FI0) + 1)
                * K_I / (P.M * s**2 - K_S))
        cl_stable = bool(np.all(control.poles(control.feedback(L_tf, 1)).real < 0))
        _, pm_tf, _, _ = control.margin(L_tf)
        r = margins(loop(W, kp, KD0, FI0, 0.0))
        agree = (r["stable"] == cl_stable) and (not cl_stable or abs(r["pm"] - pm_tf) < 1.0)
        ok &= agree
        print(f"Kp={kp:7.0f}  stable(nyq)={r['stable']!s:5}  stable(poles)={cl_stable!s:5}  "
              f"PM={r['pm']:6.1f}° vs {pm_tf:6.1f}°  {'OK' if agree else 'MISMATCH'}")

    print("\nPM cost of slice thickness (1018, μr=500, l_Fe=0.33 m, defaults):")
    for d in (25.4, 3.2, 1.6, 0.76):
        _, a, b = analyse(KP0, KD0, d, MUR0, LFE0, FI0, DELAY0_MS, RHO["1018 (15.9 µΩ·cm)"])
        print(f"  d={d:5.2f} mm  f_gc {a['f_gc']:6.1f}→{b['f_gc']:6.1f} Hz   "
              f"PM {a['pm']:5.1f}→{b['pm']:5.1f}°")
    print("\nselftest", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--snapshot", metavar="PATH")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(selftest())
    sys.exit(launch_gui(snapshot=args.snapshot))

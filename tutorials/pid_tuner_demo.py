"""
Interactive PID Tuner — single-yoke maglev gap loop (interview demo)
===================================================================

A live, knob-turnable version of the Layer-3 nested loop, built so a candidate
can develop *intuition* for tuning an open-loop-unstable plant in ~10 minutes
without being defeated by it.

Reuses the existing single source of truth: `maglev.params`, `maglev.plant`,
`maglev.controllers`. No physics is redefined here.

WHAT THE CANDIDATE SEES
    Outer PID on gap height -> i_ref -> inner PI current loop -> nonlinear plant.
    The inner loop is pre-tuned and hidden (it is not what we are testing).
    They turn Kp / Ki / Kd, move the set-point, kick the pod, and watch.

--------------------------------------------------------------------------
THE RUNAWAY GUARDS (the point of this file)
--------------------------------------------------------------------------
The bare plant is unstable, so any arbitrary gain set ends in the pod either
slamming shut or falling away forever. Either way the trace leaves the screen
and the candidate learns nothing. Two hard mechanical stops keep every attempt
on-screen and recoverable:

  X_BLOCK = 2.0 mm   mechanical block. Stands in for the physical hard stop that
                     prevents the magnet from sticking to the track. Inelastic:
                     position clamps, closing velocity is killed.

  X_CATCH = 3.6 mm   droop stop / catch net. Bounds the fall.

X_CATCH is NOT arbitrary, and it is the one number here that must not be raised
casually. With the shipped params.py:

    PM alone holds the load at ......... 3.10 mm   (zero-power point)
    Full +5 A holds the load out to .... 3.78 mm   <-- hard physical ceiling
    Beyond that, NO current recovers it.

So the catch must sit *inside* 3.78 mm or resting on it becomes a dead state and
the demo stumps rather than teaches. 3.6 mm leaves ~0.2 mm of margin. If you
raise I_MAX the ceiling moves and the catch can follow:

    I_MAX =  5 A -> ceiling 3.78 mm   (faithful to params.py)
    I_MAX = 15 A -> ceiling 5.15 mm   (forgiving; use for nervous candidates)

Both stops are self-correcting rather than sticky: resting on the block drives
the error negative (current down, pod falls off it), resting on the catch drives
it positive (current up, pod lifts). Nobody gets wedged.

--------------------------------------------------------------------------
THE TEACHING MOMENT
--------------------------------------------------------------------------
Kp must exceed k_s/k_i ~ 7340 A/m *just to make the closed-loop stiffness
positive*. Below that threshold no amount of Kd or Ki helps -- it sits on a stop.
That threshold is drawn on the Kp slider and printed in the readout, because
discovering it is the single most valuable thing a candidate can take away.

Run:
    python3 pid_tuner_demo.py              # interactive GUI
    python3 pid_tuner_demo.py --selftest   # headless; verifies guards + presets
"""

import argparse
import sys
from collections import deque

import numpy as np

from maglev import params as P
from maglev.plant import equilibrium_current, inductance
from maglev.linearization import compute_stiffnesses, unstable_pole_hz
from maglev.controllers import PICurrentLoop, PIDPositionLoop

# ---------------------------------------------------------------------------
# Mechanical guards -- see module docstring before changing X_CATCH
# ---------------------------------------------------------------------------
X_BLOCK = 2.0e-3          # mechanical block  [m]  (magnet cannot stick)
X_CATCH = 3.6e-3          # droop stop        [m]  (must stay < lift ceiling)
RESTITUTION = 0.0         # inelastic stops: no chaotic bouncing

# Gap where the PM alone carries the load (i_eq = 0). With Ki=0 the P-only
# steady-state droop is exactly zero here and grows either side -- a good thing
# to let a candidate discover for themselves.
ZERO_POWER_GAP = 3.10e-3  # [m]

# ---------------------------------------------------------------------------
# Loop rates. Lower than layer3 (200 kHz) so the GUI can run in real time;
# still >> the 2 kHz outer loop, so the physics is unchanged in any way that
# matters here.
# ---------------------------------------------------------------------------
FS_PLANT = 50e3;  DT_PLANT = 1.0 / FS_PLANT
FS_INNER = 10e3;  N_INNER = int(FS_PLANT / FS_INNER)
FS_OUTER = 2e3;   N_OUTER = int(FS_PLANT / FS_OUTER)

TAU_D = 1e-3              # derivative filter time constant
INNER_BW_HZ = 1000.0      # pre-tuned inner current loop bandwidth

# Known-good outer gains from layer3_siso_stabilizer.py
GOOD_KP, GOOD_KI, GOOD_KD = 25000.0, 0.0, 600.0

# ---------------------------------------------------------------------------
# Yoke cross-section geometry [inches] -- from Vault/docs/rfcs/Diagram_1.png.
# Consistent with params.py: 1"x1" pole face -> A = 6.45e-4 m^2, and
# 1" of PM per leg x 2 legs -> L_PM = 2 x 0.0254 m.
# ---------------------------------------------------------------------------
YK_W = 5.0                # overall width
YK_BASE_H = 1.5           # steel base height
YK_LEG_W = 1.0            # leg width  (= pole face width)
YK_STEEL_BOT = 0.5        # leg: steel below the PM
YK_PM = 1.0               # leg: PM block
YK_STEEL_TOP = 0.5        # leg: steel above the PM (the pole face)
YK_TOP = YK_BASE_H + YK_STEEL_BOT + YK_PM + YK_STEEL_TOP   # 3.5"
YK_EXTRUSION = 1.0        # cross-section depth
GAP_EXAG = 5.0            # air gap drawn x5 so motion is visible

C_STEEL = "#1b6b8a"
C_PM = "#e87a30"
C_RAIL = "#4b5563"

TRACE_SECONDS = 1.2       # rolling window shown on the plot
DEFAULT_SPEED = 0.25      # slow-mo: the 4.3 Hz pole is a blur at 1.0x

# Slider ranges
KP_RANGE = (0.0, 80000.0)
KI_RANGE = (0.0, 200000.0)
KD_RANGE = (0.0, 3000.0)
NOISE_RANGE_UM = (0.0, 10.0)

# Precomputed scalars for the tight integration loop
_MU0A = P.MU0 * P.A
_N = P.N
_MMF = P.MMF_PM
_R0 = P.R0
_RC = P.R_COIL
_M = P.M
_G = P.G


def _force(i, x):
    """Attractive force [N]. Scalar inline copy of plant.force for loop speed."""
    R = 2.0 * x / _MU0A + _R0
    phi = (_N * i + _MMF) / R
    return phi * phi / _MU0A


def _induct(x):
    R = 2.0 * x / _MU0A + _R0
    return _N * _N / R


class Sim:
    """Nested-loop maglev sim with mechanical stops and live-tunable outer PID."""

    def __init__(self, i_max=P.I_MAX):
        self.k_i, self.k_s = compute_stiffnesses(P.S0)
        self.kp_threshold = self.k_s / self.k_i      # the teaching number
        self.pole_hz = unstable_pole_hz()
        self.i_max = i_max

        self.x_ref = P.S0
        self.noise_m = 0.5e-6
        self.speed = DEFAULT_SPEED

        self.kp, self.ki, self.kd = GOOD_KP, GOOD_KI, GOOD_KD
        self._build_controllers()
        self.reset()

    # -- setup -------------------------------------------------------------
    def _build_controllers(self):
        L0 = inductance(P.S0)
        w = 2 * np.pi * INNER_BW_HZ
        self.inner = PICurrentLoop(Kp=w * L0, Ki=w * _RC,
                                   dt=1 / FS_INNER, i_max=self.i_max)
        self.outer = PIDPositionLoop(self.kp, self.ki, self.kd,
                                     dt=1 / FS_OUTER, tau=TAU_D,
                                     i_max=self.i_max)

    def set_gains(self, kp, ki, kd):
        self.kp, self.ki, self.kd = kp, ki, kd
        self.outer.Kp, self.outer.Ki, self.outer.Kd = kp, ki, kd

    def set_i_max(self, i_max):
        self.i_max = i_max
        self.inner.i_max = i_max
        self.outer.i_max = i_max

    def reset(self):
        """Drop the pod from just below the set-point, coil at its bias current."""
        self.x = min(self.x_ref * 1.10, X_CATCH - 1e-5)
        self.xdot = 0.0
        self.i = equilibrium_current(P.S0)
        self.v = _RC * self.i
        self.i_ref = self.i
        self.t = 0.0
        self.k = 0
        self.F_dist = 0.0
        self._dist_until = -1.0

        self.inner.reset()
        self.outer.reset()

        n = int(TRACE_SECONDS * FS_OUTER)
        self.log_t = deque(maxlen=n)
        self.log_x = deque(maxlen=n)
        self.log_i = deque(maxlen=n)
        self.log_ref = deque(maxlen=n)

        self.n_block = 0
        self.n_catch = 0
        self.on_stop = False
        self._sat_hits = 0
        self._sat_total = 0
        self._err_sq = deque(maxlen=n)

    def kick(self, newtons=25.0, duration=0.02):
        """Impulse-ish downward (gap-opening) payload force -- 'now disturb it'."""
        self.F_dist = newtons
        self._dist_until = self.t + duration

    # -- integration -------------------------------------------------------
    def advance(self, sim_dt):
        """
        Advance by exactly `sim_dt` seconds of SIMULATED time.

        Deliberately honours the full request -- no internal cap. The GUI is
        responsible for clamping a stalled frame before calling (see redraw);
        capping in here silently truncates programmatic callers, which is how
        the self-test once "settled" at 50 ms and reported nonsense.
        """
        for _ in range(int(max(0.0, sim_dt) * FS_PLANT)):
            self._step()

    def _step(self):
        dt = DT_PLANT

        if self.t >= self._dist_until:
            self.F_dist = 0.0

        # --- outer gap loop (2 kHz) --------------------------------------
        if self.k % N_OUTER == 0:
            x_meas = self.x + (np.random.normal(0.0, self.noise_m)
                               if self.noise_m > 0 else 0.0)
            # SIGN FLIP at the sim<->controller boundary (plant.py convention)
            dz_ref = P.S0 - self.x_ref
            dz_meas = P.S0 - x_meas
            self.i_ref = self.outer.update(dz_ref, dz_meas)

            self.log_t.append(self.t)
            self.log_x.append(self.x)
            self.log_i.append(self.i)
            self.log_ref.append(self.x_ref)
            self._err_sq.append((self.x - self.x_ref) ** 2)
            self._sat_total += 1
            if abs(self.i_ref) >= self.i_max * 0.999:
                self._sat_hits += 1

        # --- inner current loop (10 kHz) ---------------------------------
        if self.k % N_INNER == 0:
            self.v = self.inner.update(self.i_ref, self.i)

        # --- plant RK4 (scalar, for speed) -------------------------------
        Fd, v = self.F_dist, self.v

        def deriv(x, xd, i):
            xc = x if x > 1e-5 else 1e-5
            return xd, (_M * _G + Fd - _force(i, xc)) / _M, (v - _RC * i) / _induct(xc)

        x0, v0, i0 = self.x, self.xdot, self.i
        a1, b1, c1 = deriv(x0, v0, i0)
        a2, b2, c2 = deriv(x0 + .5 * dt * a1, v0 + .5 * dt * b1, i0 + .5 * dt * c1)
        a3, b3, c3 = deriv(x0 + .5 * dt * a2, v0 + .5 * dt * b2, i0 + .5 * dt * c2)
        a4, b4, c4 = deriv(x0 + dt * a3, v0 + dt * b3, i0 + dt * c3)

        self.x += dt / 6 * (a1 + 2 * a2 + 2 * a3 + a4)
        self.xdot += dt / 6 * (b1 + 2 * b2 + 2 * b3 + b4)
        self.i += dt / 6 * (c1 + 2 * c2 + 2 * c3 + c4)

        self._apply_stops()

        self.t += dt
        self.k += 1

    def _apply_stops(self):
        """
        Inelastic mechanical stops -- the runaway guards.

        Counters record contact EVENTS (transitions into a stop), not timesteps
        spent resting on one; the latter reads in the tens of thousands and is
        useless as a tuning signal.
        """
        was_on = self.on_stop
        self.on_stop = False
        if self.x <= X_BLOCK:                 # magnet tried to stick
            self.x = X_BLOCK
            if self.xdot < 0.0:               # moving further closed
                self.xdot = -self.xdot * RESTITUTION
            if not was_on:
                self.n_block += 1
            self.on_stop = True
        elif self.x >= X_CATCH:               # fell onto the droop stop
            self.x = X_CATCH
            if self.xdot > 0.0:
                self.xdot = -self.xdot * RESTITUTION
            if not was_on:
                self.n_catch += 1
            self.on_stop = True

    # -- readout -----------------------------------------------------------
    RMS_WINDOW = int(0.4 * FS_OUTER)      # judge the last 0.4 s, not the transient

    def metrics(self):
        recent = list(self._err_sq)[-self.RMS_WINDOW:]
        rms_um = (np.sqrt(np.mean(recent)) * 1e6) if recent else 0.0
        sat_pct = 100.0 * self._sat_hits / self._sat_total if self._sat_total else 0.0
        return dict(
            gap_mm=self.x * 1e3,
            err_um=(self.x - self.x_ref) * 1e6,
            rms_um=rms_um,
            i_a=self.i,
            sat_pct=sat_pct,
            n_block=self.n_block,
            n_catch=self.n_catch,
            verdict=self._verdict(rms_um),
        )

    def _verdict(self, rms_um):
        if self.kp < self.kp_threshold:
            return ("NOT STABILIZING  (Kp below threshold)", "#dc2626")
        if self.on_stop:
            return ("ON A STOP  (would have run away)", "#dc2626")
        if len(self._err_sq) < int(0.3 * FS_OUTER):
            return ("settling...", "#6b7280")
        if rms_um < 15:
            return ("STABLE  (tight)", "#16a34a")
        if rms_um < 80:
            return ("STABLE  (loose)", "#ca8a04")
        return ("OSCILLATING", "#ea580c")


def _draw_yoke(ax):
    """
    Static yoke cross-section. Returns the handles that move with the sim:
    (rail patch, gap-dimension line, gap label).
    """
    from matplotlib.patches import Circle, Rectangle

    def rect(x, y, w, h, color, z=2):
        ax.add_patch(Rectangle((x, y), w, h, facecolor=color,
                               edgecolor="#0f172a", lw=1.2, zorder=z))

    # base
    rect(0, 0, YK_W, YK_BASE_H, C_STEEL)
    # two legs: steel / PM / steel
    for x0 in (0.0, YK_W - YK_LEG_W):
        y = YK_BASE_H
        rect(x0, y, YK_LEG_W, YK_STEEL_BOT, C_STEEL);           y += YK_STEEL_BOT
        rect(x0, y, YK_LEG_W, YK_PM, C_PM);                     y += YK_PM
        rect(x0, y, YK_LEG_W, YK_STEEL_TOP, C_STEEL)

    ax.text(YK_W / 2, YK_BASE_H / 2, "Steel (1018)", ha="center", va="center",
            color="white", fontsize=8.5)
    ax.text(YK_LEG_W / 2, YK_BASE_H + YK_STEEL_BOT + YK_PM / 2, "PM",
            ha="center", va="center", color="white", fontsize=8.5, fontweight="bold")
    ax.text(YK_W - YK_LEG_W / 2, YK_BASE_H + YK_STEEL_BOT + YK_PM / 2, "PM",
            ha="center", va="center", color="white", fontsize=8.5, fontweight="bold")

    # coil bundles flanking each leg (wire cross-sections), N turns from params
    for x0 in (0.0, YK_W - YK_LEG_W):
        for xc in (x0 - 0.17, x0 + YK_LEG_W + 0.17):
            for k in range(5):
                ax.add_patch(Circle((xc, YK_BASE_H + 0.28 + 0.34 * k), 0.115,
                                    facecolor="#b45309", edgecolor="#0f172a",
                                    lw=0.7, zorder=3))
    ax.text(YK_W / 2, -0.95,
            f"coil {P.N} turns/leg   ·   {YK_EXTRUSION:.0f}\" extrusion   ·   "
            f"pole face {YK_LEG_W:.0f}\"×{YK_EXTRUSION:.0f}\"",
            ha="center", va="top", fontsize=7.5, color="#475569")

    # rail (moves with the gap)
    rail = Rectangle((-0.55, YK_TOP), YK_W + 1.10, 0.55, facecolor=C_RAIL,
                     edgecolor="#0f172a", lw=1.2, zorder=5)
    ax.add_patch(rail)
    rail_lbl = ax.text(YK_W / 2, YK_TOP + 0.27, "track", ha="center", va="center",
                       color="white", fontsize=8, zorder=6)

    x_gap = YK_W - YK_LEG_W / 2          # over the right pole face
    gap_line = ax.annotate("", xy=(x_gap, YK_TOP), xytext=(x_gap, YK_TOP),
                           arrowprops=dict(arrowstyle="<->", color="#dc2626", lw=1.4),
                           zorder=7)
    gap_lbl = ax.text(x_gap + 0.2, YK_TOP, "", ha="left", va="center",
                      fontsize=8.5, color="#dc2626", fontweight="bold", zorder=7)

    # dimensions down the left edge
    for y0, h, lab in ((0, YK_BASE_H, f'{YK_BASE_H}"'),
                       (YK_BASE_H, YK_STEEL_BOT, f'{YK_STEEL_BOT}"'),
                       (YK_BASE_H + YK_STEEL_BOT, YK_PM, f'{YK_PM}"'),
                       (YK_BASE_H + YK_STEEL_BOT + YK_PM, YK_STEEL_TOP, f'{YK_STEEL_TOP}"')):
        ax.annotate("", xy=(-0.75, y0), xytext=(-0.75, y0 + h),
                    arrowprops=dict(arrowstyle="<->", color="#64748b", lw=0.9))
        ax.text(-0.88, y0 + h / 2, lab, ha="right", va="center",
                fontsize=7.5, color="#475569")
    ax.annotate("", xy=(0, -0.42), xytext=(YK_W, -0.42),
                arrowprops=dict(arrowstyle="<->", color="#64748b", lw=0.9))
    ax.text(YK_W / 2, -0.60, f'{YK_W:.0f}"', ha="center", va="top",
            fontsize=7.5, color="#475569")

    ax.set_xlim(-1.9, YK_W + 1.75)
    ax.set_ylim(-1.5, YK_TOP + 1.5)
    ax.set_aspect("equal")
    ax.axis("off")
    return rail, rail_lbl, gap_line, gap_lbl


# ===========================================================================
# GUI
# ===========================================================================
def launch_gui(snapshot=None):
    import matplotlib.pyplot as plt
    from matplotlib.widgets import Slider, Button, RadioButtons

    sim = Sim()

    fig = plt.figure(figsize=(13.5, 8.4))
    fig.canvas.manager.set_window_title("Maglev PID Tuner — single yoke")
    gs = fig.add_gridspec(2, 2, width_ratios=[2.05, 1.6], height_ratios=[2, 1],
                          left=0.065, right=0.985, top=0.93, bottom=0.37,
                          hspace=0.28, wspace=0.10)

    ax_gap = fig.add_subplot(gs[0, 0])
    ax_cur = fig.add_subplot(gs[1, 0], sharex=ax_gap)
    ax_yoke = fig.add_subplot(gs[0, 1])
    ax_txt = fig.add_subplot(gs[1, 1]); ax_txt.axis("off")

    rail, rail_lbl, gap_line, gap_lbl = _draw_yoke(ax_yoke)
    ax_yoke.set_title("yoke cross-section  ·  air gap ×5", fontsize=9, color="#374151")

    fig.suptitle("Single-yoke maglev — tune the gap loop", fontsize=14, y=0.975)

    # --- gap axis ---------------------------------------------------------
    ax_gap.axhspan(0, X_BLOCK * 1e3, color="#dc2626", alpha=0.13, zorder=0)
    ax_gap.axhspan(X_CATCH * 1e3, 5.0, color="#f59e0b", alpha=0.13, zorder=0)
    ax_gap.axhline(X_BLOCK * 1e3, color="#dc2626", lw=2)
    ax_gap.axhline(X_CATCH * 1e3, color="#f59e0b", lw=2)
    ax_gap.text(0.995, X_BLOCK * 1e3 - 0.06, "mechanical block (magnet sticks)",
                transform=ax_gap.get_yaxis_transform(), ha="right", va="top",
                fontsize=8, color="#dc2626")
    ax_gap.text(0.995, X_CATCH * 1e3 + 0.06, "droop stop (catch)",
                transform=ax_gap.get_yaxis_transform(), ha="right", va="bottom",
                fontsize=8, color="#b45309")

    ax_gap.axhline(ZERO_POWER_GAP * 1e3, color="#0f766e", ls=":", lw=1.2,
                   label="zero-power gap")
    (ln_gap,) = ax_gap.plot([], [], lw=1.8, color="#2563eb", label="gap")
    (ln_ref,) = ax_gap.plot([], [], lw=1.3, ls="--", color="#16a34a", label="set-point")
    ax_gap.set_ylim(X_BLOCK * 1e3 - 0.25, X_CATCH * 1e3 + 0.25)
    ax_gap.set_ylabel("air gap [mm]")
    ax_gap.grid(alpha=0.3)
    ax_gap.legend(loc="upper left", fontsize=7.5, ncol=3)

    # --- current axis -----------------------------------------------------
    (ln_cur,) = ax_cur.plot([], [], lw=1.5, color="#7c3aed")
    lim_hi = ax_cur.axhline(sim.i_max, color="#dc2626", ls=":", lw=1.2)
    lim_lo = ax_cur.axhline(-sim.i_max, color="#dc2626", ls=":", lw=1.2)
    ax_cur.set_ylim(-sim.i_max * 1.25, sim.i_max * 1.25)
    ax_cur.set_ylabel("coil current [A]")
    ax_cur.set_xlabel("time [s]")
    ax_cur.grid(alpha=0.3)

    txt = ax_txt.text(0.0, 1.0, "", va="top", ha="left", fontsize=10.5,
                      family="monospace", transform=ax_txt.transAxes)
    # anchored to the BOTTOM of the panel so it can never collide with the
    # readout above it, whatever length that grows to
    verdict_txt = ax_txt.text(0.0, 0.02, "", va="bottom", ha="left", fontsize=11.5,
                              family="monospace", fontweight="bold",
                              transform=ax_txt.transAxes)

    # --- sliders ----------------------------------------------------------
    def _ax(y, h=0.030):
        return fig.add_axes([0.155, y, 0.335, h])

    s_kp = Slider(_ax(0.205), "Kp  [A/m]", *KP_RANGE, valinit=GOOD_KP, valstep=250)
    s_ki = Slider(_ax(0.160), "Ki  [A/(m·s)]", *KI_RANGE, valinit=GOOD_KI, valstep=500)
    s_kd = Slider(_ax(0.115), "Kd  [A/(m/s)]", *KD_RANGE, valinit=GOOD_KD, valstep=10)
    s_sp = Slider(_ax(0.070), "set-point [mm]",
                  (X_BLOCK + 0.3e-3) * 1e3, (X_CATCH - 0.3e-3) * 1e3,
                  valinit=P.S0 * 1e3, valstep=0.05)
    s_nz = Slider(_ax(0.025), "sensor noise [µm]", *NOISE_RANGE_UM,
                  valinit=0.5, valstep=0.25)

    # the threshold marker -- the single most useful thing on screen
    s_kp.ax.axvline(sim.kp_threshold, color="#dc2626", lw=2.0, zorder=5)
    s_kp.ax.annotate("Kp must exceed this to stabilize at all",
                     xy=(sim.kp_threshold, 0.5), xycoords=("data", "axes fraction"),
                     xytext=(10, 15), textcoords="offset points",
                     fontsize=8, color="#dc2626",
                     arrowprops=dict(arrowstyle="->", color="#dc2626", lw=1.1))

    s_speed = Slider(fig.add_axes([0.635, 0.070, 0.145, 0.030]),
                     "sim speed ×", 0.05, 1.0, valinit=DEFAULT_SPEED, valstep=0.05)

    # --- buttons ----------------------------------------------------------
    b_run = Button(fig.add_axes([0.60, 0.205, 0.10, 0.045]), "Pause")
    b_reset = Button(fig.add_axes([0.715, 0.205, 0.10, 0.045]), "Reset")
    b_kick = Button(fig.add_axes([0.83, 0.205, 0.10, 0.045]), "Kick ↓")
    b_good = Button(fig.add_axes([0.60, 0.145, 0.155, 0.045]), "Load good tune")
    b_zero = Button(fig.add_axes([0.775, 0.145, 0.155, 0.045]), "Zero gains")

    radio = RadioButtons(fig.add_axes([0.845, 0.025, 0.115, 0.075]),
                         ("5 A  faithful", "15 A  forgiving"), active=0)
    fig.text(0.845, 0.107, "drive limit", fontsize=8.5, color="#374151")

    state = {"running": True}

    def on_gain(_):
        sim.set_gains(s_kp.val, s_ki.val, s_kd.val)

    def on_sp(_):
        sim.x_ref = s_sp.val * 1e-3

    def on_noise(_):
        sim.noise_m = s_nz.val * 1e-6

    def on_speed(_):
        sim.speed = s_speed.val

    for s, cb in ((s_kp, on_gain), (s_ki, on_gain), (s_kd, on_gain),
                  (s_sp, on_sp), (s_nz, on_noise), (s_speed, on_speed)):
        s.on_changed(cb)

    def on_run(_):
        state["running"] = not state["running"]
        b_run.label.set_text("Pause" if state["running"] else "Run")

    def on_reset(_):
        sim.reset()

    def on_kick(_):
        sim.kick()

    def on_good(_):
        s_kp.set_val(GOOD_KP); s_ki.set_val(GOOD_KI); s_kd.set_val(GOOD_KD)
        sim.reset()

    def on_zero(_):
        s_kp.set_val(0.0); s_ki.set_val(0.0); s_kd.set_val(0.0)
        sim.reset()

    def on_radio(label):
        sim.set_i_max(15.0 if label.startswith("15") else P.I_MAX)
        for ln, sgn in ((lim_hi, 1), (lim_lo, -1)):
            ln.set_ydata([sgn * sim.i_max] * 2)
        ax_cur.set_ylim(-sim.i_max * 1.25, sim.i_max * 1.25)
        sim.reset()

    b_run.on_clicked(on_run); b_reset.on_clicked(on_reset)
    b_kick.on_clicked(on_kick); b_good.on_clicked(on_good)
    b_zero.on_clicked(on_zero); radio.on_clicked(on_radio)

    def redraw():
        if state["running"]:
            # clamp a stalled frame here, then scale into sim time
            sim.advance(min(1 / 30.0, 0.05) * sim.speed)

        if sim.log_t:
            t = np.fromiter(sim.log_t, float)
            ln_gap.set_data(t, np.fromiter(sim.log_x, float) * 1e3)
            ln_ref.set_data(t, np.fromiter(sim.log_ref, float) * 1e3)
            ln_cur.set_data(t, np.fromiter(sim.log_i, float))
            ax_gap.set_xlim(max(0.0, t[-1] - TRACE_SECONDS), max(TRACE_SECONDS, t[-1]))

        m = sim.metrics()
        txt.set_text(
            f"LIVE\n"
            f"  gap           {m['gap_mm']:8.3f} mm\n"
            f"  error         {m['err_um']:+8.0f} µm\n"
            f"  RMS error     {m['rms_um']:8.0f} µm\n"
            f"  coil current  {m['i_a']:+8.2f} A\n"
            f"  saturated     {m['sat_pct']:8.1f} %\n"
        )

        # yoke: rail rides the (exaggerated) live gap
        vis = sim.x * 1e3 / 25.4 * GAP_EXAG
        rail.set_y(YK_TOP + vis)
        rail_lbl.set_y(YK_TOP + vis + 0.27)
        rail.set_facecolor("#b91c1c" if sim.on_stop else C_RAIL)
        x_gap = YK_W - YK_LEG_W / 2
        gap_line.set_position((x_gap, YK_TOP + vis))
        gap_line.xy = (x_gap, YK_TOP)
        gap_lbl.set_position((x_gap + 0.2, YK_TOP + vis / 2))
        gap_lbl.set_text(f"{m['gap_mm']:.2f} mm")

        label, color = m["verdict"]
        verdict_txt.set_text(label)
        verdict_txt.set_color(color)
        fig.canvas.draw_idle()

    timer = fig.canvas.new_timer(interval=33)
    timer.add_callback(redraw)
    timer.start()

    print(f"unstable pole {sim.pole_hz:.2f} Hz | Kp threshold {sim.kp_threshold:.0f} A/m "
          f"| guards {X_BLOCK*1e3:.1f}–{X_CATCH*1e3:.1f} mm")

    if snapshot:                       # headless layout preview
        timer.stop()
        sim.advance(0.35); sim.kick(); sim.advance(0.55)
        redraw()
        fig.savefig(snapshot, dpi=110)
        print(f"saved {snapshot}")
        return
    plt.show()


# ===========================================================================
# Headless self-test
# ===========================================================================
def selftest():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}{'  ' + detail if detail else ''}")

    print("Guards vs. physics")
    from scipy.optimize import brentq
    ceiling = brentq(lambda x: _force(P.I_MAX, x) - _M * _G, 0.5e-3, 30e-3)
    check("catch inside lift ceiling", X_CATCH < ceiling,
          f"catch {X_CATCH*1e3:.2f} mm < ceiling {ceiling*1e3:.2f} mm")
    check("block below set-point", X_BLOCK < P.S0 < X_CATCH)

    print("\nGood tune holds the gap")
    s = Sim(); s.set_gains(GOOD_KP, GOOD_KI, GOOD_KD); s.noise_m = 0.0
    s.advance(2.0)
    m = s.metrics()
    check("stays off both stops", not s.on_stop)
    # Ki=0 leaves a genuine P-only droop; it is physics, not a tuning failure.
    check("droop < 100 µm", abs(m["err_um"]) < 100, f"{m['err_um']:+.1f} µm")

    print("\nP-only droop vanishes at the zero-power gap (3.10 mm)")
    s = Sim(); s.set_gains(GOOD_KP, 0.0, GOOD_KD); s.noise_m = 0.0
    s.x_ref = ZERO_POWER_GAP; s.reset(); s.advance(2.0)
    check("|error| < 5 µm at zero-power point",
          abs((s.x - s.x_ref) * 1e6) < 5, f"{(s.x - s.x_ref) * 1e6:+.1f} µm")

    print("\nIntegral action nulls the droop")
    s = Sim(); s.set_gains(GOOD_KP, 40000.0, GOOD_KD); s.noise_m = 0.0
    s.advance(3.0)
    check("|error| < 5 µm with Ki", abs((s.x - s.x_ref) * 1e6) < 5,
          f"{(s.x - s.x_ref) * 1e6:+.1f} µm")

    print("\nZero gains -> caught, not runaway")
    s = Sim(); s.set_gains(0.0, 0.0, 0.0); s.noise_m = 0.0
    s.advance(1.5)
    check("bounded by the stops", X_BLOCK - 1e-9 <= s.x <= X_CATCH + 1e-9,
          f"x = {s.x*1e3:.3f} mm")
    check("flagged NOT STABILIZING", "NOT STABILIZING" in s.metrics()["verdict"][0])

    print("\nHuge gains -> still bounded, no NaN")
    s = Sim(); s.set_gains(KP_RANGE[1], KI_RANGE[1], KD_RANGE[1]); s.noise_m = 5e-6
    s.advance(1.5)
    check("finite state", np.isfinite([s.x, s.xdot, s.i]).all())
    check("bounded by the stops", X_BLOCK - 1e-9 <= s.x <= X_CATCH + 1e-9,
          f"x = {s.x*1e3:.3f} mm")

    print("\nRecovery from the catch is physically possible")
    s = Sim(); s.set_gains(GOOD_KP, GOOD_KI, GOOD_KD); s.noise_m = 0.0
    s.x, s.xdot = X_CATCH, 0.0
    s.advance(1.5)
    check("recovered to near the set-point", abs(s.x - s.x_ref) < 100e-6,
          f"recovered to {s.x*1e3:.3f} mm")

    print("\nDisturbance kick is survivable with the good tune")
    s = Sim(); s.set_gains(GOOD_KP, GOOD_KI, GOOD_KD); s.noise_m = 0.0
    s.advance(1.0); s.kick(25.0); s.advance(1.0)
    check("still off the stops after kick", not s.on_stop,
          f"x = {s.x*1e3:.3f} mm")

    print("\n" + ("ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--selftest", action="store_true",
                    help="run headless checks on the guards and presets")
    ap.add_argument("--snapshot", metavar="PATH",
                    help="render a static layout preview to PATH and exit")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(selftest())
    sys.exit(launch_gui(snapshot=args.snapshot) or 0)

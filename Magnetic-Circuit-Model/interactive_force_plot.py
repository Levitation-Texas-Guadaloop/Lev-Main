"""
Interactive F(z[mm]) explorer for the HEMS yoke reluctance model.

Adjust turns, stacked yoke depth, and target mass with sliders and see the
Force-vs-air-gap curve family (one curve per coil current) update live.
Hover over the plot to read exact (gap, force) values off the nearest curve.

Run:
    python interactive_force_plot.py
    (or, from inside the project venv:
     guadaloop_lev_control/.venv/bin/python3 interactive_force_plot.py)
"""

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.widgets import Button, CheckButtons, Slider, TextBox

import power_model
from reluctance_model import (
    YokeGeometry,
    equilibrium_gap_mm,
    required_release_current_amp,
    total_force,
)

DEFAULT_GEOM = YokeGeometry()
DEFAULT_CURRENTS = "-10,-9,-8,0,8,9,10"
DEFAULT_GAP_RANGE_MM = (5.0, 10.0)
DEFAULT_MASS_KG = 226.0
DEFAULT_S0_MM = 6.0
DEFAULT_R_COIL_OHM = 2.0  # manual-mode placeholder (auto mode ignores it)


def parse_currents(text):
    vals = []
    for tok in text.split(","):
        tok = tok.strip()
        if tok:
            vals.append(float(tok))
    if not vals:
        raise ValueError("need at least one current value")
    return vals


class ForcePlotApp:
    def __init__(self):
        self.geom = YokeGeometry()
        self.currents = parse_currents(DEFAULT_CURRENTS)
        self.gap_range_mm = DEFAULT_GAP_RANGE_MM
        self.s0_mm = DEFAULT_S0_MM  # starting gap for the release-current solve; None = unset
        self.coil_r_ohm = DEFAULT_R_COIL_OHM  # manual override value (when auto is off)
        # self.chk_auto_rcoil (built in _build_power_panel) is the source of truth for
        # whether R_coil is auto-derived from yoke depth via coil_model.resistance()
        self._hover_curves = []  # [(label, gap_mm_array, force_array, color)]

        self.fig = plt.figure(figsize=(13, 8.5))
        self.fig.suptitle("HEMS Yoke: Force vs. Air Gap (transcribed from full_hems.mw)",
                           fontsize=13, fontweight="bold", y=0.985)

        self.ax = self.fig.add_axes([0.07, 0.38, 0.58, 0.52])
        self.ax.set_xlabel("Air gap z [mm]")
        self.ax.set_ylabel("Total force, 4x per-leg-pair [N]")
        self.ax.grid(True, alpha=0.3)

        self._build_sliders()
        self._build_text_controls()
        self._build_reset_button()
        self._build_power_panel()
        self._build_hover()

        self.update(None)
        plt.show()

    # -- widget layout -------------------------------------------------------

    def _build_sliders(self):
        specs = [
            ("N_turns", "Turns (N)", 10.0, 1000.0, None, None),
            ("ydepth_in", "Yoke depth, ydepth [in]", 1.0, 20.0, 1.0, None),
            ("mass_kg", "Mass [kg]", 10.0, 1000.0, 1.0, DEFAULT_MASS_KG),
        ]
        left0, width, gap = 0.07, 0.24, 0.06
        y_label, y_slider, slider_h = 0.24, 0.19, 0.025

        self.sliders = {}
        for idx, (attr, label, vmin, vmax, valstep, init_override) in enumerate(specs):
            x0 = left0 + idx * (width + gap)
            self.fig.text(x0, y_label, label, fontsize=9.5, va="bottom")
            axs = self.fig.add_axes([x0, y_slider, width, slider_h])
            init = init_override if init_override is not None else getattr(DEFAULT_GEOM, attr)
            slider = Slider(axs, "", vmin, vmax, valinit=init, valstep=valstep, valfmt="%.3g")
            slider.on_changed(self.update)
            self.sliders[attr] = slider

    def _build_text_controls(self):
        right_x = 0.71
        right_w = 0.24

        self.fig.text(right_x, 0.895, "Currents [A] (comma-separated)", fontsize=9.5, va="bottom")
        ax_currents = self.fig.add_axes([right_x, 0.845, right_w, 0.045])
        self.tb_currents = TextBox(ax_currents, "", initial=DEFAULT_CURRENTS)
        self.tb_currents.on_submit(self._on_currents_change)

        self.fig.text(right_x, 0.775, "Air gap sweep range [mm]", fontsize=9.5, va="bottom")
        ax_gapmin = self.fig.add_axes([right_x, 0.725, right_w * 0.46, 0.045])
        self.tb_gap_min = TextBox(ax_gapmin, "min ", initial=str(DEFAULT_GAP_RANGE_MM[0]))
        self.tb_gap_min.on_submit(self._on_gap_range_change)

        ax_gapmax = self.fig.add_axes([right_x + right_w * 0.54, 0.725, right_w * 0.46, 0.045])
        self.tb_gap_max = TextBox(ax_gapmax, "max ", initial=str(DEFAULT_GAP_RANGE_MM[1]))
        self.tb_gap_max.on_submit(self._on_gap_range_change)

        self.fig.text(right_x, 0.655, "Starting gap s0 [mm] (< eq. gap) -- release current",
                       fontsize=9.5, va="bottom")
        ax_s0 = self.fig.add_axes([right_x, 0.605, right_w, 0.045])
        self.tb_s0 = TextBox(ax_s0, "", initial=str(DEFAULT_S0_MM))
        self.tb_s0.on_submit(self._on_s0_change)

        self.info_ax = self.fig.add_axes([right_x, 0.32, right_w, 0.25])
        self.info_ax.axis("off")

    def _build_reset_button(self):
        ax_reset = self.fig.add_axes([0.37, 0.06, 0.24, 0.05])
        self.btn_reset = Button(ax_reset, "Reset defaults")
        self.btn_reset.on_clicked(self._on_reset)

    def _build_power_panel(self):
        self.fig.text(0.07, 0.178, "R coil [Ω] (per leg)", fontsize=8.5, va="bottom")
        ax_rcoil = self.fig.add_axes([0.07, 0.14, 0.13, 0.034])
        self.tb_rcoil = TextBox(ax_rcoil, "", initial=str(DEFAULT_R_COIL_OHM))
        self.tb_rcoil.on_submit(self._on_rcoil_change)

        ax_auto = self.fig.add_axes([0.07, 0.108, 0.13, 0.028])
        ax_auto.axis("off")
        self.chk_auto_rcoil = CheckButtons(ax_auto, ["auto (coil_model(D))"], [True])
        self.chk_auto_rcoil.on_clicked(self._on_auto_rcoil_toggle)

        self.power_ax = self.fig.add_axes([0.225, 0.105, 0.69, 0.085])
        self.power_ax.axis("off")

    def _build_hover(self):
        self.hover_annot = self.ax.annotate(
            "", xy=(0, 0), xytext=(15, 15), textcoords="offset points",
            bbox=dict(boxstyle="round", fc="white", ec="0.5", alpha=0.95),
            arrowprops=dict(arrowstyle="->"), fontsize=9, family="monospace",
            visible=False, zorder=10,
        )
        self.fig.canvas.mpl_connect("motion_notify_event", self._on_hover)

    # -- callbacks -------------------------------------------------------------

    def _on_currents_change(self, text):
        try:
            self.currents = parse_currents(text)
        except ValueError:
            pass
        self.update(None)

    def _on_gap_range_change(self, _text):
        try:
            lo = float(self.tb_gap_min.text)
            hi = float(self.tb_gap_max.text)
            if hi > lo > 0:
                self.gap_range_mm = (lo, hi)
        except ValueError:
            pass
        self.update(None)

    def _on_s0_change(self, text):
        text = text.strip()
        self.s0_mm = float(text) if text else None
        self.update(None)

    def _on_rcoil_change(self, text):
        try:
            r = float(text)
            if r > 0:
                self.coil_r_ohm = r
                self.chk_auto_rcoil.set_active(0, state=False)  # also triggers an update()
                return
        except ValueError:
            pass
        self.update(None)

    def _on_auto_rcoil_toggle(self, _label):
        self.update(None)

    def _on_reset(self, _event):
        for attr, slider in self.sliders.items():
            slider.reset()
        # set_val() fires each box's on_submit itself in this matplotlib version; this is
        # a plain display reset, so suppress that and set the backing state explicitly
        # below instead (avoids redundant/out-of-order update() calls mid-reset).
        for tb, text in (
            (self.tb_currents, DEFAULT_CURRENTS),
            (self.tb_gap_min, str(DEFAULT_GAP_RANGE_MM[0])),
            (self.tb_gap_max, str(DEFAULT_GAP_RANGE_MM[1])),
            (self.tb_s0, str(DEFAULT_S0_MM)),
            (self.tb_rcoil, str(DEFAULT_R_COIL_OHM)),
        ):
            tb.eventson = False
            tb.set_val(text)
            tb.eventson = True
        self.gap_range_mm = DEFAULT_GAP_RANGE_MM
        self.currents = parse_currents(DEFAULT_CURRENTS)
        self.s0_mm = DEFAULT_S0_MM
        self.coil_r_ohm = DEFAULT_R_COIL_OHM
        self.chk_auto_rcoil.set_active(0, state=True)  # also triggers an update()

    def _on_hover(self, event):
        if event.inaxes != self.ax or not self._hover_curves:
            if self.hover_annot.get_visible():
                self.hover_annot.set_visible(False)
                self.fig.canvas.draw_idle()
            return

        gap_mm = self._hover_curves[0][1]
        idx = int(np.clip(np.searchsorted(gap_mm, event.xdata), 0, len(gap_mm) - 1))

        # snap to whichever plotted curve is vertically closest to the cursor
        best = min(
            self._hover_curves,
            key=lambda c: abs(c[2][idx] - event.ydata) if event.ydata is not None else np.inf,
        )
        label, xs, ys, color = best
        x_snap, y_snap = xs[idx], ys[idx]

        self.hover_annot.xy = (x_snap, y_snap)
        self.hover_annot.set_text(f"{label}\nz = {x_snap:.3f} mm\nF = {y_snap:.2f} N")
        self.hover_annot.get_bbox_patch().set_edgecolor(color)
        self.hover_annot.set_visible(True)
        self.fig.canvas.draw_idle()

    # -- core update -----------------------------------------------------------

    def _geom_from_sliders(self):
        kwargs = {attr: slider.val for attr, slider in self.sliders.items()}
        return YokeGeometry(**{**DEFAULT_GEOM.__dict__, **kwargs})

    def _r_coil(self, geom):
        """Per-leg R: None override -> power_model derives it from geom via coil_model."""
        auto = self.chk_auto_rcoil.get_status()[0]
        return power_model.coil_resistance(geom, None if auto else self.coil_r_ohm)

    def update(self, _val):
        geom = self._geom_from_sliders()
        R = self._r_coil(geom)

        lo_mm, hi_mm = self.gap_range_mm
        gap_mm = np.linspace(lo_mm, hi_mm, 300)
        gap_m = gap_mm * 1e-3

        self.ax.cla()
        self.ax.set_xlabel("Air gap z [mm]")
        self.ax.set_ylabel("Total force, 4x per-leg-pair [N]")
        self.ax.grid(True, alpha=0.3)

        cmap = plt.get_cmap("coolwarm")
        n = len(self.currents)
        self._hover_curves = []
        for k, i_amp in enumerate(self.currents):
            F = total_force(gap_m, i_amp, geom)
            color = cmap(k / max(n - 1, 1))
            label = f"i = {i_amp:g} A"
            self.ax.plot(gap_mm, F, lw=2, color=color, label=label)
            self._hover_curves.append((label, gap_mm, F, color))

        weight_n = geom.mass_kg * 9.8
        g_eq = None
        try:
            g_eq = equilibrium_gap_mm(geom, i_amp=0.0, bracket_mm=(lo_mm * 0.5, hi_mm * 2.0))
            if lo_mm <= g_eq <= hi_mm:
                self.ax.axvline(g_eq, color="k", ls="--", lw=1, alpha=0.6)
                self.ax.annotate(f"eq. gap @ i=0\n{g_eq:.2f} mm",
                                  xy=(g_eq, self.ax.get_ylim()[1] * 0.05),
                                  fontsize=8, ha="center")
            eq_note = f"Equilibrium gap (i=0): {g_eq:.3f} mm"
        except Exception:
            eq_note = "Equilibrium gap: no solution in range"

        i_release = None
        if self.s0_mm is None:
            s0_note = "Release current: (enter s0 above)"
        elif self.s0_mm <= 0:
            s0_note = "Release current: s0 must be > 0"
        elif g_eq is not None and self.s0_mm >= g_eq:
            s0_note = f"Release current: s0 must be < eq. gap ({g_eq:.3f} mm)"
        else:
            try:
                i_release = required_release_current_amp(geom, self.s0_mm * 1e-3)
                s0_note = f"Release current @ s0={self.s0_mm:.3f}mm: {i_release:.3f} A"
                if lo_mm <= self.s0_mm <= hi_mm:
                    self.ax.axvline(self.s0_mm, color="firebrick", ls=":", lw=1.3, alpha=0.8)
                    self.ax.annotate(f"s0 = {self.s0_mm:.2f} mm\ni_release = {i_release:.2f} A",
                                      xy=(self.s0_mm, self.ax.get_ylim()[1] * 0.15),
                                      fontsize=8, ha="center", color="firebrick")
            except Exception as e:
                s0_note = f"Release current: {e}"

        self.ax.set_title("F(z) at swept currents")
        self.ax.legend(loc="upper right", fontsize=8, ncol=2)

        self.info_ax.cla()
        self.info_ax.axis("off")
        info_lines = [
            f"Mass:   {geom.mass_kg:.1f} kg",
            f"Weight: {weight_n:.1f} N  (m x 9.8)",
            "",
            eq_note,
            s0_note,
            "",
            f"Turns (N):    {geom.N_turns:.0f}",
            f"Yoke depth:   {geom.ydepth_in:.2f} in",
            f"Pole area:    {geom.ydepth_in * geom.pole_width_in:.3f} in^2",
        ]
        self.info_ax.text(0, 1, "\n".join(info_lines), va="top", ha="left", fontsize=10,
                           family="monospace")

        auto_rcoil = self.chk_auto_rcoil.get_status()[0]
        if auto_rcoil:
            # set_val() itself fires the 'submit' event in this matplotlib version, which
            # would otherwise bounce straight back into _on_rcoil_change() and flip auto
            # mode back off -- suppress that for this programmatic, display-only sync.
            self.tb_rcoil.eventson = False
            self.tb_rcoil.set_val(f"{R:.4f}")
            self.tb_rcoil.eventson = True
            self.tb_rcoil.ax.set_facecolor("#eeeeee")
        else:
            self.tb_rcoil.ax.set_facecolor("white")

        self.power_ax.cla()
        self.power_ax.axis("off")
        if i_release is None:
            power_text = "Release-current power draw: enter a valid s0 above"
        else:
            r_src = f"auto: coil_model.resistance(D={geom.ydepth_in:.2f}in)" if auto_rcoil else "manual"
            power = power_model.release_current_power(geom, self.s0_mm * 1e-3, R)
            y, t = power['per_yoke'], power['total']
            power_text = (
                f"Release-current power draw -- R_coil = {R:.3f} ohm/leg [{r_src}], "
                f"i_release = {i_release:.3f} A\n"
                f"  Peak power:  {y['peak_power_w']:8.1f} W/yoke   "
                f"{t['peak_power_w']:9.1f} W total (x{power['n_yokes']} yokes)\n"
                f"  2 coils SERIES:    V = {y['series']['voltage_v']:7.2f} V"
                f"   I/yoke = {y['series']['current_a']:6.3f} A"
                f"   I(battery) = {t['series']['current_a']:7.3f} A\n"
                f"  2 coils PARALLEL:  V = {y['parallel']['voltage_v']:7.2f} V"
                f"   I/yoke = {y['parallel']['current_a']:6.3f} A"
                f"   I(battery) = {t['parallel']['current_a']:7.3f} A"
            )
        self.power_ax.text(0, 1, power_text, va="top", ha="left", fontsize=8.5,
                            family="monospace")

        self.hover_annot = self.ax.annotate(
            "", xy=(0, 0), xytext=(15, 15), textcoords="offset points",
            bbox=dict(boxstyle="round", fc="white", ec="0.5", alpha=0.95),
            arrowprops=dict(arrowstyle="->"), fontsize=9, family="monospace",
            visible=False, zorder=10,
        )

        self.fig.canvas.draw_idle()


if __name__ == "__main__":
    ForcePlotApp()

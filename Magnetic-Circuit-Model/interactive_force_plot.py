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
from matplotlib.widgets import Button, Slider, TextBox

from reluctance_model import YokeGeometry, equilibrium_gap_mm, total_force

DEFAULT_GEOM = YokeGeometry()
DEFAULT_CURRENTS = "-16,-12,-8,-4,0,4,8,12,16"
DEFAULT_GAP_RANGE_MM = (2.0, 15.0)


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
        self._build_hover()

        self.update(None)
        plt.show()

    # -- widget layout -------------------------------------------------------

    def _build_sliders(self):
        specs = [
            ("N_turns", "Turns (N)", 10.0, 1000.0),
            ("ydepth_in", "Yoke depth, ydepth [in]", 1.0, 20.0),
            ("mass_kg", "Mass [kg]", 10.0, 1000.0),
        ]
        left0, width, gap = 0.07, 0.24, 0.06
        y_label, y_slider, slider_h = 0.24, 0.19, 0.025

        self.sliders = {}
        for idx, (attr, label, vmin, vmax) in enumerate(specs):
            x0 = left0 + idx * (width + gap)
            self.fig.text(x0, y_label, label, fontsize=9.5, va="bottom")
            axs = self.fig.add_axes([x0, y_slider, width, slider_h])
            init = getattr(DEFAULT_GEOM, attr)
            slider = Slider(axs, "", vmin, vmax, valinit=init, valfmt="%.3g")
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

        self.info_ax = self.fig.add_axes([right_x, 0.38, right_w, 0.30])
        self.info_ax.axis("off")

    def _build_reset_button(self):
        ax_reset = self.fig.add_axes([0.37, 0.06, 0.24, 0.05])
        self.btn_reset = Button(ax_reset, "Reset defaults")
        self.btn_reset.on_clicked(self._on_reset)

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

    def _on_reset(self, _event):
        for attr, slider in self.sliders.items():
            slider.reset()
        self.tb_currents.set_val(DEFAULT_CURRENTS)
        self.tb_gap_min.set_val(str(DEFAULT_GAP_RANGE_MM[0]))
        self.tb_gap_max.set_val(str(DEFAULT_GAP_RANGE_MM[1]))
        self.gap_range_mm = DEFAULT_GAP_RANGE_MM
        self.currents = parse_currents(DEFAULT_CURRENTS)
        self.update(None)

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

    def update(self, _val):
        geom = self._geom_from_sliders()

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

        self.ax.set_title("F(z) at swept currents")
        self.ax.legend(loc="upper right", fontsize=8, ncol=2)

        self.info_ax.cla()
        self.info_ax.axis("off")
        info_lines = [
            f"Mass:   {geom.mass_kg:.1f} kg",
            f"Weight: {weight_n:.1f} N  (m x 9.8)",
            "",
            eq_note,
            "",
            f"Turns (N):    {geom.N_turns:.0f}",
            f"Yoke depth:   {geom.ydepth_in:.2f} in",
            f"Pole area:    {geom.ydepth_in * geom.pole_width_in:.3f} in^2",
        ]
        self.info_ax.text(0, 1, "\n".join(info_lines), va="top", ha="left", fontsize=10,
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

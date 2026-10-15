"""
Interactive UI for power_model: set a total (all-yokes) peak power ceiling and see the
2-coil series/parallel voltage/current it allows, plus the release-current power draw at a
starting gap s0 and the largest s0 the ceiling can still release from.

Plot: total peak power needed to release from gap s (curve) vs. the ceiling (line).

Run:
    guadaloop_lev_control/.venv/bin/python3 Magnetic-Circuit-Model/power_ui.py
"""

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.widgets import Button, CheckButtons, Slider, TextBox

import power_model
from reluctance_model import YokeGeometry, equilibrium_gap_mm

DEFAULT_GEOM = YokeGeometry()
DEFAULT_MASS_KG = 226.0
DEFAULT_S0_MM = 6.0
DEFAULT_CEILING_W = 1500.0
DEFAULT_R_COIL_OHM = 2.0  # manual-mode placeholder


class PowerApp:
    def __init__(self):
        self.s0_mm = DEFAULT_S0_MM
        self.ceiling_w = DEFAULT_CEILING_W
        self.coil_r_ohm = DEFAULT_R_COIL_OHM

        self.fig = plt.figure(figsize=(13, 8.5))
        self.fig.suptitle("HEMS Yoke: Power Ceiling / Release-Current Budget",
                          fontsize=13, fontweight="bold", y=0.985)
        self.ax = self.fig.add_axes([0.07, 0.45, 0.58, 0.45])
        self.out_ax = self.fig.add_axes([0.07, 0.0, 0.88, 0.31])
        self.out_ax.axis("off")

        self._build_sliders()
        self._build_controls()
        self.update(None)
        plt.show()

    def _build_sliders(self):
        specs = [
            ("N_turns", "Turns (N)", 10.0, 1000.0, None, None),
            ("ydepth_in", "Yoke depth [in]", 1.0, 20.0, 1.0, None),
            ("mass_kg", "Mass [kg]", 10.0, 1000.0, 1.0, DEFAULT_MASS_KG),
        ]
        left0, width, gap = 0.07, 0.24, 0.06
        self.sliders = {}
        for idx, (attr, label, vmin, vmax, step, init_override) in enumerate(specs):
            x0 = left0 + idx * (width + gap)
            self.fig.text(x0, 0.375, label, fontsize=9.5, va="bottom")
            axs = self.fig.add_axes([x0, 0.34, width, 0.025])
            init = init_override if init_override is not None else getattr(DEFAULT_GEOM, attr)
            s = Slider(axs, "", vmin, vmax, valinit=init, valstep=step, valfmt="%.3g")
            s.on_changed(self.update)
            self.sliders[attr] = s

    def _build_controls(self):
        x, w = 0.71, 0.24

        self.fig.text(x, 0.895, "Power ceiling, total [W]", fontsize=9.5, va="bottom")
        self.tb_ceiling = TextBox(self.fig.add_axes([x, 0.845, w, 0.045]), "",
                                  initial=str(DEFAULT_CEILING_W))
        self.tb_ceiling.on_submit(self._on_ceiling)

        self.fig.text(x, 0.775, "Starting gap s0 [mm]", fontsize=9.5, va="bottom")
        self.tb_s0 = TextBox(self.fig.add_axes([x, 0.725, w, 0.045]), "", initial=str(DEFAULT_S0_MM))
        self.tb_s0.on_submit(self._on_s0)

        self.fig.text(x, 0.655, "R coil [Ω] (per leg)", fontsize=9.5, va="bottom")
        self.tb_rcoil = TextBox(self.fig.add_axes([x, 0.605, w, 0.045]), "",
                                initial=str(DEFAULT_R_COIL_OHM))
        self.tb_rcoil.on_submit(self._on_rcoil)

        ax_auto = self.fig.add_axes([x, 0.555, w, 0.04])
        ax_auto.axis("off")
        self.chk_auto = CheckButtons(ax_auto, ["auto (coil_model(D))"], [True])
        self.chk_auto.on_clicked(lambda _l: self.update(None))

        self.btn_reset = Button(self.fig.add_axes([x, 0.48, w, 0.05]), "Reset defaults")
        self.btn_reset.on_clicked(self._on_reset)

    # -- callbacks -------------------------------------------------------------

    def _on_ceiling(self, text):
        try:
            v = float(text)
            if v > 0:
                self.ceiling_w = v
        except ValueError:
            pass
        self.update(None)

    def _on_s0(self, text):
        try:
            self.s0_mm = float(text) if text.strip() else None
        except ValueError:
            pass
        self.update(None)

    def _on_rcoil(self, text):
        try:
            r = float(text)
            if r > 0:
                self.coil_r_ohm = r
                self.chk_auto.set_active(0, state=False)  # also triggers update()
                return
        except ValueError:
            pass
        self.update(None)

    def _on_reset(self, _event):
        for s in self.sliders.values():
            s.reset()
        # TextBox.set_val fires on_submit here; suppress and set state explicitly
        for tb, text in ((self.tb_ceiling, str(DEFAULT_CEILING_W)), (self.tb_s0, str(DEFAULT_S0_MM)),
                         (self.tb_rcoil, str(DEFAULT_R_COIL_OHM))):
            tb.eventson = False
            tb.set_val(text)
            tb.eventson = True
        self.ceiling_w, self.s0_mm, self.coil_r_ohm = (
            DEFAULT_CEILING_W, DEFAULT_S0_MM, DEFAULT_R_COIL_OHM)
        self.chk_auto.set_active(0, state=True)  # also triggers update()

    # -- core ------------------------------------------------------------------

    def _geom(self):
        kwargs = {a: s.val for a, s in self.sliders.items()}
        return YokeGeometry(**{**DEFAULT_GEOM.__dict__, **kwargs})

    def update(self, _val):
        geom = self._geom()
        auto = self.chk_auto.get_status()[0]
        R = power_model.coil_resistance(geom, None if auto else self.coil_r_ohm)

        if auto:
            self.tb_rcoil.eventson = False
            self.tb_rcoil.set_val(f"{R:.4f}")
            self.tb_rcoil.eventson = True
            self.tb_rcoil.ax.set_facecolor("#eeeeee")
        else:
            self.tb_rcoil.ax.set_facecolor("white")

        try:
            g_eq = equilibrium_gap_mm(geom)
        except Exception:
            g_eq = None

        # release power vs starting gap
        s_mm, p_tot = np.array([]), np.array([])
        if g_eq is not None:
            s_mm = np.linspace(0.3, g_eq * 0.995, 60)
            p_tot = np.array([
                power_model.release_current_power(geom, s * 1e-3, R)["total"]["peak_power_w"]
                for s in s_mm
            ])

        self.ax.cla()
        self.ax.grid(True, alpha=0.3)
        self.ax.set_xlabel("Starting gap s0 [mm]")
        self.ax.set_ylabel("Total release power, all yokes [W]")
        self.ax.set_title("Power needed to release from s0 vs. ceiling")
        lines = []
        if len(s_mm):
            self.ax.plot(s_mm, p_tot, lw=2, color="tab:blue", label="release power")
            self.ax.axhline(self.ceiling_w, color="firebrick", ls="--", label="ceiling")
            # largest s0 still covered: power rises as s0 shrinks, so cover = s0 >= crossing
            ok = p_tot <= self.ceiling_w
            if ok.any() and not ok.all():
                k = int(np.argmax(ok))  # first covered point (s increasing)
                s_min = np.interp(self.ceiling_w, [p_tot[k], p_tot[k - 1]], [s_mm[k], s_mm[k - 1]])
                self.ax.axvspan(s_min, s_mm[-1], color="green", alpha=0.08)
                lines.append(f"Ceiling covers release from s0 >= {s_min:.2f} mm (up to eq. gap {g_eq:.2f} mm)")
            elif ok.all():
                lines.append(f"Ceiling covers release from every s0 up to eq. gap {g_eq:.2f} mm")
            else:
                lines.append("Ceiling does not cover release from any s0 in range")
            if self.s0_mm is not None and 0 < self.s0_mm < g_eq:
                p0 = power_model.release_current_power(geom, self.s0_mm * 1e-3, R)["total"]["peak_power_w"]
                self.ax.plot([self.s0_mm], [p0], "o", color="k")
            self.ax.legend(loc="upper right", fontsize=8)
        else:
            lines.append("Equilibrium gap: no solution")

        head = (f"Mass {geom.mass_kg:.0f} kg | N = {geom.N_turns:.0f} | D = {geom.ydepth_in:.1f} in | "
                f"R_coil = {R:.3f} ohm/leg [{'auto' if auto else 'manual'}] | "
                f"eq. gap = {g_eq:.3f} mm" if g_eq else "no equilibrium")
        txt = [head, ""]

        b = power_model.power_budget(geom, self.ceiling_w, R)
        txt.append(f"CEILING {self.ceiling_w:g} W total -> max coil current {b['i_coil_amp']:.3f} A "
                   f"({b['max_ampere_turns_per_coil']:.0f} A-turns/coil)")
        txt.append(power_model.format_result(b).split("\n", 1)[1])
        txt.extend(lines)

        if self.s0_mm is not None and g_eq is not None:
            txt.append("")
            if not 0 < self.s0_mm < g_eq:
                txt.append(f"s0 = {self.s0_mm:g} mm: must be in (0, {g_eq:.3f}) mm")
            else:
                r = power_model.release_current_power(geom, self.s0_mm * 1e-3, R)
                ok = b["i_coil_amp"] >= r["i_release_amp"]
                txt.append(f"RELEASE @ s0 = {self.s0_mm:g} mm: need {r['i_release_amp']:.3f} A "
                           f"-> {'OK' if ok else 'NOT COVERED'} "
                           f"(headroom {b['i_coil_amp'] - r['i_release_amp']:+.3f} A)")
                txt.append(power_model.format_result(r).split("\n", 1)[1])

        self.out_ax.cla()
        self.out_ax.axis("off")
        self.out_ax.text(0, 1, "\n".join(txt), va="top", ha="left", fontsize=7, family="monospace")
        self.fig.canvas.draw_idle()


if __name__ == "__main__":
    PowerApp()

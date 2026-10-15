# Magnetic-Circuit-Model — Agent Handoff

## What This Is

A Python transcription of a Maple worksheet, plus an interactive force-plot
built on top of it. Not independent research — a faithful port, then a UI.

**Source of truth (Maple, read-only, do not edit):**
`/Users/aditya/Library/CloudStorage/OneDrive-TheUniversityofTexasatAustin/Levitation 2024-2025/Code/hems_models/full_hems.mw`
(XML worksheet, Maple 2023.2 — readable directly as text, no Maple install needed;
the giant embedded-plot line near the end is base64 plot data, skip it when grepping).

**Physics background:** `../docs/rfcs/knowledge/Maglev - PM Bias and Force Linearization.md`
(§4b derives the same reluctance-network force law by hand). That doc's model
(`guadaloop_lev_control` / `tutorials/maglev/params.py`) lumps PM+steel into one
series reluctance `R0`; **this** model keeps leg/base/track/PM as separate
reluctance terms and adds the `ydepth` stacking dimension — richer, not a
duplicate. Don't merge them.

## Provenance / How This Was Built

1. Read `full_hems.mw` as plain XML text (grep for `:=` and `<Input>` to find
   the executable Maple cells; the `<Output>` cells hex/base64-encode Maple's
   typeset rendering and are not worth decoding — the plain-text numeric
   literals inside them were used only to spot-check the transcription).
2. Transcribed the worksheet's symbolic derivation cell-by-cell into
   `reluctance_model.py` using `sympy` (mirrors Maple's `unapply`/`diff`
   exactly), generalizing every literal (leg/PM/base/track lengths, `ydepth`,
   `N`, `usteel`, `H_c`) into a field on `YokeGeometry`.
3. Validated the transcription against three of the worksheet's own printed
   outputs (see "Verified against Maple" below) — matched to 5+ significant
   figures. This is the confidence basis; don't re-derive the physics to
   double check, re-run `python reluctance_model.py` instead.
4. Built `interactive_force_plot.py` (matplotlib, no new deps) on top of the
   validated model. Iterated per user feedback: started with ~12 sliders (one
   per geometry field) → user cut it to 3 (turns, ydepth, mass) because the
   rest are rarely-touched construction constants, not design knobs. Also
   added a Newtons readout (`mass_kg * 9.8`) and hover tooltips (manual
   `motion_notify_event` handler that snaps to the nearest plotted curve —
   `mplcursors` is NOT installed in the venv and was deliberately not added
   for one feature).

## File Inventory

| File | Contents |
|---|---|
| `reluctance_model.py` | The transcription. `YokeGeometry` dataclass (all knobs), symbolic derivation (module-level, built once at import), `force_per_leg_pair()` == Maple `Frel11`, `total_force()` == Maple `4*Frel11(...)`, `equilibrium_gap_mm()` == Maple `fsolve(...)`. Has a `__main__` block that prints the validation numbers. |
| `interactive_force_plot.py` | `ForcePlotApp` (matplotlib) — F(z) curve family at swept currents; sliders for N_turns / ydepth_in / mass_kg; text boxes for currents, gap range, s0, R coil; "auto" R checkbox; hover tooltips; power-draw panel; reset button. Non-slider `YokeGeometry` fields stay at dataclass defaults. |
| `coil_model.py` | Leg-coil DC resistance from geometry (`resistance(D, ...)`), `fit_k_c()` (current fit)/`fit_k()`/`fit_k_power()`, `report()`. Data in `measurements.csv`; tests in `test_coil_model.py`. |
| `power_model.py` | Power/voltage/current helper (forward + inverse) — see "Power helper". Tests in `test_power_model.py`. |
| `power_ui.py` | matplotlib UI for `power_model` (ceiling → V/I, release-vs-ceiling plot). Kept as-is alongside the web UI. |
| `web/` | Browser UI (Vite + Plotly frontend, stdlib Python API reusing the real models) — see "Web UI". `start_web.sh` launches it. |

## Maple → Python Name Map

| Maple | Python | Notes |
|---|---|---|
| `u0` | `_mu0` (module-private sympy constant) | `4*pi*1e-7` |
| `usteel` | `geom.mu_r_steel` | lumped 1018 relative permeability |
| `Relf(l,ur,A)` | `_Relf(l,ur,A)` | `l/(ur*mu0*A)` |
| `len(a)` | `_len_expr(a)` (symbolic) / `length_m(a)` (numeric) | inches → meters |
| `ydepth` | `geom.ydepth_in` | stack depth; >1 = multiple 1"-deep cores side by side |
| `NN` | `geom.N_turns` | |
| `Rel[air]`/`Rel[mag]`/`Rel[leg]`/`Rel[base]`/`Rel[track]` | `_Rel_air` etc. (module-private sympy exprs) | one-for-one |
| `RelT` | `_RelT` | `2*(air+leg+mag) + base + track` |
| `H[c]` | `geom.H_c_oersted` | Oersted, not SI — conversion literal `79.577471546` kept as-is |
| `PM` | `_PM_mmf` | per-leg PM MMF |
| `Mmf` | `_Mmf` | `2*(PM - N*i)` |
| `phi` | `_phi` | `Mmf/RelT` |
| `Frel1` | `_Frel1` | `diff((1/2)*Rel_air*phi^2, g)` |
| `Frel11(g,N,i)` | `force_per_leg_pair(g,N,i,geom)` | generalized over all geometry, not just g/N/i |
| `4*Frel11(...)` | `total_force(...)` | the worksheet's own scale factor, unexplained, preserved |
| `sol := fsolve(4*Frel11(g,NN,0)-Fw=0,g)*1000` | `equilibrium_gap_mm(geom)` | uses `scipy.optimize.brentq`, not `fsolve` |

## Verified Against Maple (do not re-verify, re-run instead)

Run `python reluctance_model.py` (needs the project venv — see below). Expected:

| Quantity | Maple worksheet | Python |
|---|---|---|
| PM MMF | 22233.94555 | 22233.94555 |
| `Frel11(5mm, 250, 0)` | 772.597343436 | 772.597342 |
| Equilibrium gap @ 180 kg, i=0 | 9.184990200 mm | 9.184990 mm |

## Release current (s0)

`reluctance_model.required_release_current_amp(geom, gap_m)` solves
`total_force(gap_m, i) = mass*9.8` for `i`: the coil current that cancels enough PM bias for
the pod to fall from a starting gap `s0`. `s0` must be strictly below the i=0 equilibrium gap
(above it the passive force is already < weight, so no release current exists — the UIs say so).
Since `Mmf = 2*(PM - N*i)`, force falls from its i=0 value to ~0 at `i_null = PM_mmf/N`, then
*rises again* (reverse flux); the root is bracketed in `[0, i_null]`. (An earlier version doubled
`i` until the sign flipped and could overshoot `i_null` for low mass / high turns — fixed; found by
the web API's knob-grid stability test.) Pure force-law solve: no resistance/power content here.
In the UIs `s0` is a text box (blank = unset); the plot marks it with a red dotted line.

## Coil resistance from geometry (`coil_model.py`) — rough derivation

One leg coil: N turns of 18 AWG magnet wire (insulated OD `d` = 0.043 in, `rho'` = 0.533 mΩ/in at
20 °C) wound on a rectangular bobbin around the leg. Leg depth `D` == `YokeGeometry.ydepth_in`.

    R(D) = rho' * N * MLT(D) * (1 + 0.00393*(T-20)) + R_leads
    MLT  = 2*k*D + c*(2*w + 8*t_b + 2*pi*r_bar)       (mean length per turn, inches)

- `2*k*D`: the two long sides (along D). `k` is the **slope correction**. Pure geometry is k = 1.
- `2*w`: the two short sides (leg width `w` = 1 in).
- `8*t_b`: bobbin wall (`t_b` = 0.125 in, confirmed 1/8"; an earlier 1/4" was a mistake) grows the
  rectangle by `t_b` on all four sides → perimeter +8·t_b.
- `2*pi*r_bar`: layer build-up. Turns per layer = floor(h/d) with winding height `h` = 1.5 in
  (→ 34); layer j sits at radial offset (j−½)·d and adds ~2π·offset of rounded-corner perimeter;
  `r_bar` = turn-weighted mean offset over all layers incl. the partial last one. Depends on N.
- `c` scales those three fixed-length terms (c = 1 is pure geometry).
- Temperature coeff 0.00393/°C; `R_leads` default 0 (4-wire measurement assumed).

**Current fit (2026-10-13)** — empirical data: D=1 in → 1.1 Ω, D=9 in → 3.8–4.0 Ω (3.9 used).
`fit_k_c()` fits both `k` and `c` (weighted LSQ, linear): **k = 1.313, c = 1.408** — exact through
both points, R(D) ≈ 0.750 + 0.350·D. Both are empirical: k≈1.3 is a plausible pillowing factor;
c>1 means the fixed-length terms are bigger than the ideal bobbin geometry (leads, flanges, looser
winding). With 2 points and 2 params there are no residual dof (se's are formal,
`K_BULGE_STDERR_DEFAULT` = 0.066). The pure-k fit (c = 1, original model form) gives k = 1.413 and
predicts 0.91 Ω at D=1 (−0.19, just inside the 0.2 Ω acceptance) and 3.92 Ω at D=9; use it
(`resistance(D, k=1.413, c=1.0)`) if you prefer the single-knob model. History: the D=9 row was
briefly misread as D=4 (and t_b as 1/4"); do not trust older k values (1.39, 1.45, 3.5).
Pending D=5 row predicts 2.50 Ω. More points at intermediate D will show whether R is truly linear
in D; `fit_k_power()` (needs ≥3 points) tests a D-dependent k. Re-run `python coil_model.py` after
editing `measurements.csv`, then copy new k, c into `K_BULGE_DEFAULT`/`C_SCALE_DEFAULT`.
Prediction table: D = 1, 2, 3, 4, 5, 6, 9 in → 1.10, 1.45, 1.80, 2.15, 2.50, 2.85, 3.90 Ω.
UIs show the breakdown ("How R is derived" in the web UI).

## Power helper (`power_model.py`)

Not part of the Maple transcription (keeps `reluctance_model.py` pure). Wiring model: each yoke has
2 leg coils; the reluctance model uses one shared `i`, so **each coil must carry `i_coil`** →
dissipation `2*i_coil²*R` per yoke regardless of wiring. What the supply sees:

| | voltage | supply current |
|---|---|---|
| 2 coils series | `2*i*R` | `i` |
| 2 coils parallel | `i*R` | `2*i` |

Whole pod = `N_YOKES` (4) yokes: power ×4, battery current ×4 (same voltage; assumes identical yokes
fed in parallel from one bus). Functions:
- `coil_resistance(geom, override=None)` — manual R if given, else `coil_model.resistance(D, N)`
  (this is the UIs' "auto" toggle).
- `power_for_coil_current(i, R)` → `{per_yoke, total}`.
- `release_current_power(geom, gap_m, R=None)` — **forward**: release current at s0 → power/V/I.
- `power_budget(geom, power_ceiling_w, R=None, gap_m=None)` — **inverse**: total-pod power ceiling →
  `i_max = sqrt(P / (4*2*R))`, series/parallel V/I, amp-turns/coil; with `gap_m` also headroom vs the
  release current. CLI: `python power_model.py --ceiling-w 1500 --s0-mm 6`.
- Reference (UI defaults 226 kg / 6 in / 250 T / s0 6 mm, R auto = 2.849 Ω): eq. gap 7.485 mm,
  release 8.412 A, 403.3 W/yoke, 1613.2 W total; a 1500 W ceiling allows 8.112 A → NOT covered
  (−0.300 A), covers s0 ≥ ~6.06 mm.

## Web UI (`web/`)

Run: `./start_web.sh` (from this dir) → Vite on http://localhost:5173, API on 127.0.0.1:8765.
Manually: `guadaloop_lev_control/.venv/bin/python3 web/api_server.py` + `cd web && npm run dev`.
- `web/api_server.py` — stdlib `http.server` (no pip installs; Streamlit isn't in the venv). One
  endpoint `POST /api/model` returns everything (force curves, eq. gap, release, budget, power-vs-s0
  sweep, coil breakdown) by calling the real `reluctance_model`/`coil_model`/`power_model` — the
  physics lives only in Python.
- `web/src/main.js` — vanilla JS + Plotly (`plotly.js-basic-dist-min`). Two tabs sharing all knobs:
  **Force vs. gap** (curves, weight line, eq-gap and s0 markers, equilibrium/release/coil cards, power
  table) and **Power budget** (release power vs s0 curve with ceiling line and green "covered" band,
  COVERED/NOT COVERED card, V/I tables per yoke and ×4 battery). Auto-R checkbox mirrors the
  desktop one (typing a manual R unchecks auto). Light/dark follows the OS. Requests are debounced
  (60 ms) with a sequence guard so stale responses can't overwrite newer ones.
- Tests: `web/test_api.py` (stdlib unittest) — reference numbers, a 3×3×3×4×2 knob-grid for
  exceptions/NaN, manual-R override, input validation. Browser-level check used headless Chrome via
  puppeteer-core installed *outside* the repo (slider drags, rapid-fire changes, auto/manual R, bad
  text input, tab switch, reset — no console errors); not checked in.
- The equilibrium gap is solved over a wide bracket (0.05–200 mm), independent of the plot's gap
  range, so changing the range never changes "eq. gap" or whether s0 is valid.

Matplotlib scripts (`interactive_force_plot.py`, `power_ui.py`) are intentionally unchanged
reference UIs. Gotcha: `TextBox.set_val()` fires `on_submit` in the installed matplotlib; wrap
programmatic calls in `eventson = False/True` (see `_on_reset`, auto-R sync in `update()`).

## Tests / verification

    guadaloop_lev_control/.venv/bin/python3 Magnetic-Circuit-Model/reluctance_model.py   # 3 Maple numbers
    cd Magnetic-Circuit-Model && ../guadaloop_lev_control/.venv/bin/python3 -m unittest test_coil_model test_power_model
    cd Magnetic-Circuit-Model && ../guadaloop_lev_control/.venv/bin/python3 -m unittest discover -s web -p test_api.py

No pytest in the venv — stdlib `unittest` only.

## Known, Deliberately Unfixed Discrepancy

`Rel[leg]` uses a 1" steel leg length. The user-supplied cross-section diagram
shows only 0.5" of 1018 steel per leg (the other 1" of the 1.5"-tall leg
stack is the PM, modeled separately via `Rel[mag]`). This mismatch exists in
the original `.mw` file and was carried through unchanged — **the user
explicitly asked to transcribe first, verify correctness later.** Do not
silently "fix" `leg_len_in`'s default without being asked; if asked to
reconcile it, that's a physics-review task, not a transcription task.

Other inherited approximations (also unfixed, also out of scope unless
asked): no eddy-current/lamination losses, no flux leakage, the `4x` scale
factor in `total_force` is un-derived in the source worksheet.

## Running

```
guadaloop_lev_control/.venv/bin/python3 Magnetic-Circuit-Model/reluctance_model.py
guadaloop_lev_control/.venv/bin/python3 Magnetic-Circuit-Model/interactive_force_plot.py
```

That venv (repo-root-relative path above) already has `sympy`, `numpy`,
`scipy`, `matplotlib` — reuse it, don't create a new one or pip-install
into the system Python.

## If You're Extending the Interactive Tool

- `_geom_from_sliders()` builds a full `YokeGeometry` from the 3 slider values
  merged over `DEFAULT_GEOM.__dict__` — adding a 4th slider means adding it to
  the `specs` list in `_build_sliders()` (label, min, max) and nothing else;
  the merge logic already generalizes.
- Hover state (`self._hover_curves`) is rebuilt every `update()` call from
  whatever's currently plotted — if you add a second axes or secondary plot,
  give it its own hover list or the snap logic will search across unrelated
  curves.
- Headless testing pattern used during development (no display needed):
  `matplotlib.use("Agg")`, monkeypatch `plt.show = lambda *a, **k: None`,
  instantiate `ForcePlotApp()`, drive `.sliders[...].set_val()` /
  `._on_currents_change()` / `._on_hover(fake_event)` directly, then
  `app.fig.savefig(...)` and read the PNG back to check layout.

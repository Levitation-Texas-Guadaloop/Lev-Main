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
| `interactive_force_plot.py` | `ForcePlotApp` — matplotlib figure with 3 sliders (N_turns, ydepth_in, mass_kg), current-list and gap-range text boxes, hover tooltips, reset button. Non-slider `YokeGeometry` fields stay at their dataclass defaults. |

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

import Plotly from "plotly.js-basic-dist-min";
import "./style.css";

const $ = (s) => document.querySelector(s);
const fmt = (x, d = 2) => (x == null || !isFinite(x) ? "—" : Number(x).toFixed(d));

let DEFAULTS = null;
let state = null;
let tab = "force";
let seq = 0;
let timer = null;
let last = null;

// ---- saved defaults (per browser) --------------------------------------------

const SAVE_KEY = "hems.userDefaults.v1";
function loadSaved() {
  try {
    const v = JSON.parse(localStorage.getItem(SAVE_KEY));
    return v && typeof v === "object" ? { ...DEFAULTS, ...v } : null;
  } catch { return null; }
}
function baseState() { return structuredClone(loadSaved() ?? DEFAULTS); }
function refreshDefaultUI() {
  $("#factory").hidden = !loadSaved();
}

// ---- controls ---------------------------------------------------------------

const knobs = {};
function buildKnobs() {
  document.querySelectorAll(".knob").forEach((el) => {
    const { key, min, max, step, label } = el.dataset;
    el.innerHTML = `<label>${label}</label>
      <input type="range" min="${min}" max="${max}" step="${step}">
      <input type="text" inputmode="decimal">`;
    const [range, num] = el.querySelectorAll("input");
    const set = (v, from) => {
      v = Math.min(+max, Math.max(+min, v));
      state[key] = v;
      if (from !== range) range.value = v;
      if (from !== num) num.value = v;
      schedule();
    };
    range.addEventListener("input", () => set(+range.value, range));
    num.addEventListener("change", () => {
      const v = parseFloat(num.value);
      if (isFinite(v)) set(v); else num.value = state[key];
    });
    knobs[key] = { range, num };
  });
}

function parseNum(el, { positive = true } = {}) {
  const v = parseFloat(el.value);
  const ok = isFinite(v) && (!positive || v > 0);
  el.classList.toggle("bad", !ok && el.value.trim() !== "");
  return ok ? v : null;
}

function bindText(id, apply) {
  const el = $(id);
  el.addEventListener("focus", () => el.select());
  el.addEventListener("input", () => { apply(el); schedule(); });
  return el;
}

function syncControls() {
  for (const [k, { range, num }] of Object.entries(knobs)) { range.value = state[k]; num.value = state[k]; }
  $("#s0").value = state.s0_mm ?? "";
  $("#ceiling").value = state.ceiling_w;
  $("#currents").value = state.currents.join(", ");
  $("#gapmin").value = state.gap_min_mm;
  $("#gapmax").value = state.gap_max_mm;
  $("#rauto").checked = state.r_coil_ohm == null;
  if (state.r_coil_ohm != null) $("#rcoil").value = state.r_coil_ohm;
  $("#rcoil").classList.toggle("locked", state.r_coil_ohm == null);
}

function buildControls() {
  buildKnobs();
  bindText("#s0", (el) => { const v = el.value.trim() === "" ? null : parseNum(el); if (v !== null || el.value.trim() === "") state.s0_mm = v; });
  bindText("#ceiling", (el) => { const v = parseNum(el); if (v !== null) state.ceiling_w = v; });
  bindText("#gapmin", (el) => { const v = parseNum(el); if (v !== null) state.gap_min_mm = v; });
  bindText("#gapmax", (el) => { const v = parseNum(el); if (v !== null) state.gap_max_mm = v; });
  bindText("#currents", (el) => {
    const vals = el.value.split(",").map((t) => t.trim()).filter(Boolean).map(Number);
    const ok = vals.length > 0 && vals.every(isFinite);
    el.classList.toggle("bad", !ok);
    if (ok) state.currents = vals;
  });
  // typing a manual R flips auto off (like the desktop UI); checkbox back on re-enables auto
  $("#rcoil").addEventListener("focus", () => $("#rcoil").select());
  $("#rcoil").addEventListener("input", () => {
    const v = parseNum($("#rcoil"));
    if (v !== null) { state.r_coil_ohm = v; $("#rauto").checked = false; $("#rcoil").classList.remove("locked"); schedule(); }
  });
  $("#rauto").addEventListener("change", () => {
    if ($("#rauto").checked) { state.r_coil_ohm = null; $("#rcoil").classList.add("locked"); }
    else { state.r_coil_ohm = last ? last.R_ohm : 2.0; $("#rcoil").value = state.r_coil_ohm; $("#rcoil").classList.remove("locked"); }
    schedule();
  });
  $("#reset").addEventListener("click", () => { state = baseState(); syncControls(); schedule(); });
  $("#setdefault").addEventListener("click", () => {
    try { localStorage.setItem(SAVE_KEY, JSON.stringify(state)); } catch { showError("could not save (browser storage blocked)"); return; }
    refreshDefaultUI();
    const b = $("#setdefault"); b.textContent = "Saved ✓"; b.classList.add("saved");
    setTimeout(() => { b.textContent = "Set as default"; b.classList.remove("saved"); }, 1500);
  });
  $("#factory").addEventListener("click", () => {
    try { localStorage.removeItem(SAVE_KEY); } catch {}
    refreshDefaultUI(); state = structuredClone(DEFAULTS); syncControls(); schedule();
  });
  document.querySelectorAll("#tabs button").forEach((b) => b.addEventListener("click", () => setTab(b.dataset.tab)));
}

function setTab(t) {
  tab = t;
  document.querySelectorAll("#tabs button").forEach((b) => b.classList.toggle("active", b.dataset.tab === t));
  document.querySelectorAll(".tab").forEach((el) => el.classList.toggle("active", el.id === `tab-${t}`));
  document.querySelectorAll(".force-only").forEach((el) => (el.style.display = t === "force" ? "" : "none"));
  if (last) render(last);
}

// ---- data -------------------------------------------------------------------

function schedule() {
  clearTimeout(timer);
  timer = setTimeout(fetchModel, 60);
}

async function fetchModel() {
  const my = ++seq;
  try {
    const res = await fetch("/api/model", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(state) });
    const data = await res.json();
    if (my !== seq) return; // stale response; a newer request is in flight
    if (!res.ok) return showError(data.error);
    showError(null);
    last = data;
    if (data.r_auto) { $("#rcoil").value = data.R_ohm.toFixed(4); }
    render(data);
  } catch (e) {
    if (my === seq) { showError("API unreachable — is api_server.py running?"); }
  }
}

function showError(msg) {
  const el = $("#error"), st = $("#status");
  el.hidden = !msg; el.textContent = msg || "";
  st.textContent = msg ? "error" : "live"; st.classList.toggle("err", !!msg);
}

// ---- rendering --------------------------------------------------------------

function css(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }

function baseLayout(xTitle, yTitle) {
  const ink = css("--ink"), grid = css("--plot-grid");
  return {
    paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
    font: { color: ink, size: 14 },
    margin: { l: 80, r: 24, t: 24, b: 60 },
    xaxis: { title: { text: xTitle, standoff: 8 }, gridcolor: grid, zerolinecolor: grid },
    yaxis: { title: { text: yTitle, standoff: 8 }, gridcolor: grid, zerolinecolor: grid },
    legend: { orientation: "h", y: 1.12 },
    hovermode: "closest", uirevision: "keep",
    shapes: [], annotations: [],
  };
}

function curveColor(k, n) { // blue -> grey -> red (coolwarm-ish)
  const t = n <= 1 ? 0.5 : k / (n - 1);
  const lerp = (a, b, u) => Math.round(a + (b - a) * u);
  const [c0, c1, c2] = [[59, 76, 192], [221, 221, 221], [180, 4, 38]];
  const [a, b, u] = t < 0.5 ? [c0, c1, t * 2] : [c1, c2, (t - 0.5) * 2];
  return `rgb(${lerp(a[0], b[0], u)},${lerp(a[1], b[1], u)},${lerp(a[2], b[2], u)})`;
}

const vline = (x, color, dash) => ({ type: "line", xref: "x", yref: "paper", x0: x, x1: x, y0: 0, y1: 1, line: { color, width: 1.5, dash } });
const vlabel = (x, text, color, y) => ({ x, y, xref: "x", yref: "paper", text, showarrow: false, font: { color, size: 13 }, bgcolor: "rgba(127,127,127,0.12)", xanchor: "left", xshift: 4 });

function renderForce(d) {
  const n = d.force.curves.length;
  const traces = d.force.curves.map((c, k) => ({
    x: d.force.gap_mm, y: c.force_n, mode: "lines", name: `i = ${c.i_amp} A`,
    line: { width: 2.5, color: curveColor(k, n) },
    hovertemplate: `i = ${c.i_amp} A<br>z = %{x:.3f} mm<br>F = %{y:.1f} N<extra></extra>`,
  }));
  const L = baseLayout("Air gap z [mm]", "Total force, 4× per-leg-pair [N]");
  const { gap_min_mm: lo, gap_max_mm: hi } = d.params;
  // weight reference line
  L.shapes.push({ type: "line", xref: "paper", yref: "y", x0: 0, x1: 1, y0: d.weight_n, y1: d.weight_n, line: { color: css("--muted"), width: 1.2, dash: "dot" } });
  L.annotations.push({ xref: "paper", yref: "y", x: 1, y: d.weight_n, text: `weight ${d.weight_n.toFixed(0)} N`, showarrow: false, xanchor: "right", yanchor: "bottom", font: { color: css("--muted"), size: 12 } });
  if (d.g_eq_mm != null && d.g_eq_mm >= lo && d.g_eq_mm <= hi) {
    L.shapes.push(vline(d.g_eq_mm, css("--muted"), "dash"));
    L.annotations.push(vlabel(d.g_eq_mm, `eq. gap @ i=0: ${d.g_eq_mm.toFixed(2)} mm`, css("--muted"), 0.04));
  }
  const r = d.release;
  if (r.status === "ok" && r.s0_mm >= lo && r.s0_mm <= hi) {
    L.shapes.push(vline(r.s0_mm, css("--bad"), "dot"));
    L.annotations.push(vlabel(r.s0_mm, `s0 = ${r.s0_mm.toFixed(2)} mm → i_release = ${r.i_release_amp.toFixed(2)} A`, css("--bad"), 0.14));
  }
  Plotly.react("plot-force", traces, L, { responsive: true, displaylogo: false });
}

function renderPower(d) {
  const s = d.sweep;
  const L = baseLayout("Starting gap s0 [mm]", "Total release power, all yokes [W]");
  const traces = [{
    x: s.s_mm, y: s.p_total_w, mode: "lines", name: "release power", line: { width: 3, color: css("--accent") },
    hovertemplate: "s0 = %{x:.2f} mm<br>P = %{y:.0f} W<extra></extra>",
  }];
  L.shapes.push({ type: "line", xref: "paper", yref: "y", x0: 0, x1: 1, y0: d.params.ceiling_w, y1: d.params.ceiling_w, line: { color: css("--bad"), width: 2, dash: "dash" } });
  L.annotations.push({ xref: "paper", yref: "y", x: 0.99, y: d.params.ceiling_w, text: `ceiling ${d.params.ceiling_w} W`, showarrow: false, xanchor: "right", yanchor: "bottom", font: { color: css("--bad"), size: 13 } });
  if (s.s_mm.length) {
    const x0 = s.all_covered ? s.s_mm[0] : s.s_min_mm;
    if (x0 != null) L.shapes.push({ type: "rect", xref: "x", yref: "paper", x0, x1: s.s_mm[s.s_mm.length - 1], y0: 0, y1: 1, fillcolor: css("--ok"), opacity: 0.1, line: { width: 0 }, layer: "below" });
  }
  if (d.release.status === "ok") {
    traces.push({ x: [d.release.s0_mm], y: [d.release.total.peak_power_w], mode: "markers", name: "your s0", marker: { size: 12, color: d.release.covered ? css("--ok") : css("--bad"), line: { color: css("--ink"), width: 2 } }, hovertemplate: "s0 = %{x:.2f} mm<br>P = %{y:.0f} W<extra></extra>" });
  }
  Plotly.react("plot-power", traces, L, { responsive: true, displaylogo: false });
}

const card = (title, body, cls = "") => `<div class="card ${cls}"><h3>${title}</h3>${body}</div>`;

function vi(res) {
  const y = res.per_yoke, t = res.total;
  const row = (name, k) => `<tr><td>${name}</td><td>${fmt(y[k].voltage_v)} V</td><td>${fmt(y[k].current_a, 3)} A</td><td><b>${fmt(t[k].current_a, 2)} A</b></td></tr>`;
  return `<table><tr><th>2 coils</th><th>Voltage</th><th>I / yoke</th><th>I battery (×${res.n_yokes})</th></tr>${row("Series", "series")}${row("Parallel", "parallel")}</table>
    <p class="sub">Peak power: ${fmt(y.peak_power_w, 1)} W / yoke · <b>${fmt(t.peak_power_w, 1)} W total</b></p>`;
}

function renderCards(d) {
  const r = d.release, b = d.budget, c = d.coil;
  const releaseBig = r.status === "ok" ? `<div class="big">${fmt(r.i_release_amp, 3)} A</div><div class="sub">per leg coil at s0 = ${fmt(r.s0_mm, 3)} mm</div>` : `<div class="sub">${r.message}</div>`;
  const eq = d.g_eq_mm != null ? `${d.g_eq_mm.toFixed(3)} mm` : "no solution in range";

  const rDeriv = `<details><summary>How R is derived</summary>
    <p class="sub mono">MLT = 2·k·D + c·(2·w + 8·t_b + 2π·r̄)<br>
    k = ${c.k}, c = ${c.c} (empirical fit), D = ${fmt(d.params.ydepth_in, 1)} in, r̄ = ${fmt(c.r_bar_in, 4)} in<br>
    ${c.layers} layers × ${c.turns_per_layer} turns/layer<br>
    MLT = ${fmt(c.mlt_in, 2)} in → R = ρ'·N·MLT = ${fmt(c.R_auto_ohm, 4)} Ω</p></details>`;

  const forceCards = [
    card("Equilibrium gap (i = 0)", `<div class="big">${eq}</div><div class="sub">${fmt(d.params.mass_kg, 0)} kg → weight ${fmt(d.weight_n, 1)} N</div>`),
    card("Release current", releaseBig, r.status === "ok" ? "" : ""),
    card("Coil", `<div class="big">${fmt(d.R_ohm, 3)} Ω</div><div class="sub">per leg · ${d.r_auto ? "auto from yoke depth" : "manual override"} · N = ${fmt(d.params.N_turns, 0)}</div>${rDeriv}`),
  ];
  if (r.status === "ok") forceCards.push(card(`Power at s0 = ${fmt(r.s0_mm, 2)} mm`, vi(r)));
  $("#cards-force").innerHTML = forceCards.join("");

  const cover = r.status === "ok"
    ? card("Release vs. ceiling", `<div class="big">${r.covered ? "COVERED" : "NOT COVERED"}</div><div class="sub">need ${fmt(r.i_release_amp, 3)} A · ceiling allows ${fmt(b.i_coil_amp, 3)} A · headroom ${r.headroom_a >= 0 ? "+" : ""}${fmt(r.headroom_a, 3)} A</div>`, r.covered ? "ok" : "bad")
    : card("Release vs. ceiling", `<div class="sub">${r.message}</div>`);
  const s = d.sweep;
  const sMin = s.all_covered ? `every s0 up to ${fmt(d.g_eq_mm, 2)} mm` : s.s_min_mm != null ? `s0 ≥ ${fmt(s.s_min_mm, 2)} mm (up to eq. gap ${fmt(d.g_eq_mm, 2)} mm)` : "no s0 in range";
  $("#cards-power").innerHTML = [
    card(`Ceiling ${fmt(d.params.ceiling_w, 0)} W total`, `<div class="big">${fmt(b.i_coil_amp, 3)} A</div><div class="sub">max coil current · ${fmt(b.max_ampere_turns_per_coil, 0)} A-turns/coil · R = ${fmt(d.R_ohm, 3)} Ω</div>${vi(b)}`),
    cover,
    card("Ceiling covers release from", `<div class="big" style="font-size:22px">${sMin}</div>`),
    r.status === "ok" ? card(`Release draw @ s0 = ${fmt(r.s0_mm, 2)} mm`, vi(r)) : "",
  ].join("");
}

function render(d) {
  renderCards(d);
  if (tab === "force") renderForce(d); else renderPower(d);
}

// ---- boot -------------------------------------------------------------------

async function boot() {
  try {
    DEFAULTS = (await (await fetch("/api/health")).json()).defaults;
  } catch {
    $("#status").textContent = "API unreachable — start api_server.py"; $("#status").classList.add("err"); return;
  }
  state = baseState();
  buildControls();
  refreshDefaultUI();
  syncControls();
  setTab("force");
  schedule();
}
boot();

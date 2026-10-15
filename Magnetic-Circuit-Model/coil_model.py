"""
DC resistance model for a single yoke leg coil, as a function of leg depth D [in].

Source: "Coil Resistance Model -- Handoff" (Aditya Matam, 2026-10-12). Predicts the
resistance of an N-turn magnet-wire coil wound on a rectangular bobbin whose long sides
scale with the leg depth D (the "N-inch coil" / "N-inch yoke" naming used elsewhere in
this repo -- D corresponds to `YokeGeometry.ydepth_in` in reluctance_model.py).

Model: R(D) = rho' * N * MLT(D) * (1 + 0.00393*(T-20)) + R_leads, where MLT (mean length
per turn) is the perimeter of the winding cross-section:
    MLT = 2*k*D + 2*w + 8*t_b + 2*pi*r_bar
  - 2*k*D:      the two long (D-direction) sides, inflated by bulge factor k to capture
                observed pillowing (wire bowing outward on unsupported long spans).
  - 2*w:        the two short sides of the leg.
  - 8*t_b:      the bobbin wall enlarges the winding rectangle by t_b on every side.
  - 2*pi*r_bar: layer buildup -- each winding layer at radial offset r adds a rounded-
                corner perimeter contribution of ~2*pi*r; r_bar is the turn-weighted mean
                offset across all (possibly partial) layers.

NOTE (2026-10-13): fit to the D=1 (1.1 ohm) and D=9 (~3.9 ohm) coils with BOTH k (slope) and c
(scale on the fixed-length terms) -- see K_BULGE_DEFAULT/C_SCALE_DEFAULT. The text below is the
original single-k description.

Only `k` is fit to data so far (k=1.45 with t_b=1/8", from the D=9in coil alone; the D=1in coil is an
independent check). Geometry-only reference is k=1 (no pillowing correction).

This is explicitly an interim model ("imperfect, interpolated from two measurements") --
refit `k` (or move to `fit_k_power`) as more measurements land in measurements.csv.
"""

import csv
import math
import os

# ---------------------------------------------------------------------------
# Config -- change per coil design. Keep every constant here, in one place.
# ---------------------------------------------------------------------------
LEG_WIDTH_IN = 1.0  # w -- leg cross-section width [in]
BOBBIN_WALL_IN = 0.125  # t_b -- bobbin wall thickness [in] (confirmed 1/8")
WINDING_HEIGHT_IN = 1.5  # h -- winding window height [in] (~2in leg height, clearance top/bottom)
N_TURNS_DEFAULT = 250  # N -- turns per coil (confirmed, no extra turns)
WIRE_DIAM_IN = 0.043  # d -- 18 AWG heavy-build magnet wire, insulated OD [in]
RHO_OHM_PER_IN = 0.533e-3  # rho' -- 18 AWG copper resistance per unit length at 20degC [ohm/in]
# Two-parameter fit (fit_k_c) to the D=1 (1.1 ohm) and D=9 (3.9 ohm; measured 3.8-4.0) coils, with
# t_b = 1/8". k is a slope (pillowing) correction on the long sides; c scales the fixed-length
# terms (2w + 8*t_b + 2*pi*r_bar) -- c>1 absorbs unmodeled extra length (leads, bobbin flanges,
# looser winding). Empirical until more D values are measured.
K_BULGE_DEFAULT = 1.313  # k -- slope (D-direction) correction
C_SCALE_DEFAULT = 1.408  # c -- scale on the fixed-length terms
K_BULGE_STDERR_DEFAULT = 0.066  # formal (meter-sigma) se_k; 2 points, 2 params: no real dof
T_REF_C = 20.0  # reference temperature for rho' [degC]
TEMP_COEFF_PER_C = 0.00393  # copper resistance temperature coefficient [1/degC]
R_LEADS_OHM_DEFAULT = 0.0  # lead/probe resistance; ~0 with a 4-wire measurement

ACCEPTANCE_TOL_OHM = 0.2  # |measured - predicted| pass/fail threshold

METER_SIGMA_OHM = {"2wire": 0.1, "4wire": 0.02}  # default meter error by measurement method

DEFAULT_CSV_PATH = os.path.join(os.path.dirname(__file__), "measurements.csv")


def _layer_turn_counts(h, d, N):
    """Turns per winding layer: floor(h/d) per full layer, partial last layer. Returns a
    list of turn counts, one per layer, in winding order (innermost layer first)."""
    n_per_layer = max(int(h // d), 1)
    counts = []
    remaining = int(round(N))
    while remaining > 0:
        c = min(n_per_layer, remaining)
        counts.append(c)
        remaining -= c
    return counts


def mean_radial_offset_in(h, d, N):
    """r_bar -- turn-weighted mean radial offset of the winding buildup [in]. Layer k
    (1-indexed) sits at offset (k - 1/2)*d; weight each layer's offset by its turn count."""
    counts = _layer_turn_counts(h, d, N)
    total_offset = sum(c * (k - 0.5) * d for k, c in enumerate(counts, start=1))
    return total_offset / N


def mean_length_per_turn_in(D, w, t_b, h, N, d, k, c=C_SCALE_DEFAULT):
    """MLT(D) -- mean length per turn [in], excluding the rho'*N scale factor. `c` scales the
    fixed-length terms (c=1 is the pure-geometry value)."""
    r_bar = mean_radial_offset_in(h, d, N)
    return 2 * k * D + c * (2 * w + 8 * t_b + 2 * math.pi * r_bar)


def resistance(
    D,
    w=LEG_WIDTH_IN,
    t_b=BOBBIN_WALL_IN,
    h=WINDING_HEIGHT_IN,
    N=N_TURNS_DEFAULT,
    d=WIRE_DIAM_IN,
    rho=RHO_OHM_PER_IN,
    k=K_BULGE_DEFAULT,
    T=T_REF_C,
    R_leads=R_LEADS_OHM_DEFAULT,
    c=C_SCALE_DEFAULT,
):
    """DC resistance [ohm] of one leg coil with leg depth `D` [in]. See module docstring."""
    mlt = mean_length_per_turn_in(D, w, t_b, h, N, d, k, c)
    r20 = rho * N * mlt + R_leads
    return r20 * (1.0 + TEMP_COEFF_PER_C * (T - T_REF_C))


# ---------------------------------------------------------------------------
# Measurements
# ---------------------------------------------------------------------------

def load_measurements(csv_path=DEFAULT_CSV_PATH):
    """Reads measurements.csv -> list of dicts with D_in, R_ohm (float or None if
    pending), method, temp_C (float or None), notes."""
    rows = []
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            rows.append({
                "D_in": float(row["D_in"]),
                "R_ohm": float(row["R_ohm"]) if row["R_ohm"].strip() else None,
                "method": row["method"].strip(),
                "temp_C": float(row["temp_C"]) if row["temp_C"].strip() else None,
                "notes": row.get("notes", ""),
            })
    return rows


def _usable_rows(rows):
    """Rows with an actual measurement (R_ohm present) -- pending rows are excluded
    from any fit."""
    return [r for r in rows if r["R_ohm"] is not None]


# ---------------------------------------------------------------------------
# Fitting
# ---------------------------------------------------------------------------

def fit_k(
    rows=None,
    csv_path=DEFAULT_CSV_PATH,
    w=LEG_WIDTH_IN,
    t_b=BOBBIN_WALL_IN,
    h=WINDING_HEIGHT_IN,
    N=N_TURNS_DEFAULT,
    d=WIRE_DIAM_IN,
    rho=RHO_OHM_PER_IN,
    R_leads=R_LEADS_OHM_DEFAULT,
    c=C_SCALE_DEFAULT,
):
    """Weighted least-squares fit of the slope factor `k` (with `c` held fixed), weighting each measurement row
    by 1/sigma^2 (sigma = meter error for that row's method). R(D) is affine in k through
    a single term (2*k*D), so for fixed T this is 1-D weighted linear regression with a
    known (T-dependent) intercept:

        R_i = TF_i * (A0*k*D_i + C0) + noise,   A0 = 2*rho*N,  C0 = rho*N*(2w+8t_b+2*pi*r_bar) + R_leads

    Returns (k_hat, se_k, n_points_used).
    """
    if rows is None:
        rows = load_measurements(csv_path)
    rows = _usable_rows(rows)
    if not rows:
        raise ValueError("no measurements with R_ohm to fit against")

    r_bar = mean_radial_offset_in(h, d, N)
    A0 = 2 * rho * N
    C0 = rho * N * c * (2 * w + 8 * t_b + 2 * math.pi * r_bar) + R_leads

    sum_wx2 = 0.0
    sum_wxb = 0.0
    for row in rows:
        T = row["temp_C"] if row["temp_C"] is not None else T_REF_C
        TF = 1.0 + TEMP_COEFF_PER_C * (T - T_REF_C)
        sigma = METER_SIGMA_OHM.get(row["method"], 0.1)
        w_i = 1.0 / sigma**2

        x_i = TF * A0 * row["D_in"]  # dR/dk for this row
        b_i = row["R_ohm"] - TF * C0  # response with the known (k-independent) part removed

        sum_wx2 += w_i * x_i**2
        sum_wxb += w_i * x_i * b_i

    if sum_wx2 == 0.0:
        raise ValueError("degenerate fit (all D=0?)")

    k_hat = sum_wxb / sum_wx2
    se_k = math.sqrt(1.0 / sum_wx2)
    return k_hat, se_k, len(rows)


def fit_k_c(
    rows=None,
    csv_path=DEFAULT_CSV_PATH,
    w=LEG_WIDTH_IN,
    t_b=BOBBIN_WALL_IN,
    h=WINDING_HEIGHT_IN,
    N=N_TURNS_DEFAULT,
    d=WIRE_DIAM_IN,
    rho=RHO_OHM_PER_IN,
    R_leads=R_LEADS_OHM_DEFAULT,
):
    """Weighted least-squares fit of BOTH the slope correction `k` and the fixed-term scale
    `c`: R_i = TF_i * (A0*k*D_i + c*C0) + R_leads, with C0 = rho*N*(2w+8t_b+2*pi*r_bar). Linear
    in (k, c); needs >= 2 distinct D. With exactly 2 points the fit is exact (no residual
    freedom), so se's are formal (meter-sigma propagated) only. Returns (k, c, se_k, se_c, n)."""
    if rows is None:
        rows = load_measurements(csv_path)
    rows = _usable_rows(rows)
    if len({r["D_in"] for r in rows}) < 2:
        raise ValueError("fit_k_c needs measurements at >= 2 distinct D")

    A0 = 2 * rho * N
    C0 = rho * N * (2 * w + 8 * t_b + 2 * math.pi * mean_radial_offset_in(h, d, N))
    s11 = s12 = s22 = b1 = b2 = 0.0
    for row in rows:
        T = row["temp_C"] if row["temp_C"] is not None else T_REF_C
        TF = 1.0 + TEMP_COEFF_PER_C * (T - T_REF_C)
        w_i = 1.0 / METER_SIGMA_OHM.get(row["method"], 0.1) ** 2
        x1, x2, y = TF * A0 * row["D_in"], TF * C0, row["R_ohm"] - R_leads
        s11 += w_i * x1 * x1
        s12 += w_i * x1 * x2
        s22 += w_i * x2 * x2
        b1 += w_i * x1 * y
        b2 += w_i * x2 * y
    det = s11 * s22 - s12**2
    if det <= 0:
        raise ValueError("degenerate fit")
    k = (s22 * b1 - s12 * b2) / det
    c = (s11 * b2 - s12 * b1) / det
    return k, c, math.sqrt(s22 / det), math.sqrt(s11 / det), len(rows)


def fit_k_power(
    rows=None,
    csv_path=DEFAULT_CSV_PATH,
    w=LEG_WIDTH_IN,
    t_b=BOBBIN_WALL_IN,
    h=WINDING_HEIGHT_IN,
    N=N_TURNS_DEFAULT,
    d=WIRE_DIAM_IN,
    rho=RHO_OHM_PER_IN,
    R_leads=R_LEADS_OHM_DEFAULT,
    c=C_SCALE_DEFAULT,
):
    """Once >=3 measured points exist, fits k(D) = 1 + beta*D^p (nonlinear, 2 free
    params) and compares it to the constant-k fit via AIC. Returns a dict with both
    fits' params, residual sum of squares, AIC, and `power_law_better` (bool).

    Raises ValueError if fewer than 3 measured points are available.
    """
    from scipy.optimize import curve_fit

    if rows is None:
        rows = load_measurements(csv_path)
    rows = _usable_rows(rows)
    if len(rows) < 3:
        raise ValueError(
            f"need >=3 measured points to fit k(D)=1+beta*D^p, have {len(rows)}"
        )

    r_bar = mean_radial_offset_in(h, d, N)
    A0 = 2 * rho * N
    C0 = rho * N * c * (2 * w + 8 * t_b + 2 * math.pi * r_bar) + R_leads

    Ds = [row["D_in"] for row in rows]
    Rs = [row["R_ohm"] for row in rows]
    TFs = [
        1.0 + TEMP_COEFF_PER_C * ((row["temp_C"] if row["temp_C"] is not None else T_REF_C) - T_REF_C)
        for row in rows
    ]
    sigmas = [METER_SIGMA_OHM.get(row["method"], 0.1) for row in rows]

    def predict_const_k(k):
        return [TFs[i] * (A0 * k * Ds[i] + C0) for i in range(len(rows))]

    def predict_power_k(beta, p):
        return [TFs[i] * (A0 * (1.0 + beta * Ds[i] ** p) * Ds[i] + C0) for i in range(len(rows))]

    k_hat, _, _ = fit_k(rows=rows, w=w, t_b=t_b, h=h, N=N, d=d, rho=rho, R_leads=R_leads, c=c)
    rss_const = sum(((Rs[i] - predict_const_k(k_hat)[i]) / sigmas[i]) ** 2 for i in range(len(rows)))
    n_params_const = 1

    def model_power(D_arr, beta, p):
        return [
            TFs[i] * (A0 * (1.0 + beta * D ** p) * D + C0) for i, D in enumerate(D_arr)
        ]

    beta0, p0 = (K_BULGE_DEFAULT - 1.0), 0.0  # start near the constant-k solution (p=0 => flat)
    popt, _ = curve_fit(
        lambda D_arr, beta, p: model_power(D_arr, beta, p),
        Ds, Rs, p0=[beta0, p0], sigma=sigmas, absolute_sigma=True, maxfev=10000,
    )
    beta_hat, p_hat = popt
    rss_power = sum(
        ((Rs[i] - predict_power_k(beta_hat, p_hat)[i]) / sigmas[i]) ** 2 for i in range(len(rows))
    )
    n_params_power = 2

    n = len(rows)
    aic_const = n * math.log(rss_const / n) + 2 * n_params_const if rss_const > 0 else -math.inf
    aic_power = n * math.log(rss_power / n) + 2 * n_params_power if rss_power > 0 else -math.inf

    return {
        "k_const": k_hat,
        "rss_const": rss_const,
        "aic_const": aic_const,
        "beta_power": beta_hat,
        "p_power": p_hat,
        "rss_power": rss_power,
        "aic_power": aic_power,
        "power_law_better": aic_power < aic_const,
        "n_points": n,
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def report(csv_path=DEFAULT_CSV_PATH, out_png=None, k=K_BULGE_DEFAULT, k_se=K_BULGE_STDERR_DEFAULT, c=C_SCALE_DEFAULT, **resistance_kwargs):
    """Builds a (D, measured, predicted, residual, pass) table for every row in
    measurements.csv (pending rows show measured=None, pass=None), and optionally saves
    an R-vs-D plot with a +/-k_se uncertainty band to `out_png`.　Returns the table as a
    list of dicts (import pandas yourself if you want a DataFrame).
    """
    rows = load_measurements(csv_path)
    table = []
    for row in rows:
        predicted = resistance(row["D_in"], k=k, c=c, T=row["temp_C"] or T_REF_C, **resistance_kwargs)
        if row["R_ohm"] is None:
            table.append({**row, "predicted_ohm": predicted, "residual_ohm": None, "passed": None})
        else:
            residual = row["R_ohm"] - predicted
            table.append({
                **row,
                "predicted_ohm": predicted,
                "residual_ohm": residual,
                "passed": abs(residual) <= ACCEPTANCE_TOL_OHM,
            })

    if out_png is not None:
        import matplotlib
        matplotlib.use("Agg")
        from matplotlib import pyplot as plt

        D_curve = [0.25 * i for i in range(1, 41)]  # 0.25 .. 10 in
        R_curve = [resistance(D, k=k, c=c, **resistance_kwargs) for D in D_curve]
        A0 = 2 * RHO_OHM_PER_IN * resistance_kwargs.get("N", N_TURNS_DEFAULT)
        band = [A0 * D * k_se for D in D_curve]

        fig, ax = plt.subplots(figsize=(7, 5))
        ax.plot(D_curve, R_curve, color="C0", lw=2, label=f"prediction (k={k:.3f}, c={c:.3f})")
        ax.fill_between(
            D_curve,
            [r - b for r, b in zip(R_curve, band)],
            [r + b for r, b in zip(R_curve, band)],
            color="C0", alpha=0.15, label=f"+/- k uncertainty (se_k={k_se:.3f})",
        )
        measured = [r for r in table if r["R_ohm"] is not None]
        pending = [r for r in table if r["R_ohm"] is None]
        if measured:
            ax.scatter([r["D_in"] for r in measured], [r["R_ohm"] for r in measured],
                       color="C1", zorder=5, label="measured")
        if pending:
            ax.scatter([r["D_in"] for r in pending], [r["predicted_ohm"] for r in pending],
                       color="gray", marker="x", zorder=5, label="pending (predicted shown)")
        ax.set_xlabel("Leg depth D [in]")
        ax.set_ylabel("Coil resistance [ohm]")
        ax.set_title("Yoke leg coil resistance vs. depth")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(out_png, dpi=130)
        plt.close(fig)

    return table


if __name__ == "__main__":
    k_hat, c_hat, se_k, se_c, n = fit_k_c()
    print(f"fit_k_c(): k = {k_hat:.4f} +/- {se_k:.4f}, c = {c_hat:.4f} +/- {se_c:.4f}  (n={n})")
    print()

    table = report(out_png=os.path.join(os.path.dirname(__file__), "coil_model_report.png"))
    print(f"{'D [in]':>8} {'measured':>10} {'predicted':>10} {'residual':>10}  {'pass':>6}  notes")
    for row in table:
        meas = f"{row['R_ohm']:.3f}" if row["R_ohm"] is not None else "--"
        resid = f"{row['residual_ohm']:+.3f}" if row["residual_ohm"] is not None else "--"
        passed = "--" if row["passed"] is None else ("PASS" if row["passed"] else "FAIL")
        print(f"{row['D_in']:>8.2f} {meas:>10} {row['predicted_ohm']:>10.3f} {resid:>10}  {passed:>6}  {row['notes']}")

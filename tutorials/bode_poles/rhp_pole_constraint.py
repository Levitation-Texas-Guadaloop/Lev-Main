"""
The Bandwidth/Phase Constraint Imposed by an RHP Pole
======================================================

Plant: linearized maglev-type dynamics with a destabilizing "negative
stiffness" term, m*x'' = k_s*x + u   ->   P(s) = 1 / (m*s^2 - k_s)

This has poles at s = +-sqrt(k_s/m) = +-p. One RHP pole at p, one stable
pole at -p. Note P(jw) = 1/(-m*w^2 - k_s), which is a NEGATIVE REAL number
for every real w -> the plant phase is pinned at exactly -180 deg at ALL
frequencies. That single fact is why proportional-only control can never
truly stabilize it (shown below), and why a controller must inject its own
phase lead, and why that lead must do its work at a frequency above p.

We build:
  1. A "good" lead-compensator design with gain crossover comfortably above p.
  2. A "bad" design with gain crossover pulled below p (same lead shape,
     just re-centered lower) -> closed-loop poles computed directly to show
     it does NOT stabilize.
  3. The sensitivity function S(jw) = 1/(1+L(jw)) for the good design, with
     a numerical check of the Bode/Poisson sensitivity integral:
         integral_0^inf ln|S(jw)| dw  =  pi * p
     (valid here because L has relative degree >= 2 and no other RHP
     poles/NMP zeros) -- i.e. the "waterbed" that MUST appear somewhere in
     S is not a vague idea, it has a size, and that size is set by p.

Run: python3 rhp_pole_constraint.py
Outputs: three PNGs in the current directory.
"""

import numpy as np
import matplotlib.pyplot as plt

# ---------------------------------------------------------------
# 1. Plant
# ---------------------------------------------------------------
m = 1.0
p = 5.0                    # RHP pole frequency (rad/s)
k_s = p**2 * m

P_num = np.array([1.0])
P_den = np.array([m, 0.0, -k_s])       # m*s^2 - k_s


def poly_eval(coeffs, s):
    return np.polyval(coeffs, s)


def tf_response(num, den, w):
    s = 1j * w
    return poly_eval(num, s) / poly_eval(den, s)


# ---------------------------------------------------------------
# 2. Lead compensator: C(s) = K*(s+z)/(s+pc), pc/z = a
#    max phase lead occurs at wm = sqrt(z*pc)
# ---------------------------------------------------------------
def lead_compensator(wm, a):
    z = wm / np.sqrt(a)
    pc = wm * np.sqrt(a)
    C_num = np.array([1.0, z])          # K applied later
    C_den = np.array([1.0, pc])
    return C_num, C_den, z, pc


def set_unity_gain_at(C_num, C_den, P_num, P_den, w_target):
    """Scale controller gain K so |L(j*w_target)| = 1."""
    L_num0 = np.polymul(C_num, P_num)
    L_den0 = np.polymul(C_den, P_den)
    mag0 = np.abs(tf_response(L_num0, L_den0, w_target))
    K = 1.0 / mag0
    return K * C_num


a_ratio = 10.0

# ---- Good design: phase-lead centered ABOVE p ----
wm_good = 10.0                                    # > p = 5
Cn_good, Cd_good, z_good, pc_good = lead_compensator(wm_good, a_ratio)
Cn_good = set_unity_gain_at(Cn_good, Cd_good, P_num, P_den, wm_good)
K_good = Cn_good[0]

Ln_good = np.polymul(Cn_good, P_num)
Ld_good = np.polymul(Cd_good, P_den)

# ---- Bad design: same lead shape, centered BELOW p ----
wm_bad = 3.0                                      # < p = 5
Cn_bad, Cd_bad, z_bad, pc_bad = lead_compensator(wm_bad, a_ratio)
Cn_bad = set_unity_gain_at(Cn_bad, Cd_bad, P_num, P_den, wm_bad)
K_bad = Cn_bad[0]

Ln_bad = np.polymul(Cn_bad, P_num)
Ld_bad = np.polymul(Cd_bad, P_den)

# ---- Proportional-only (no lead at all) for comparison ----
K_prop = k_s * 1.5   # > k_s, best you can do is push poles to jw-axis
Ln_prop = np.array([K_prop])
Ld_prop = P_den


def closed_loop_poles(L_num, L_den):
    """Roots of 1 + L(s) = 0  ->  roots of (L_den + L_num_padded)."""
    n = max(len(L_num), len(L_den))
    num_p = np.pad(L_num, (n - len(L_num), 0))
    den_p = np.pad(L_den, (n - len(L_den), 0))
    char_poly = den_p + num_p
    return np.roots(char_poly)


poles_good = closed_loop_poles(Ln_good, Ld_good)
poles_bad = closed_loop_poles(Ln_bad, Ld_bad)
poles_prop = closed_loop_poles(Ln_prop, Ld_prop)

print("=== Closed-loop pole check ===")
print(f"Plant open-loop poles:            {np.roots(P_den)}")
print(f"Good design  (w_gc target=10>p):  {poles_good}")
print(f"  -> max Re(pole) = {poles_good.real.max():.4f}  "
      f"({'STABLE' if poles_good.real.max() < -1e-9 else 'UNSTABLE'})")
print(f"Bad design   (w_gc target=3<p):   {poles_bad}")
print(f"  -> max Re(pole) = {poles_bad.real.max():.4f}  "
      f"({'STABLE' if poles_bad.real.max() < -1e-9 else 'UNSTABLE'})")
print(f"Proportional-only (K={K_prop:.1f}): {poles_prop}")
print(f"  -> max Re(pole) = {poles_prop.real.max():.4f}  "
      f"({'STABLE' if poles_prop.real.max() < -1e-9 else 'UNSTABLE (or marginal)'})")

# ---------------------------------------------------------------
# 3. Frequency response of L(s) for good & bad design
# ---------------------------------------------------------------
w = np.logspace(-1, 3, 4000)

L_good = tf_response(Ln_good, Ld_good, w)
mag_good_db = 20 * np.log10(np.abs(L_good))
phase_good = np.unwrap(np.angle(L_good)) * 180 / np.pi

L_bad = tf_response(Ln_bad, Ld_bad, w)
mag_bad_db = 20 * np.log10(np.abs(L_bad))
phase_bad = np.unwrap(np.angle(L_bad)) * 180 / np.pi

P_only = tf_response(P_num, P_den, w)
phase_P_only = np.unwrap(np.angle(P_only)) * 180 / np.pi   # should be flat -180


def find_gain_crossover(w, mag_db):
    idx = np.argmin(np.abs(mag_db))
    return w[idx], idx


def find_phase_crossover(w, phase_deg):
    """Return None if phase never reaches -180 except at the boundaries."""
    interior = phase_deg[5:-5]
    idx_rel = np.argmin(np.abs(interior + 180))
    idx = idx_rel + 5
    if np.abs(phase_deg[idx] + 180) < 1.0:
        return w[idx], idx
    return None, None


w_gc_good, i_gc_good = find_gain_crossover(w, mag_good_db)
PM_good = 180 + phase_good[i_gc_good]
w_pc_good, i_pc_good = find_phase_crossover(w, phase_good)

w_gc_bad, i_gc_bad = find_gain_crossover(w, mag_bad_db)
PM_bad = 180 + phase_bad[i_gc_bad]

print("\n=== Frequency-domain margins ===")
print(f"Good design: w_gc = {w_gc_good:.2f} rad/s (p = {p}), PM = {PM_good:.1f} deg, "
      f"w_pc = {'none found in sweep (GM effectively unbounded for this idealized lead)' if w_pc_good is None else f'{w_pc_good:.2f}'}")
print(f"Bad design:  w_gc = {w_gc_bad:.2f} rad/s (p = {p}), PM = {PM_bad:.1f} deg  "
      f"-> crossover BELOW p despite nonzero PM: closed loop is still unstable "
      f"(see pole check above), confirming w_gc > p is a separate, necessary condition.")

# ---------------------------------------------------------------
# 4. Sensitivity function + Bode/Poisson integral check (good design)
# ---------------------------------------------------------------
def sensitivity(L_num, L_den, w):
    n = max(len(L_num), len(L_den))
    num_p = np.pad(L_num, (n - len(L_num), 0))
    den_p = np.pad(L_den, (n - len(L_den), 0))
    s = 1j * w
    L = poly_eval(num_p, s) / poly_eval(den_p, s)
    return 1.0 / (1.0 + L)


w_fine = np.linspace(1e-4, 4000, 400000)
S_good = sensitivity(Ln_good, Ld_good, w_fine)
lnS = np.log(np.abs(S_good))

integral_numeric = np.trapezoid(lnS, w_fine)
integral_theory = np.pi * p

print("\n=== Bode sensitivity integral check (good design) ===")
print(f"integral_0^inf ln|S(jw)| dw   numeric  = {integral_numeric:.4f}")
print(f"pi * p                        theory   = {integral_theory:.4f}")
print(f"(agreement confirms the 'waterbed' area pushed above 0 dB is fixed by p, "
      f"not by how cleverly C(s) is designed)")

S_db = 20 * np.log10(np.abs(sensitivity(Ln_good, Ld_good, w)))
peak_idx = np.argmax(S_db)

# ---------------------------------------------------------------
# 5. Plots
# ---------------------------------------------------------------
plt.rcParams.update({"font.size": 10})

# --- Figure 0: Bode of the plant alone, no controller ---
mag_P_db = 20 * np.log10(np.abs(P_only))

fig, (ax_mag, ax_ph) = plt.subplots(2, 1, figsize=(8, 7), sharex=True)

ax_mag.semilogx(w, mag_P_db, lw=2, color="#2563eb", label="Plant P(s)")
ax_mag.axhline(0, color="gray", ls="--", lw=1)
ax_mag.axvline(p, color="crimson", ls=":", lw=1.5, label=f"RHP pole p = {p} rad/s")
ax_mag.set_ylabel("Magnitude (dB)")
ax_mag.set_title("Plant alone: P(s) = 1 / (m*s^2 - k_s), no controller")
ax_mag.legend(loc="upper right", fontsize=8)
ax_mag.grid(True, which="both", alpha=0.3)

ax_ph.semilogx(w, phase_P_only, lw=2, color="#2563eb", label="Plant P(s) phase")
ax_ph.axhline(-180, color="gray", ls="--", lw=1)
ax_ph.axvline(p, color="crimson", ls=":", lw=1.5)
ax_ph.set_ylabel("Phase (deg)")
ax_ph.set_xlabel("Frequency w (rad/s)")
ax_ph.set_ylim(-200, -160)
ax_ph.annotate("phase pinned at -180 deg for all w\n(RHP pole, no zeros)",
               xy=(p, -180), xytext=(p * 2, -172),
               arrowprops=dict(arrowstyle="->", color="black"))
ax_ph.legend(loc="lower right", fontsize=8)
ax_ph.grid(True, which="both", alpha=0.3)

fig.tight_layout()
fig.savefig("fig0_bode_plant_only.png", dpi=150)
plt.close(fig)

# --- Figure 1: Bode of good design, with plant-alone phase overlay ---
fig, (ax_mag, ax_ph) = plt.subplots(2, 1, figsize=(8, 7), sharex=True)

ax_mag.semilogx(w, mag_good_db, lw=2, color="#2563eb", label="Loop L(s)=C(s)P(s)")
ax_mag.axhline(0, color="gray", ls="--", lw=1)
ax_mag.axvline(p, color="crimson", ls=":", lw=1.5, label=f"RHP pole p = {p} rad/s")
ax_mag.axvline(w_gc_good, color="green", ls=":", lw=1.5, label=f"w_gc = {w_gc_good:.1f} rad/s")
ax_mag.set_ylabel("Magnitude (dB)")
ax_mag.set_title("Good design: gain crossover placed above the RHP pole")
ax_mag.legend(loc="upper right", fontsize=8)
ax_mag.grid(True, which="both", alpha=0.3)

ax_ph.semilogx(w, phase_good, lw=2, color="#2563eb", label="Loop L(s) phase")
ax_ph.semilogx(w, phase_P_only, lw=1.5, color="#999999", ls="--",
               label="Plant alone: pinned at -180 deg")
ax_ph.axhline(-180, color="gray", ls="--", lw=1)
ax_ph.axvline(p, color="crimson", ls=":", lw=1.5)
ax_ph.axvline(w_gc_good, color="green", ls=":", lw=1.5)
ax_ph.annotate(f"PM = {PM_good:.0f} deg",
               xy=(w_gc_good, phase_good[i_gc_good]),
               xytext=(w_gc_good * 1.4, phase_good[i_gc_good] + 25),
               arrowprops=dict(arrowstyle="->", color="black"))
ax_ph.set_ylabel("Phase (deg)")
ax_ph.set_xlabel("Frequency w (rad/s)")
ax_ph.legend(loc="lower right", fontsize=8)
ax_ph.grid(True, which="both", alpha=0.3)

fig.tight_layout()
fig.savefig("fig1_bode_good_design.png", dpi=150)
plt.close(fig)

# --- Figure 2: Good vs bad crossover placement + pole-zero map ---
fig, (ax_cmp, ax_pz) = plt.subplots(1, 2, figsize=(11, 5))

ax_cmp.semilogx(w, mag_good_db, lw=2, color="#16a34a", label="Good: w_gc above p")
ax_cmp.semilogx(w, mag_bad_db, lw=2, color="#dc2626", label="Bad: w_gc below p")
ax_cmp.axhline(0, color="gray", ls="--", lw=1)
ax_cmp.axvline(p, color="black", ls=":", lw=1.5, label=f"p = {p} rad/s")
ax_cmp.set_xlabel("Frequency w (rad/s)")
ax_cmp.set_ylabel("Magnitude (dB)")
ax_cmp.set_title("Same lead shape, recentered:\ncrossover location relative to p decides everything")
ax_cmp.legend(fontsize=8)
ax_cmp.grid(True, which="both", alpha=0.3)

ax_pz.axvline(0, color="gray", lw=1)
ax_pz.axhline(0, color="gray", lw=1)
ax_pz.scatter(poles_good.real, poles_good.imag, marker="x", s=90, color="#16a34a",
              label="Good design closed-loop poles")
ax_pz.scatter(poles_bad.real, poles_bad.imag, marker="x", s=90, color="#dc2626",
              label="Bad design closed-loop poles")
ax_pz.scatter(poles_prop.real, poles_prop.imag, marker="x", s=90, color="#6b7280",
              label="Proportional-only closed-loop poles")
ax_pz.axvspan(0, max(ax_pz.get_xlim()[1], 6), color="red", alpha=0.06)
ax_pz.set_xlabel("Re(s)")
ax_pz.set_ylabel("Im(s)")
ax_pz.set_title("Closed-loop pole locations\n(shaded = unstable RHP)")
ax_pz.legend(fontsize=7, loc="upper left")
ax_pz.grid(True, alpha=0.3)

fig.tight_layout()
fig.savefig("fig2_good_vs_bad_polezero.png", dpi=150)
plt.close(fig)

# --- Figure 3: Sensitivity function + waterbed area ---
fig, ax = plt.subplots(figsize=(8, 5))
ax.semilogx(w, S_db, lw=2, color="#7c3aed")
ax.axhline(0, color="gray", ls="--", lw=1)
ax.axvline(p, color="crimson", ls=":", lw=1.5, label=f"RHP pole p = {p} rad/s")
ax.fill_between(w, 0, S_db, where=(S_db > 0), color="#7c3aed", alpha=0.25,
                 label="Amplification region (|S|>1)\nrequired by RHP pole")
ax.plot(w[peak_idx], S_db[peak_idx], "o", color="#7c3aed")
ax.annotate(f"peak |S| = {S_db[peak_idx]:.1f} dB",
            xy=(w[peak_idx], S_db[peak_idx]),
            xytext=(w[peak_idx] * 1.3, S_db[peak_idx] + 3),
            arrowprops=dict(arrowstyle="->", color="black"))
ax.set_xlabel("Frequency w (rad/s)")
ax.set_ylabel("|S(jw)| (dB)")
ax.set_title(
    f"Sensitivity waterbed: integral ln|S| = {integral_numeric:.2f}"
    f"  (theory: pi*p = {integral_theory:.2f})"
)
ax.legend(fontsize=8)
ax.grid(True, which="both", alpha=0.3)
fig.tight_layout()
fig.savefig("fig3_sensitivity_waterbed.png", dpi=150)
plt.close(fig)

print("\nSaved: fig0_bode_plant_only.png, fig1_bode_good_design.png, "
      "fig2_good_vs_bad_polezero.png, fig3_sensitivity_waterbed.png")

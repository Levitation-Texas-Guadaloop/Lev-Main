"""Generate SendCutSend lamination DXFs + acrylic glue-up jigs for the 1" sandwich test yoke.

Geometry (mm) follows SCS_Lamination_CrossSection.FCStd (127 wide, 1" legs, 1.5" base,
R1 corners) but split to match the EXISTING sandwich yokes:
    base U (1.5" base + 0.5" leg stubs) | 1" PM | 0.5" steel tip   (total 3.5")

Outputs (Vault/SCS_Laminations/):
  base_lamination.dxf         SCS, A1008 0.048" — order ~23
  pole_tip_lamination.dxf     SCS, A1008 0.048" — order ~46 (2 tips x ~20 + spares), 1" x 0.5"
  jig_tip_pocket.dxf          laser-cut 1/4" acrylic — cut 4 (stack = pocket depth)
  jig_tip_bottom.dxf          laser-cut 1/4" acrylic — cut 1
  jig_nest_cavity.dxf         laser-cut 1/4" acrylic — cut 3 (stack protrudes for top clamp)
  jig_nest_bottom.dxf         laser-cut 1/4" acrylic — cut 1
  preview.png

Run:  python3 scripts/gen_lamination_dxfs.py
"""

import math
import os

IN = 25.4
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SCS_Laminations")

# --- part geometry -----------------------------------------------------------
W = 5 * IN            # yoke width 127
H_BASE = 1.5 * IN     # base height 38.1
LEG = 1.0 * IN        # leg width / PM / tip size 25.4
H_STUB = 0.5 * IN    # steel leg stub under the PM (existing yokes)
H_PM = 1.0 * IN
H_TIP = 0.5 * IN     # steel tip above the PM (existing yokes)
R = 1.0               # corner radius (matches FreeCAD model)

HOLE_D = 6.6          # #10 bolt in 0.25" OD insulating sleeve, +0.010" clearance
HOLE_XY = 9.5         # hole centre from outer side and bottom edges (low-flux corner)

# --- jig geometry --------------------------------------------------------------
CLR = 0.15            # per-side clearance in acrylic pockets (tune after a test cut)
JIG_MARGIN = 12.0


# ===========================================================================
# Minimal DXF R12 writer (LINE / ARC / CIRCLE) — no dependencies
# ===========================================================================
class Dxf:
    def __init__(self):
        self.e = []

    def line(self, a, b):
        self.e.append(f"0\nLINE\n8\n0\n10\n{a[0]:.4f}\n20\n{a[1]:.4f}\n30\n0\n"
                      f"11\n{b[0]:.4f}\n21\n{b[1]:.4f}\n31\n0\n")

    def arc(self, c, r, a0, a1):
        self.e.append(f"0\nARC\n8\n0\n10\n{c[0]:.4f}\n20\n{c[1]:.4f}\n30\n0\n40\n{r:.4f}\n"
                      f"50\n{a0:.4f}\n51\n{a1:.4f}\n")

    def circle(self, c, r):
        self.e.append(f"0\nCIRCLE\n8\n0\n10\n{c[0]:.4f}\n20\n{c[1]:.4f}\n30\n0\n40\n{r:.4f}\n")

    def save(self, path):
        hdr = "0\nSECTION\n2\nHEADER\n9\n$ACADVER\n1\nAC1009\n9\n$INSUNITS\n70\n4\n0\nENDSEC\n"
        body = "0\nSECTION\n2\nENTITIES\n" + "".join(self.e) + "0\nENDSEC\n0\nEOF\n"
        with open(path, "w") as f:
            f.write(hdr + body)


def rrect(d, x0, y0, x1, y1, r):
    """Rounded rectangle, CCW."""
    if r <= 0:
        poly(d, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
        return
    d.line((x0 + r, y0), (x1 - r, y0)); d.arc((x1 - r, y0 + r), r, 270, 360)
    d.line((x1, y0 + r), (x1, y1 - r)); d.arc((x1 - r, y1 - r), r, 0, 90)
    d.line((x1 - r, y1), (x0 + r, y1)); d.arc((x0 + r, y1 - r), r, 90, 180)
    d.line((x0, y1 - r), (x0, y0 + r)); d.arc((x0 + r, y0 + r), r, 180, 270)


def poly(d, pts):
    for a, b in zip(pts, pts[1:] + pts[:1]):
        d.line(a, b)


# ===========================================================================
# Parts
# ===========================================================================
def base_lamination():
    """U profile: base + leg stubs, R1 on all corners (convex and the two concave ones)."""
    d = Dxf()
    yt = H_BASE + H_STUB                     # top of stubs
    xi0, xi1 = LEG, W - LEG                  # inner faces of the legs
    # outer bottom edge and right side
    d.line((R, 0), (W - R, 0)); d.arc((W - R, R), R, 270, 360)
    d.line((W, R), (W, yt - R)); d.arc((W - R, yt - R), R, 0, 90)
    # right stub top, inner face, concave fillet, window floor
    d.line((W - R, yt), (xi1 + R, yt)); d.arc((xi1 + R, yt - R), R, 90, 180)
    d.line((xi1, yt - R), (xi1, H_BASE + R)); d.arc((xi1 - R, H_BASE + R), R, 270, 360)
    d.line((xi1 - R, H_BASE), (xi0 + R, H_BASE)); d.arc((xi0 + R, H_BASE + R), R, 180, 270)
    # left inner face, left stub top, left side
    d.line((xi0, H_BASE + R), (xi0, yt - R)); d.arc((xi0 - R, yt - R), R, 0, 90)
    d.line((xi0 - R, yt), (R, yt)); d.arc((R, yt - R), R, 90, 180)
    d.line((0, yt - R), (0, R)); d.arc((R, R), R, 180, 270)
    for x in (HOLE_XY, W - HOLE_XY):
        d.circle((x, HOLE_XY), HOLE_D / 2)
    return d


def tip_lamination():
    d = Dxf()
    rrect(d, 0, 0, LEG, H_TIP, R)
    return d


def jig_tip_pocket():
    sx, sy = LEG + 2 * CLR, H_TIP + 2 * CLR
    m = JIG_MARGIN
    d = Dxf()
    rrect(d, 0, 0, sx + 2 * m, sy + 2 * m, 3)
    poly(d, [(m, m), (m + sx, m), (m + sx, m + sy), (m, m + sy)])
    return d


def jig_tip_bottom():
    sx, sy = LEG + 2 * CLR, H_TIP + 2 * CLR
    m = JIG_MARGIN
    d = Dxf()
    rrect(d, 0, 0, sx + 2 * m, sy + 2 * m, 3)
    d.circle((m + sx / 2, m + sy / 2), 4.0)        # push-out hole
    return d


def nest_outline(c):
    """Sandwich outline (base + PM + tip legs) grown by clearance c."""
    top = H_BASE + H_STUB + H_PM + H_TIP
    return [(-c, -c), (W + c, -c), (W + c, top + c), (W - LEG - c, top + c),
            (W - LEG - c, H_BASE + c), (LEG + c, H_BASE + c), (LEG + c, top + c), (-c, top + c)]


def jig_nest(bottom=False):
    m = JIG_MARGIN
    top = H_BASE + H_STUB + H_PM + H_TIP
    d = Dxf()
    rrect(d, -m, -m, W + m, top + m, 3)
    if bottom:
        for x in (HOLE_XY, W - HOLE_XY):          # bolts/pins pass through to locate the base
            d.circle((x, HOLE_XY), (HOLE_D + 0.2) / 2)
    else:
        # cavity = sandwich outline grown by CLR; the two window-floor corners are
        # rounded (RN > part fillet R) so they clear the base's concave R1 fillets
        c, RN = CLR, 1.5
        pts = nest_outline(c)
        for a, b in zip(pts[:3], pts[1:4]):                  # bottom, right side, right leg top
            d.line(a, b)
        xr, xl, yf = W - LEG - c, LEG + c, H_BASE + c
        d.line((xr, top + c), (xr, yf + RN)); d.arc((xr - RN, yf + RN), RN, 270, 360)
        d.line((xr - RN, yf), (xl + RN, yf)); d.arc((xl + RN, yf + RN), RN, 180, 270)
        d.line((xl, yf + RN), (xl, top + c)); d.line((xl, top + c), (-c, top + c))
        d.line((-c, top + c), (-c, -c))
    return d


def preview(path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    fig, ax = plt.subplots(1, 2, figsize=(12, 5))
    a = ax[0]
    a.add_patch(Rectangle((0, 0), W, H_BASE, fc="#9ca3af", ec="k"))
    for x in (0, W - LEG):
        a.add_patch(Rectangle((x, H_BASE), LEG, H_STUB, fc="#9ca3af", ec="k"))
        a.add_patch(Rectangle((x, H_BASE + H_STUB), LEG, H_PM, fc="#dc2626", ec="k", alpha=0.7))
        a.add_patch(Rectangle((x, H_BASE + H_STUB + H_PM), LEG, H_TIP, fc="#6b7280", ec="k"))
    for x in (HOLE_XY, W - HOLE_XY):
        a.add_patch(plt.Circle((x, HOLE_XY), HOLE_D / 2, fc="white", ec="k"))
    a.text(W / 2, H_BASE / 2, "base U lamination", ha="center")
    a.text(LEG / 2, H_BASE + H_STUB + H_PM / 2, "PM", ha="center", va="center", color="white")
    a.text(LEG / 2, H_BASE + H_STUB + H_PM + H_TIP / 2, "tip", ha="center", va="center", color="white")
    a.set_title("Sandwich stack-up (mm), one lamination plane")
    a.set_aspect("equal"); a.set_xlim(-10, W + 10); a.set_ylim(-10, 100); a.grid(alpha=0.3)

    b = ax[1]
    pts = nest_outline(CLR)
    b.fill(*zip(*pts), fc="#e0f2fe", ec="#0369a1", label="nest cavity (+0.15/side)")
    b.add_patch(Rectangle((-JIG_MARGIN, -JIG_MARGIN), W + 2 * JIG_MARGIN,
                          H_BASE + H_STUB + H_PM + H_TIP + 2 * JIG_MARGIN, fill=False, ec="k"))
    b.set_title("Assembly nest (acrylic): registers base, PM, tip")
    b.set_aspect("equal"); b.set_xlim(-20, W + 20); b.set_ylim(-20, 110); b.grid(alpha=0.3)
    b.legend(loc="lower center", fontsize=8)
    fig.tight_layout(); fig.savefig(path, dpi=120); plt.close(fig)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    files = {
        "base_lamination.dxf": base_lamination(),
        "pole_tip_lamination.dxf": tip_lamination(),
        "jig_tip_pocket.dxf": jig_tip_pocket(),
        "jig_tip_bottom.dxf": jig_tip_bottom(),
        "jig_nest_cavity.dxf": jig_nest(),
        "jig_nest_bottom.dxf": jig_nest(bottom=True),
    }
    for name, d in files.items():
        d.save(os.path.join(OUT, name))
        print("wrote", os.path.join(OUT, name))
    preview(os.path.join(OUT, "preview.png"))
    print("wrote", os.path.join(OUT, "preview.png"))

"""Parametric single-yoke Maxwell 3D magnetostatic model (rebuild of 1_Yoke_Forcings - Copy.aedt).

Geometry (mm): U-yoke = 2" base with a 3" x 0.5" pocket between the legs, two legs (each an N52 magnet
plus a steel cap), a coil around each magnet, and a steel track above. The coil z-range is tied to the
base geometry (pocket floor / pole face), so it cannot poke above the pole face. Design variables:
GapHeight, currL, currR (amps, x NTURNS), rollDeg. GapHeight is measured from pole face to track.

Run:  .venv\\Scripts\\python scripts\\yoke_model.py [--sweep] [--gap MM] [--cores N] [--gpus N]
Close any open AEDT window first (Student license = one session).
"""
import argparse
import math
import os

from ansys.aedt.core import Maxwell3d

# ---- parameters (mm unless noted) -----------------------------------------------------------
IN = 25.4
DEPTH = 1 * IN              # yoke depth along y
LEG = 1 * IN                # leg footprint (x and y)
SPAN = 5 * IN               # base length along x (outer edge to outer edge)
BASE_H = 2 * IN             # base height at the legs (z = -11.75 .. 39.05)
BASE_Z0 = -11.75
POCKET_D = 0.5 * IN         # pocket depth between the legs (1.5" of steel left underneath)
MAG_H = 1 * IN              # magnet height
CAP_H = 0.5 * IN            # steel cap on top of each magnet
COIL_T = 7.0                # coil radial thickness
COIL_CLEAR = 3.0            # clearance between leg and coil inner wall
COIL_ABOVE_FLOOR = 4.47     # coil bottom above the pocket floor (original: z 30.82 over floor at 26.35)
COIL_BELOW_FACE = 3.15      # coil top below the pole face (original: z 74.00 under face at 77.15)
TRACK = (12 * IN, 36 * IN, 0.25 * IN)  # x (across the legs), y (along the rail, = yoke depth direction), z (thickness)
NTURNS = 250
HC = 955000                 # A/m, N52 magnet coercivity (mu_r = 1.07)
REGION_PAD = [88.9, 88.9, 152.4, 152.4, 50.05, 50.05]  # -x,+x,-y,+y,-z,+z absolute offsets

STEEL = "steel_1010"   # nonlinear BH, closest syslib match to the original "1018 CS"/"1020 CS" (PersonalLib)

DEFAULTS = {"GapHeight": "5mm", "currL": "0A", "currR": "0A", "rollDeg": "0deg"}


MU0 = 4e-7 * math.pi
BR_LINEAR, MU_R_LINEAR = 1.45, 1.04   # "linear" magnet: sintered N52 at 20 C (Arnold N52: Br 1.450 T, recoil mu_r 1.041)
ARNOLD_LIB, ARNOLD_HC = "Arnold_Magnetics_N52_20C", 880000   # library demag table; |Hc| from its header


def define_magnets(m, magnet):
    """Create N52_Mdown (left, S face up) and N52_Mup (right, N face up).

    magnet = "legacy": mu_r 1.07, Hc 955 kA/m, i.e. Br = 1.284 T (the original project's values; ~N35-class).
             "linear": Br = BR_LINEAR, mu_r = MU_R_LINEAR, Hc = Br / (mu0 * mu_r). Do NOT use HcB here: a linear
                       material needs the extrapolated intercept (~1.1 MA/m), not the 0.9-1.0 MA/m knee value.
             "arnold": clone of the library's nonlinear Arnold N52 20 C demag table, re-pointed along z.
    Maxwell wants a coercivity magnitude <= 0; M points opposite the Hc direction vector.
    """
    for name, hc_dir in (("N52_Mdown", -1), ("N52_Mup", 1)):
        if magnet == "arnold":
            mat = m.materials.duplicate_material(ARNOLD_LIB, name)
            mat.set_magnetic_coercivity(-ARNOLD_HC, 0, 0, hc_dir)   # keeps the library B-H table
            continue
        if magnet == "linear":
            mu_r, hc = MU_R_LINEAR, BR_LINEAR / (MU0 * MU_R_LINEAR)
        elif magnet == "legacy":
            mu_r, hc = 1.07, HC
        else:
            raise ValueError(f"unknown magnet model {magnet!r}")
        mat = m.materials.add_material(name)
        mat.permeability = mu_r
        mat.conductivity = 667000
        mat.set_magnetic_coercivity(-hc, 0, 0, hc_dir)


def stack_slices(n, slice_mm=IN, glue_mm=0.0):
    """y-intervals for n steel slices of slice_mm, separated by glue_mm (an air gap standing in for the epoxy
    line), centred on y = 0. This is the "pseudo-laminated" yoke: n 1-inch slices side by side along the rail."""
    total = n * slice_mm + (n - 1) * glue_mm
    y, out = -total / 2, []
    for _ in range(n):
        out.append((y, y + slice_mm))
        y += slice_mm + glue_mm
    return out


def lamination_sheets(depth_mm, t_mm, coat_mm):
    """Explicit-sheet plan: sheets of thickness t_mm with insulating gaps spanning exactly depth_mm.

    n is the sheet count that best matches a pitch of t + coat; the gap is then stretched so the stack fills the
    depth exactly (same envelope as the solid yoke). Returns (intervals, n, gap_mm, stacking_factor)."""
    n = max(1, round((depth_mm + coat_mm) / (t_mm + coat_mm)))
    while n > 1 and n * t_mm > depth_mm:
        n -= 1
    if n == 1:                                   # sheet as thick as the whole depth: nothing to laminate
        return [(-depth_mm / 2, depth_mm / 2)], 1, 0.0, 1.0
    gap = (depth_mm - n * t_mm) / (n - 1)
    y, out = -depth_mm / 2, []
    for _ in range(n):
        out.append((y, y + t_mm))
        y += t_mm + gap
    return out, n, gap, n * t_mm / depth_mm


def make_lamination_material(m, base, sf, direction="V(2)"):
    """Homogenized lamination: clone `base`, flag it as laminated with stacking factor sf. V(2) = global y, the
    direction the sheets are stacked in. Maxwell scales the steel's effective cross-section by sf (magnetostatic,
    eddy current and transient solvers); plotted B is then the average over steel and insulation."""
    name = "steel_lam"
    mat = m.materials.duplicate_material(base, name)
    mat.stacking_type = "Lamination"
    mat.stacking_factor = sf
    mat.stacking_direction = direction
    return name


def build(project, design="Yoke", version="2025.2", cores=None, gpus=None, non_graphical=True, magnet="legacy",
          track=TRACK, slices=None, lam_sf=None):
    """slices: list of (y_lo, y_hi) steel intervals along y (default one 1-inch slice). Magnets and the coil span the
    whole envelope, so one coil wraps the entire leg however many slices there are.
    lam_sf: if set, the yoke steel (base and caps, not the track) is a homogenized lamination with that stacking factor."""
    # always rebuild from scratch: stale boundaries/materials in an old .aedt clash with the new ones
    import shutil
    for f in (project, project + ".lock"):
        if os.path.isfile(f):
            os.remove(f)
    shutil.rmtree(project[:-5] + ".aedtresults", ignore_errors=True)
    m = Maxwell3d(project=project, design=design, solution_type="Magnetostatic",
                  version=version, student_version=True, non_graphical=non_graphical, new_desktop=True)
    m.modeler.model_units = "mm"
    for k, v in DEFAULTS.items():
        m[k] = v
    mod = m.modeler

    # materials
    define_magnets(m, magnet)

    # yoke
    x0 = -4.6                                   # left edge of yoke
    xc = x0 + SPAN / 2                          # yoke centre (x)
    slices = slices or [(-DEPTH / 2, DEPTH / 2)]
    y_lo, y_hi = slices[0][0], slices[-1][1]    # envelope of the yoke along y
    depth = y_hi - y_lo
    yoke_steel = make_lamination_material(m, STEEL, lam_sf) if lam_sf else STEEL
    z_mag = BASE_Z0 + BASE_H                    # 39.05, magnet bottom
    z_top = z_mag + MAG_H + CAP_H               # 77.15, pole face
    z_floor = z_mag - POCKET_D                  # 26.35, pocket floor
    legs = {"L": x0, "R": x0 + SPAN - LEG}
    base_names, cap_names = [], []
    for i, (ya, yb) in enumerate(slices):
        sfx = "" if len(slices) == 1 else f"_{i + 1}"
        mod.create_box([x0, ya, BASE_Z0], [SPAN, yb - ya, BASE_H - POCKET_D], f"Base{sfx}", yoke_steel)
        blocks = []
        for side, lx in legs.items():           # full-height steel under each leg, pocket between them
            blocks.append(mod.create_box([lx, ya, z_floor], [LEG, yb - ya, POCKET_D], f"BaseBlock{side}{sfx}",
                                         yoke_steel).name)
        mod.unite([f"Base{sfx}"] + blocks)
        base_names.append(f"Base{sfx}")
        for side, lx in legs.items():
            cap_names.append(mod.create_box([lx, ya, z_mag + MAG_H], [LEG, yb - ya, CAP_H], f"Cap{side}{sfx}",
                                            yoke_steel).name)
    coil_z0 = z_floor + COIL_ABOVE_FLOOR
    coil_h = (z_top - COIL_BELOW_FACE) - coil_z0
    for side, lx in legs.items():
        # left magnet: south face up (M down); right: north face up (M up), as in the original.
        # One magnet bar per leg across the whole envelope (it spans any gaps between slices).
        mat = "N52_Mdown" if side == "L" else "N52_Mup"
        mod.create_box([lx, y_lo, z_mag], [LEG, depth, MAG_H], f"Magnet{side}", mat)

    # coils + current sheets (amp-turns = current * NTURNS). Each coil is one rectangular loop around the whole
    # leg (all slices), not one per slice.
    coils = []
    for side, lx in legs.items():
        cx, cy = lx + LEG / 2, (y_lo + y_hi) / 2
        w_out, w_in = LEG + 2 * (COIL_CLEAR + COIL_T), LEG + 2 * COIL_CLEAR
        d_out, d_in = depth + 2 * (COIL_CLEAR + COIL_T), depth + 2 * COIL_CLEAR
        outer = mod.create_box([cx - w_out / 2, cy - d_out / 2, coil_z0], [w_out, d_out, coil_h],
                               f"Coil{side}", "copper")
        inner = mod.create_box([cx - w_in / 2, cy - d_in / 2, coil_z0 - 1], [w_in, d_in, coil_h + 2], "tmp")
        mod.subtract(outer, inner, keep_originals=False)
        sheet = mod.create_rectangle("YZ", [cx, cy - d_out / 2, coil_z0], [COIL_T, coil_h], f"Coil{side}Section")
        m.assign_current(sheet, amplitude=f"curr{side}*{NTURNS}", solid=False,
                         swap_direction=(side == "R"), name=f"Current{side}")
        coils.append(outer.name)

    # track, hung off a roll CS so rollDeg is parametric (rotation about global Y at gap midplane)
    cs = mod.create_coordinate_system(origin=[xc, 0, f"{z_top}mm+GapHeight"], mode="zyz",
                                      phi=0, theta="rollDeg", psi=0, name="TrackCS")
    mod.set_working_coordinate_system(cs.name)
    mod.create_box([-track[0] / 2, -track[1] / 2, 0], list(track), "Track", STEEL)
    mod.set_working_coordinate_system("Global")

    mod.create_region(REGION_PAD, is_percentage=False)

    # force / torque on the moving (yoke) body; torque about -Y like the original RelativeCS2
    moving = base_names + ["MagnetL", "MagnetR"] + cap_names + coils
    mod.create_coordinate_system(origin=[xc, 0, z_top], mode="axis", x_pointing=[0, -1, 0],
                                 y_pointing=[1, 0, 0], name="TorqueCS")
    m.assign_force(moving, force_name="YokeForce")
    m.assign_torque(moving, coordinate_system="TorqueCS", axis="X", torque_name="YokeTorque")

    # setup
    s = m.create_setup("Setup1")
    s.props.update({"MaximumPasses": 15, "PercentRefinement": 30, "PercentError": 1,
                    "NonLinearResidual": 0.001})
    s.update()
    if cores or gpus:
        m.set_custom_hpc_options(cores=cores, tasks=1, gpus=gpus)
    return m


def add_gap_sweep(m, start="2mm", stop="15mm", step="1mm"):
    return m.parametrics.add("GapHeight", start, stop, step, variation_type="LinearStep",
                             name="GapSweep")


def solve_point(m, gap_mm):
    """Set GapHeight, solve Setup1, return (Fz in N, peak |B| in the track in T; nan if the field read fails)."""
    m["GapHeight"] = f"{gap_mm}mm"
    if not m.analyze_setup("Setup1"):
        raise RuntimeError(f"solve failed at {gap_mm} mm: " +
                           str(list(m.odesktop.GetMessages(m.project_name, m.design_name, 2))))
    d = m.post.get_solution_data(["YokeForce.Force_z"], setup_sweep_name="Setup1 : LastAdaptive")
    fz = float(d.get_expression_data("YokeForce.Force_z")[1][0])
    try:
        b = float(m.post.get_scalar_field_value("Mag_B", scalar_function="Maximum",
                                                solution="Setup1 : LastAdaptive",
                                                object_name="Track", object_type="volume"))
    except Exception:
        b = math.nan
    return fz, b


def print_results(m):
    """Print Fz and roll torque for every GapHeight variation (mm)."""
    d = m.post.get_solution_data(["YokeForce.Force_z", "YokeTorque.Torque"],
                                 setup_sweep_name="Setup1 : LastAdaptive",
                                 variations={"GapHeight": ["All"], "currL": ["All"], "currR": ["All"],
                                             "rollDeg": ["All"]})
    gaps = d.variations if False else None
    fz = d.get_expression_data("YokeForce.Force_z")[1]
    tq = d.get_expression_data("YokeTorque.Torque")[1]
    for v, f, t in zip(d.variations, fz, tq):
        print(f"GapHeight={v.get('GapHeight')}  Fz={f:9.3f} N  Torque={t:9.5f} N*m")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", action="store_true", help="run the GapHeight sweep (2-15 mm)")
    ap.add_argument("--cores", type=int, default=4, help="Student license caps at 4")
    ap.add_argument("--gpus", type=int)
    ap.add_argument("--gap", type=float, help="single-point GapHeight in mm (default 5)")
    ap.add_argument("--magnet", choices=["legacy", "linear", "arnold"], default="legacy",
                    help="magnet material model (default legacy = original project values, Br 1.284 T)")
    ap.add_argument("--project", default=os.path.join(os.path.dirname(__file__), "..", "sim", "yoke.aedt"))
    a = ap.parse_args()
    os.makedirs(os.path.dirname(os.path.abspath(a.project)), exist_ok=True)
    m = build(os.path.abspath(a.project), cores=a.cores, gpus=a.gpus, magnet=a.magnet)
    if a.gap is not None:
        m["GapHeight"] = f"{a.gap}mm"
    try:
        if a.sweep:
            sweep = add_gap_sweep(m)
            if not sweep.analyze():
                print("SWEEP FAILED:", list(m.odesktop.GetMessages(m.project_name, m.design_name, 2)))
                raise SystemExit(1)
        else:
            if not m.analyze_setup("Setup1"):
                print("SOLVE FAILED:", list(m.odesktop.GetMessages(m.project_name, m.design_name, 2)))
                raise SystemExit(1)
        print_results(m)
        m.save_project()
    finally:
        m.release_desktop(close_projects=True, close_desktop=True)

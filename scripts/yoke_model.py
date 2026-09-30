"""Parametric single-yoke Maxwell 3D magnetostatic model (rebuild of 1_Yoke_Forcings - Copy.aedt).

Geometry (mm): U-yoke = base block + two legs, each leg = N52 magnet + steel cap, a coil around each
magnet, and a steel track above. Design variables: GapHeight, currL, currR (amps, x NTURNS), rollDeg.

Run:  .venv\\Scripts\\python scripts\\yoke_model.py [--sweep] [--cores N] [--gpus N]
Close any open AEDT window first (Student license = one session).
"""
import argparse
import os

from ansys.aedt.core import Maxwell3d

# ---- parameters (mm unless noted) -----------------------------------------------------------
IN = 25.4
DEPTH = 1 * IN              # yoke depth along y
LEG = 1 * IN                # leg footprint (x and y)
SPAN = 5 * IN               # base length along x (outer edge to outer edge)
BASE_H = 43.18              # base block height (z = -11.75 .. 39.05)
BASE_Z0 = -11.75
MAG_H = 1 * IN              # magnet height
CAP_H = 0.5 * IN            # steel cap on top of each magnet
COIL_T = 7.0                # coil radial thickness
COIL_CLEAR = 3.0            # clearance between leg and coil inner wall
COIL_Z0 = 39.05             # coil sits on the base top (original overlapped the base, solver rejects it)
COIL_H = 74.0 - COIL_Z0     # coil top at z = 74
TRACK = (7 * IN, 12 * IN, 0.25 * IN)   # x, y, z size
NTURNS = 250
HC = 955000                 # A/m, N52 magnet coercivity (mu_r = 1.07)
REGION_PAD = [88.9, 88.9, 152.4, 152.4, 50.05, 50.05]  # -x,+x,-y,+y,-z,+z absolute offsets

STEEL = "steel_1010"   # nonlinear BH, closest syslib match to the original "1018 CS"/"1020 CS" (PersonalLib)

DEFAULTS = {"GapHeight": "5mm", "currL": "0A", "currR": "0A", "rollDeg": "0deg"}


def build(project, design="Yoke", version="2025.2", cores=None, gpus=None, non_graphical=True):
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
    for name, sign in (("N52_up", 1), ("N52_down", -1)):
        mat = m.materials.add_material(name)
        mat.permeability = 1.07
        mat.conductivity = 667000
        mat.set_magnetic_coercivity(sign * HC, 0, 0, 1)

    # yoke
    x0 = -4.6                                   # left edge of yoke
    xc = x0 + SPAN / 2                          # yoke centre (x)
    y0 = -DEPTH / 2
    z_mag = BASE_Z0 + BASE_H                    # 39.05, magnet bottom
    z_top = z_mag + MAG_H + CAP_H               # 77.15, yoke top
    mod.create_box([x0, y0, BASE_Z0], [SPAN, DEPTH, BASE_H], "Base", STEEL)
    legs = {"L": x0, "R": x0 + SPAN - LEG}
    for side, lx in legs.items():
        mat = "N52_up" if side == "L" else "N52_down"
        mod.create_box([lx, y0, z_mag], [LEG, DEPTH, MAG_H], f"Magnet{side}", mat)
        mod.create_box([lx, y0, z_mag + MAG_H], [LEG, DEPTH, CAP_H], f"Cap{side}", STEEL)

    # coils + current sheets (amp-turns = current * NTURNS)
    coils = []
    for side, lx in legs.items():
        cx, cy = lx + LEG / 2, 0.0
        w_out = LEG + 2 * (COIL_CLEAR + COIL_T)
        w_in = LEG + 2 * COIL_CLEAR
        outer = mod.create_box([cx - w_out / 2, cy - w_out / 2, COIL_Z0], [w_out, w_out, COIL_H],
                               f"Coil{side}", "copper")
        inner = mod.create_box([cx - w_in / 2, cy - w_in / 2, COIL_Z0 - 1], [w_in, w_in, COIL_H + 2], "tmp")
        mod.subtract(outer, inner, keep_originals=False)
        sheet = mod.create_rectangle("YZ", [cx, cy - w_out / 2, COIL_Z0], [COIL_T, COIL_H], f"Coil{side}Section")
        m.assign_current(sheet, amplitude=f"curr{side}*{NTURNS}", solid=False,
                         swap_direction=(side == "R"), name=f"Current{side}")
        coils.append(outer.name)

    # track, hung off a roll CS so rollDeg is parametric (rotation about global Y at gap midplane)
    cs = mod.create_coordinate_system(origin=[xc, 0, f"{z_top}mm+GapHeight"], mode="zyz",
                                      phi=0, theta="rollDeg", psi=0, name="TrackCS")
    mod.set_working_coordinate_system(cs.name)
    mod.create_box([-TRACK[0] / 2, -TRACK[1] / 2, 0], list(TRACK), "Track", STEEL)
    mod.set_working_coordinate_system("Global")

    mod.create_region(REGION_PAD, is_percentage=False)

    # force / torque on the moving (yoke) body; torque about -Y like the original RelativeCS2
    moving = ["Base", "MagnetL", "MagnetR", "CapL", "CapR"] + coils
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
    ap.add_argument("--project", default=os.path.join(os.path.dirname(__file__), "..", "sim", "yoke.aedt"))
    a = ap.parse_args()
    os.makedirs(os.path.dirname(os.path.abspath(a.project)), exist_ok=True)
    m = build(os.path.abspath(a.project), cores=a.cores, gpus=a.gpus)
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

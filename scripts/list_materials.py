"""List every material name AEDT knows about and write it to scripts/materials_list.txt.

Sections: materials in the installed AEDT libraries, and materials defined in the open project
(project-level materials such as "1018 CS" never appear in the library list).

Run:  .venv\\Scripts\\python scripts\\list_materials.py [--bh REGEX] [--out PATH]
Close any open AEDT window first (Student license = one session).

--bh REGEX  also tag library names matching REGEX with their permeability type ("nonlinear" means the
            material carries a B-H curve). Opens each match, so keep the regex narrow (e.g. "steel_|1018|A36").
            Comma-named structural entries are skipped; any other name that cannot be read is tagged "?".
"""
import argparse
import os
import re
import tempfile

import psutil
from ansys.aedt.core import Maxwell3d

os.environ.setdefault("ANSYSEM_ROOT252", r"F:\Ansys2\ANSYS Inc\ANSYS Student\v252\AnsysEM")


def permeability_type(m, name):
    # "Copper, C10200, soft" style names are structural-library entries: pyaedt cannot load them as
    # Maxwell materials (it logs an API error per name) and they carry no B-H data, so don't probe.
    if "," in name:
        return "structural, skipped"
    try:
        return str(m.materials[name].permeability.type)
    except Exception:
        return "?"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bh", metavar="REGEX", help="tag matching library names with their permeability type")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "materials_list.txt"))
    a = ap.parse_args()

    # Student allows one AEDT session; an orphaned headless process makes design creation fail and hang.
    running = [p for p in psutil.process_iter(["name", "pid"]) if (p.info["name"] or "").lower().startswith("ansysedt")]
    if running:
        raise SystemExit("AEDT is already running (PID " + ", ".join(str(p.info["pid"]) for p in running) +
                         "). Close it first: Get-Process ansys* | Stop-Process -Force")

    m = Maxwell3d(project=os.path.join(tempfile.gettempdir(), "list_materials.aedt"), design="mat",
                  solution_type="Magnetostatic", version="2025.2", student_version=True,
                  non_graphical=True, new_desktop=True)
    try:
        library = sorted(set(m.materials.mat_names_aedt), key=str.lower)
        project = sorted(m.materials.material_keys, key=str.lower)
        rx = re.compile(a.bh, re.I) if a.bh else None

        lines = [f"# AEDT materials, version {m.aedt_version_id}",
                 f"# library: {len(library)}   project: {len(project)}", "", "## Library"]
        for n in library:
            tag = f"  [{permeability_type(m, n)}]" if rx and rx.search(n) else ""
            lines.append(n + tag)
        lines += ["", "## Project (defined in this project only)"]
        lines += [n + (f"  [{permeability_type(m, n)}]" if rx and rx.search(n) else "") for n in project]

        with open(a.out, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"wrote {len(library)} library + {len(project)} project materials to {a.out}")
    finally:
        m.release_desktop(close_projects=True, close_desktop=True)

"""Smoke test: launch Maxwell 3D (Student 2025 R2), draw a box, read it back."""
import os
import tempfile

from ansys.aedt.core import Maxwell3d

os.environ.setdefault(
    "ANSYSEM_ROOT252", r"F:\Ansys2\ANSYS Inc\ANSYS Student\v252\AnsysEM"
)

project = os.path.join(tempfile.gettempdir(), "pyaedt_smoke.aedt")

m3d = Maxwell3d(
    project=project,
    version="2025.2",
    student_version=True,
    non_graphical=True,
    new_desktop=True,
)
try:
    box = m3d.modeler.create_box([0, 0, 0], [10, 20, 5], name="test_box", material="steel_1008")
    print("created:", box.name, "volume (mm^3):", box.volume)
    print("objects:", m3d.modeler.object_names)
finally:
    m3d.release_desktop(close_projects=True, close_desktop=True)

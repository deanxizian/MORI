"""Local iteration fixture; final delivery always uses full build.py."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
import build
from wheel_interfaces import apply_wheel_interfaces
bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections();assembled();build.materials()
base=ROOT/'revisions/V1.2-M1.13_before_wheel_interface/mechanical/reports'
for n in ['module_assembly.json','structure_changes.json','part_consolidation.json','layout_cleanup_changes.json']:(ROOT/'reports'/n).write_bytes((base/n).read_bytes())
build.CONTACTS[:]=json.loads((base/'intended_contacts.json').read_text())
apply_wheel_interfaces()
save_json(ROOT/'reports/intended_contacts.json',build.CONTACTS)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'studies/s288_interface_review/wheel_iteration.blend'))

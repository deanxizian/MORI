"""Read final saved geometry and finalize intermediate construction summaries.

The staged build keeps earlier change records for comparison. After all geometry
phases, the final module inventory and dimensions must come from saved objects.
This script never edits a mesh or a validation result.
"""
import sys,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from structural_simplification import volume
bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections();assembled()
objects={o.name.removeprefix(PREFIX):o for o in parts() if o.get('simple_support_module')}
path=ROOT/'reports/structure_changes.json';r=json.loads(path.read_text())
r['after']={n:{'volume_mm3':volume(o),'bounds_xyz_mm':bounds(o)} for n,o in objects.items()}
r['support_printed_parts_after']=len(objects)
r['final_inventory_source']='Saved MORI_V1_Assembly objects tagged simple_support_module; prior before snapshot retained.'
r['final_source_blend_sha256']=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest()
save_json(path,r)
print('STRUCTURE_METADATA_FINALIZED',len(objects),flush=True)

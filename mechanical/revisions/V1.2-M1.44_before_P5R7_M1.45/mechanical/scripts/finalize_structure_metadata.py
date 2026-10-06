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
# M1.43 adopts the drive-entry candidate's GB823 M2x8 screws as a set.
# The construction-stage joint schedule still describes the old 1.6mm head.
# Update that semantic record to the selected catalogue envelope (1.4mm),
# retaining the independently defined XY and bearing-plane datums for checking.
q=P.get('assembly_issue_fixes',{})
if q.get('enabled'):
    plan_path=ROOT/'reports/module_assembly.json'
    plan=json.loads(plan_path.read_text())
    drive_ids={n.removesuffix('_Nut') for n in q['drive_nuts']['ids']}
    for joint in plan['joints']:
        if joint['id'] in drive_ids:
            joint.update(head_height_mm=1.4,
                         screw_length_mm=q['drive_nuts']['screw_length_mm'],
                         screw_specification='GB823 M2x8; nominal head diameter3.5xheight1.4mm',
                         screw_source_url=P['interface_completion']['M2_screw_source'])
    plan['final_source_blend_sha256']=r['final_source_blend_sha256']
    save_json(plan_path,plan)
print('STRUCTURE_METADATA_FINALIZED',len(objects),flush=True)

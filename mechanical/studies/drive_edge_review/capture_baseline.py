"""Capture the accepted M1.35 assembly before the local right cap-edge edit."""
import sys,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from common import *
from validate_head_cleanup import geometry_record
bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections()
for n in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[n].hide_viewport=False
assembled()
r={'revision':P['revision'],'source':bpy.data.filepath,'source_sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),
   'parts':{o.name.removeprefix(PREFIX):geometry_record(o) for o in parts()}}
o=bpy.data.objects[PREFIX+'Motor_Retainer'];o.data.calc_loop_triangles()
r['Motor_Retainer']={'vertices_mm':[list(v) for v in vertices_world(o)],'triangles':[list(f.vertices) for f in o.data.loop_triangles]}
out=Path(__file__).parent/'baseline_geometry.json';assert not out.exists(),'Immutable baseline already exists'
save_json(out,r)
print('CAP_EDGE_BASELINE',len(r['parts']),flush=True)

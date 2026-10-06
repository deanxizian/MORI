import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from common import *
from validate_head_cleanup import geometry_record
bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections()
for n in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[n].hide_viewport=False
assembled();r={'revision':'V1.2-M1.34','source':bpy.data.filepath,'parts':{o.name.removeprefix(PREFIX):geometry_record(o) for o in parts()}}
for n in ['Pitch_Cradle','Head_Front','Display_Frame','Battery_Tray']:
 o=bpy.data.objects[PREFIX+n];o.data.calc_loop_triangles();r[n]={'vertices_mm':[list(v) for v in vertices_world(o)],'triangles':[list(f.vertices) for f in o.data.loop_triangles]}
out=Path(__file__).parent/'baseline_geometry.json';assert not out.exists(),'Immutable baseline already exists';save_json(out,r)

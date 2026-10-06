"""Immutable mesh/transform records for the approved M1.39 local changes."""
import sys,json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[2]/'mechanical/scripts'))
from common import *
from validate_head_cleanup import geometry_record
from validate import Solid
load_collections();assembled();bpy.context.view_layer.update()
dest=sys.argv[sys.argv.index('--')+1]
out={'revision':'V1.2-M1.38','blend':bpy.data.filepath,
     'blend_sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),
     'parts':{o.name.removeprefix(PREFIX):geometry_record(o) for o in parts()}}
for name in ['Pitch_Yoke','Head_Front']:
 s=Solid(bpy.data.objects[PREFIX+name]);m=s.m.to_mesh64()
 out[name]={'vertices_mm':m.vert_properties[:,:3].tolist(),'triangles':m.tri_verts.tolist()}
(HERE/dest).write_text(json.dumps(out,separators=(',',':')))
print('CAPTURED',dest,flush=True)

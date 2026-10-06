from pathlib import Path
import sys,json,math
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from common import *
from head_surface_display import planar_faces

def angle64(a,b):
    a=np.array(a,dtype=np.float64);b=np.array(b,dtype=np.float64)
    a/=np.linalg.norm(a);b/=np.linalg.norm(b)
    return math.degrees(math.atan2(np.linalg.norm(np.cross(a,b)),np.dot(a,b)))

for name in P['head_surface_display']['target_part_ids']:
    o=bpy.data.objects[PREFIX+name];me=o.data
    is_planar=planar_faces(o)
    normals=[n.vector[:] for n in me.corner_normals]
    for p,flat in zip(me.polygons,is_planar):
        if flat:
            for k in p.loop_indices:normals[k]=p.normal[:]
    me.normals_split_custom_set(normals);me.update()
    errors=[angle64(p.normal,me.corner_normals[k].vector) for p,flat in zip(me.polygons,is_planar) if flat for k in p.loop_indices]
    print(name,'flat_custom_max',max(errors),'failed',sum(e>.05 for e in errors),'has_custom',me.has_custom_normals,flush=True)

bpy.ops.wm.save_as_mainfile(filepath=str(Path(__file__).with_name('custom_normal_trial.blend')))

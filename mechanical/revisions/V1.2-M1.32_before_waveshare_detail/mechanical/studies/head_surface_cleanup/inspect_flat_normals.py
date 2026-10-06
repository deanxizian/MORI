from pathlib import Path
import sys,json,math
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from common import *
from head_surface_display import planar_faces

def angle64(a,b):
    a=np.array(a,dtype=np.float64);b=np.array(b,dtype=np.float64)
    a/=np.linalg.norm(a);b/=np.linalg.norm(b)
    return math.degrees(math.atan2(np.linalg.norm(np.cross(a,b)),np.dot(a,b)))

rows=[]
for name in P['head_surface_display']['target_part_ids']:
    o=bpy.data.objects[PREFIX+name];me=o.data;me.update()
    flat=planar_faces(o);normals=me.corner_normals
    samples=[]
    for p,is_plane in zip(me.polygons,flat):
        if not is_plane:continue
        ns=[normals[k].vector.copy() for k in p.loop_indices]
        errs=[angle64(p.normal,n) for n in ns]
        if max(errs)<.05:continue
        vs=np.array([me.vertices[k].co[:] for k in p.vertices],dtype=np.float64)
        cross=np.cross(vs[1]-vs[0],vs[2]-vs[0]);cross/=np.linalg.norm(cross)
        samples.append({'face':p.index,'area':p.area,'smooth':p.use_smooth,'normal':list(p.normal),
                        'normal_length':p.normal.length,'corner_normals':[list(n) for n in ns],
                        'corner_lengths':[n.length for n in ns],'vertices':vs.tolist(),
                        'cross_normal':cross.tolist(),'errs':errs,
                        'cross_vs_polygon':angle64(cross,p.normal),
                        'cross_vs_corner':[angle64(cross,n) for n in ns]})
    samples.sort(key=lambda s:max(s['errs']),reverse=True)
    row={'id':name,'has_custom_normals':me.has_custom_normals,'normals_domain':me.normals_domain,
         'modifiers':[m.name+':'+m.type for m in o.modifiers],
         'failed_count':len(samples),'top_samples':samples[:3]}
    rows.append(row)
out=Path(__file__).with_name('flat_normal_diagnosis.json');out.write_text(json.dumps(rows,indent=2))
print(json.dumps(rows,indent=2))

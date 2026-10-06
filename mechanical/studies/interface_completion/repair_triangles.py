import sys,json,collections
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid
from export import topology
from layout_cleanup import mm_mesh
load_collections();assembled();bpy.context.view_layer.update()

def repair(v,faces):
 v=np.array(v);faces=np.array(faces,dtype=np.int64);history=[]
 for it in range(1000):
  bad=[]
  for i,ids in enumerate(faces):
   a,b,c=[Vector(v[j]) for j in ids]
   if (b-a).cross(c-a).length<1e-8 or len(set(ids))<3:bad.append(i)
  if not bad:break
  edgefaces=collections.defaultdict(list);neighbors=collections.defaultdict(set)
  for i,ids in enumerate(faces):
   for j in range(3):
    a,b=ids[j],ids[(j+1)%3];edgefaces[tuple(sorted([a,b]))].append(i);neighbors[a].add(b);neighbors[b].add(a)
  changed=False
  for idx in bad:
   t=faces[idx];edges=sorted([(np.linalg.norm(v[t[j]]-v[t[(j+1)%3]]),t[j],t[(j+1)%3],t[(j+2)%3]) for j in range(3)])
   length,a,b,c=edges[0]
   if length<.00051 and len(neighbors[a]&neighbors[b])==2:
    faces[faces==b]=a;faces=np.array([f for f in faces if len(set(f))==3]);history.append({'kind':'edge_collapse','length_mm':float(length)});changed=True;break
   length,a,b,c=edges[-1];adj=edgefaces[tuple(sorted([a,b]))]
   if len(adj)!=2:continue
   k=next(k for k in adj if k!=idx);d=next((x for x in faces[k] if x not in [a,b]),None)
   if d is None or d==c or tuple(sorted([c,d])) in edgefaces:continue
   # C lies on AB. Replace the zero-area triangle and its neighbour by AC-D and CB-D.
   old=np.array([faces[idx],faces[k]]);faces[idx]=[c,d,b];faces[k]=[d,c,a];history.append({'kind':'zero_area_diagonal_flip','old':old.tolist(),'new':[faces[idx].tolist(),faces[k].tolist()]});changed=True;break
  if not changed:break
 return v,faces,history,bad
rows=[]
for name in ['Head_Front','Head_Rear','Body_Upper']:
 o=bpy.data.objects[PREFIX+name];s=Solid(o);m=s.m.set_tolerance(.00005).simplify(.00005);d=m.to_mesh64();v=np.asarray(d.vert_properties[:,:3],dtype=np.float32).astype(float);f=np.array(d.tri_verts,dtype=np.int64)
 v,f,h,bad=repair(v,f);m=manifold.Manifold(manifold.Mesh64(np.array(v,dtype=np.float64,order='C'),np.array(f,dtype=np.uint64,order='C')));top=topology(v.tolist(),f.tolist());r={'id':name,'status':str(m.status()),'topology':top,'operations':h,'remaining_bad':bad,'delta_mm3':None}
 if m.status()==manifold.Error.NoError:r['delta_mm3']=max(0,(m-s.m).volume())+max(0,(s.m-m).volume())
 rows.append(r)
print('TRIANGLE_REPAIR',[(r['id'],r['status'],r['topology'],len(r['operations']),r['delta_mm3']) for r in rows],flush=True);(HERE/'triangle_repair_trial.json').write_text(json.dumps(rows,indent=2))

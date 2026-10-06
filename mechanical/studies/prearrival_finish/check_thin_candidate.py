"""Compare isolated candidate against current main; never save the main."""
from pathlib import Path
import sys,json,hashlib
HERE=Path(__file__).resolve().parent;M=HERE.parents[1]
sys.path.insert(0,str(M/'scripts'))
from common import *
from validate import Solid,rigidtr
from validate_head_retention import hit
from validate_head_cleanup import geometry_record
load_collections()
# Hidden construction collections contain current validation proxies. They
# must be evaluated before reading matrix_world, as in the main validator.
for n in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[n].hide_viewport=False
assembled();bpy.context.view_layer.update()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']}
records={n:geometry_record(s.o) for n,s in ss.items()}
names=list(ss)
with bpy.data.libraries.load(str(M/'mori_v1_2.blend'),link=False) as (a,b):b.objects=[PREFIX+n for n in names]
baseline={n:o for n,o in zip(names,b.objects) if o}
for o in baseline.values():
 bpy.context.scene.collection.objects.link(o)
 parent=o.parent
 while parent:
  if parent.name not in bpy.context.scene.objects:bpy.context.scene.collection.objects.link(parent)
  parent=parent.parent
bpy.context.view_layer.update()
changed=sorted(n for n,o in baseline.items() if records[n]!=geometry_record(o))
expected={'Pitch_Yoke','Yaw_Reaction_Link','Drive_Bridge','Motor_Retainer'}
deltas=[]
for n in changed:
 a=Solid(baseline[n]).m;c=ss[n].m
 deltas.append(dict(id=n,added_mm3=max(0,(c-a).volume()),removed_mm3=max(0,(a-c).volume()),connected_solids=len(c.decompose())))
collisions=[]
for n in changed:
 for other,t in ss.items():
  if n==other or (other in changed and changed.index(other)<changed.index(n)):continue
  v=hit(ss[n].m,t.m)
  if v:collisions.append(dict(a=n,b=other,overlap_mm3=v))
motion=[]
for yd in range(-60,61,10):
 for pd in range(-20,26,5):
  moved={n:s.m.transform(np.array(rigidtr(yd,pd if s.group=='pitch' else 0))[:3,:]) for n,s in ss.items() if s.group in ['pitch','yaw']}
  for n,m in moved.items():
   for other,t in ss.items():
    if t.group in ['pitch','yaw']:continue
    if n!='Pitch_Yoke' and other!='Yaw_Reaction_Link':continue
    v=hit(m,t.m)
    if v:motion.append(dict(yaw=yd,pitch=pd,a=n,b=other,overlap_mm3=v))
sections=[]
spec=[('Pitch_Yoke',2,173.5),('Pitch_Yoke',2,178.3),('Yaw_Reaction_Link',1,6.04),('Motor_Retainer',0,31.9)]
for n,axis,d in spec:
 ij=[i for i in range(3) if i!=axis];tr=np.zeros((3,4));tr[0,ij[0]]=1;tr[1,ij[1]]=1;tr[2,axis]=1
 if np.linalg.det(tr[:,:3])<0:tr[0,ij[0]]=-1
 sections.append(dict(id=n,axis=axis,coordinate_mm=d,plane_axes=ij,x_sign=int(tr[0,ij[0]]),before=[p.tolist() for p in Solid(baseline[n]).m.transform(tr).slice(d).to_polygons()],after=[p.tolist() for p in ss[n].m.transform(tr).slice(d).to_polygons()]))
walls=[]
for n in changed:
 s=ss[n];tri=s.v[s.f];cross=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);ar=np.linalg.norm(cross,axis=1)/2;ns=cross/np.maximum(ar[:,None]*2,1e-15);bv=s.bvh();rays=[]
 ids=np.unique(np.searchsorted(np.cumsum(ar),np.linspace(0,ar.sum(),20002)[1:-1]))
 for i in ids:
  p=tri[i].mean(0);normal=ns[i];h,hn,j,d=bv.ray_cast(Vector(p-normal*.0001),Vector(-normal),300)
  if h is not None and j!=i and normal@np.array(hn)<-.95 and d>.02:rays.append((float(d+.0001),p.tolist()))
 rays.sort();walls.append(dict(id=n,samples=len(rays),minimum_sampled_mm=rays[0][0],lowest=rays[:8]))
out=dict(status='PASS' if set(changed)==expected and not collisions and not motion and all(r['connected_solids']==1 for r in deltas) else 'FAIL',applied_to_main=False,source_blend_sha256=hashlib.sha256((M/'mori_v1_2.blend').read_bytes()).hexdigest(),candidate_blend_sha256=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),changed_ids=changed,delta=deltas,static_collisions=collisions,motion_poses=130,motion_collisions=motion,sections=sections,wall_samples=walls,limits=['Finite nominal geometry only, no strength qualification','Horn-dependent final reaction connection remains BLOCKED','Await user confirmation before applying any of these proposed shapes'])
(HERE/'thin_candidate_check.json').write_text(json.dumps(out,indent=2)+'\n');print('THIN_CANDIDATE',out['status'],changed,deltas,len(collisions),len(motion),[(r['id'],r['minimum_sampled_mm']) for r in walls],flush=True)

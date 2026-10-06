"""Nominal candidate shell service sequence, tool access and local wall audit.

This script reads an independent candidate. It does not approve or publish it.
"""
import sys,json,math,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid
from export import topology
from interface_completion import axial
load_collections();COLS['DATUMS'].hide_viewport=False;assembled();bpy.context.view_layer.update()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']}
names=set(ss);report={'main_updated':False,'source_candidate_sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest()}
def select(*p):return {n for n in names if n.startswith(p)}
def collisions(m,fixed,threshold=.02):
 bb=np.array(m.bounding_box());hits=[]
 for k in fixed:
  s=ss[k]
  if np.any(bb[3:]<s.lo) or np.any(s.hi<bb[:3]):continue
  v=max(0,(m^s.m).volume())
  if v>threshold:hits.append({'part':k,'mm3':v})
 return hits
wheels=select('Tire_','Wheel_Hub','Wheel_End','Wheel_Spacer_L_1','Wheel_Spacer_R_1')
head={n for n,s in ss.items() if s.group in ['yaw','pitch']}|select('Yaw_')
paths=[]
for remove_wheels in [False,True]:
 fixed=names-{'Body_Lower'}-select('Shell_Screw')-(wheels if remove_wheels else set())
 hits=[]
 for d in np.arange(0,120.01,.5):
  row=collisions(ss['Body_Lower'].m.translate([0,0,-float(d)]),fixed)
  if row:hits.append({'travel_mm':float(d),'hits':row});break
 paths.append({'step':'lower shell straight down','wheels_removed':remove_wheels,'travel_mm':120,'step_mm':.5,'status':'FAIL' if hits else 'PASS','first_hit':hits[:1]})
report['lower_paths']=paths;print('BODY_LOWER',paths,flush=True)

tools=[]
# GB823 M3 requires recess No.2. PB190.2-100/6 has a documented 6mm x100mm
# blade. A conservative 35mm x105mm cylindrical handle is a study envelope,
# not a manufacturer handle model. Retraction extends beyond the robot.
for n in sorted(select('Shell_Screw','Frame_Screw')):
 screw=ss[n];axis=np.array([0,0,-1]);xy=(screw.lo+screw.hi)[:2]/2
 face=np.array([*xy,screw.lo[2]])
 bench=names-{n}
 if n.startswith('Frame_'):bench-=head|wheels|{'Body_Lower'}|select('Shell_Screw')
 tested=[]
 for remove_battery in [False,True]:
  fixed=bench-(select('Battery') if remove_battery else set());hits=[]
  for label,shape in [('blade',axial(3,100,face+axis*50.03,axis)),('handle_reserve',axial(17.5,105,face+axis*152.53,axis))]:
   hits.extend([dict(kind=label,**h) for h in collisions(shape,fixed)])
  tested.append({'battery_removed':remove_battery,'hits':hits})
 tools.append({'screw':n,'status':'PASS' if any(not r['hits'] for r in tested) else 'FAIL','trials':tested})
report['tools']=tools;print('BODY_TOOLS',[(r['screw'],r['status']) for r in tools],flush=True)

moving=['Body_Upper']+sorted(select('Frame_Insert','Shell_Insert','Speaker','Rear_Interface','USB_Receptacle','Power_Switch'))
removed=head|wheels|{'Body_Lower'}|select('Frame_Screw','Shell_Screw')
fixed=names-set(moving)-removed;origin=Vector((0,0,D['body_z']));poses=[]
def pose(a,y,z):return Matrix.Translation((0,y,z))@Matrix.Translation(origin)@Matrix.Rotation(math.radians(a),4,'X')@Matrix.Translation(-origin)
for u in np.linspace(0,1,61):poses.append(('tilt and lift',float(u),pose(15*u,0,14*u)))
for y in np.linspace(0,-14,57)[1:]:poses.append(('back',float(y),pose(15,y,14)))
for z in np.arange(14.5,140.01,.5):poses.append(('up',float(z),pose(15,-14,z)))
hits=[];near=[]
for phase,t,tr in poses:
 for n in moving:
  m=ss[n].m.transform(np.array(tr)[:3,:]);hs=collisions(m,fixed)
  hits.extend([{'phase':phase,'parameter':t,'moving':n,**h} for h in hs])
  if phase=='tilt and lift' and t<.2:continue
  # Useful running-clearance samples; initial intentional seating contacts
  # are separately retained in the collision test above.
  bb=np.array(m.bounding_box())
  for k in fixed:
   s=ss[k]
   if np.any(bb[3:]+.5<s.lo) or np.any(s.hi+.5<bb[:3]):continue
   gap=m.min_gap(s.m,.5)
   if gap<.499:near.append({'phase':phase,'parameter':t,'moving':n,'fixed':k,'gap_mm':gap})
near.sort(key=lambda r:r['gap_mm'])
report['upper_path']={'status':'FAIL' if hits else 'PASS','tilt_x_deg':15,'initial_lift_mm':14,'rear_translation_mm':14,'final_lift_mm':140,'samples':len(poses),'hits':hits,'moving':moving,'removed_first':sorted(removed),'closest_running_samples_excluding_initial_20percent':near[:12]}
print('BODY_UPPER',len(hits),near[:3],flush=True)

walls=[]
for n in ['Body_Upper','Body_Lower']:
 s=ss[n];tri=s.v[s.f];cross=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);ar=np.linalg.norm(cross,axis=1)/2;ns=cross/np.maximum(ar[:,None]*2,1e-15)
 indices=np.unique(np.searchsorted(np.cumsum(ar),np.linspace(0,ar.sum(),30002)[1:-1]));rays=[];b=s.bvh()
 for i in indices:
  p=tri[i].mean(0);nv=ns[i];h,hn,j,d=b.ray_cast(Vector(p-nv*.0001),Vector(-nv),300)
  if h is not None and j!=i and nv@np.array(hn)<-.95 and d>.02:rays.append((float(d+.0001),p.tolist()))
 rays.sort();walls.append({'part':n,'topology':topology(s.v,s.f),'positive_components':sum(m.volume()>.001 for m in s.m.decompose()),'sample_count':len(rays),'sampled_minimum_mm':rays[0][0],'lowest':rays[:15]})
report['shell_wall_samples']=walls
report['tool_source']='https://www.pbswisstools.com/en/tools/quality-hand-tools/screwdrivers/product/pb-190'
report['limits']='Unadopted candidate. Finite rigid nominal geometry; wires disconnected. Blade catalogue dimensions, conservative handle reserve. Hands, exact tip profile, manufacturing tolerance, strength, continuous swept-path proof NOT_TESTED. Wall rays are not global minimum thickness.'
(HERE/'body_seam_complete_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('BODY_SEAM_COMPLETE',[(r['part'],r['sampled_minimum_mm']) for r in walls],flush=True)

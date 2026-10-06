"""Finite geometry review of the isolated catalogue-insert candidate."""
import sys,json,math,itertools
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid,rigidtr,broad
from mathutils.bvhtree import BVHTree
from export import topology
load_collections();assembled();bpy.context.view_layer.update()
c=json.loads((HERE/'insert_candidate.json').read_text());f={r['id']:r for r in json.loads((HERE/'fastener_current.json').read_text())};out=[]
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']};changed={r['host'] for r in c['rows']}|{'Head_Rear'}
for r in c['rows']:
 s=ss[r['host']];b=s.bvh();e=np.array(r['entry_mm']);a=np.array(r['outward']);u=np.cross(a,[1,0,0] if abs(a[0])<.9 else [0,1,0]);u/=np.linalg.norm(u);v=np.cross(a,u);walls=[];broken=0
 for z in np.linspace(.25,r['length_mm']+.15,5):
  for th in np.arange(0,360,5):
   d=u*math.cos(math.radians(th))+v*math.sin(math.radians(th));origin=e-a*z
   hits=s.m.ray_cast(origin.tolist(),(origin+d*300).tolist());clean=[]
   for hit in hits:
    if not clean or abs(hit.distance-clean[-1].distance)>1e-7:clean.append(hit)
   if len(clean)<2 or np.dot(clean[0].normal,d)>=0 or np.dot(clean[1].normal,d)<=0:broken+=1;continue
   walls.append((clean[1].distance-clean[0].distance)*300)
 fh=s.m.ray_cast((e+a*.01).tolist(),(e-a*100).tolist());fdist=fh[0].distance*100.01-.01 if fh else None;bottom=[]
 if fh:
  for x,y in [(0,0),(.7,0),(-.7,0),(0,.7),(0,-.7)]:
   pos=np.array(fh[0].position)+u*x+v*y-a*.01
   bh=s.m.ray_cast(pos.tolist(),(pos-a*100).tolist())
   if bh:bottom.append(float(bh[0].distance*100+.01))
 fd=f[r['screw']];face=np.array(fd['tool_start_mm'])-np.array(fd['extracted_axis_outward'])*fd['nominal_head_height_mm'];length=fd['nominal_shank_length_mm'];tip=face-a*length
 if 'screw_length_mm' in r:face=np.array(r['screw_head_bearing_mm']);length=r['screw_length_mm'];tip=face-a*length
 if r['head_seam_move_pending'] and 'screw_length_mm' not in r:face[0]=e[0];face[2]+=2;tip=face-a*length
 penetration=float(np.dot(e-tip,a));engagement=max(0,min(penetration-.2,r['length_mm']))
 minwall=min(walls) if walls else 0;mincap=min(bottom) if bottom else None
 row={'id':r['id'],'host':r['host'],'min_sampled_pilot_wall_mm':minwall,'required_wall_mm':1.6 if r['OD_mm']==4.6 else 1.3,'radial_samples':len(walls),'broken_radial_samples':broken,'first_axial_material_depth_mm':fdist,'sampled_blind_end_wall_mm':mincap,'screw_insertion_below_seating_face_mm':penetration,'nominal_thread_engagement_mm':engagement,'screw_tip_to_first_axial_material_mm':fdist-penetration if fdist is not None else None}
 row['status']='PASS' if minwall>=row['required_wall_mm']-.01 and not broken and (mincap is None or mincap>=1.0) and engagement>=2.4 and (row['screw_tip_to_first_axial_material_mm'] is None or row['screw_tip_to_first_axial_material_mm']>=.15) else 'FAIL'
 out.append(row)
tops=[]
for n in sorted(changed):
 s=ss[n];t=topology(s.v.tolist(),s.f.tolist());t.update(id=n,positive_components=sum(p.volume()>.001 for p in s.m.decompose()));tops.append(t)
collisions=[]
for n in changed:
 for k,s in ss.items():
  if k==n:continue
  if 'Insert' in k:
   own=next((r for r in c['rows'] if r['id']==k),None)
   if own and own['host']==n:continue # Only specified installed knurl/host interference.
  v=max(0,(ss[n].m^s.m).volume()) if broad(ss[n],s) else 0
  if v>.02:collisions.append({'a':n,'b':k,'volume_mm3':v})
motion=[]
for yaw in range(-60,61,10):
 ys={n:Solid(s.o,s,rigidtr(yaw,0)) if s.group=='yaw' else s for n,s in ss.items() if s.group!='pitch'}
 for pitch in range(-20,26,5):
  poses={**ys,**{n:Solid(s.o,s,rigidtr(yaw,pitch)) for n,s in ss.items() if s.group=='pitch'}}
  for n in changed:
   for k,s in poses.items():
    if k==n or s.group==poses[n].group:continue
    if broad(poses[n],s):
     v=max(0,(poses[n].m^s.m).volume())
     if v>.02:motion.append({'yaw':yaw,'pitch':pitch,'a':n,'b':k,'overlap_mm3':v})
 print('INSERT_MOTION',yaw,flush=True)
report={'status':'PASS' if all(r['status']=='PASS' for r in out) and not collisions and not motion and all(r['positive_components']==1 for r in tops) else 'FAIL','main_updated':False,'rows':out,'topology':tops,'collisions':collisions,'poses':130,'motion_collisions':motion,'limits':'Finite nominal rigid geometry, manufacturer pilot-wall guideline only; strength, PA12 interference, creep and screw torque require coupon/physical tests. Own installed insert/host crest interference explicitly excluded only for each named pair.'}
(HERE/'insert_candidate_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('INSERT_CHECK',report['status'],[(r['id'],r['status']) for r in out if r['status']!='PASS'],flush=True)

import sys,json,math
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[2]/'mechanical/scripts'))
from common import *
from validate import Solid,rigidtr
ROOT=PROJECT
load_collections();assembled();bpy.context.view_layer.update()
solids={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.get('role')=='part' and o.get('group') not in ['dock','coupon']}
changed=['Pitch_Yoke']+[n for n in solids if n.startswith(('Head_Yaw_Ear','Head_Pitch_Ear'))];fail=[];checks=0
for yaw in range(-60,61,10):
 moved={n:Solid(s.o,s,rigidtr(yaw,0)) for n,s in solids.items() if s.group=='yaw'}
 for pitch in range(-20,26,5):
  other={n:Solid(s.o,s,rigidtr(yaw,pitch)) if s.group=='pitch' else s for n,s in solids.items() if s.group!='yaw'}
  for n in changed:
   a=moved[n]
   for m,b in other.items():
    if np.any(a.hi<b.lo) or np.any(b.hi<a.lo):continue
    checks+=1;v=max(0,(a.m^b.m).volume())
    if v>.02:fail.append({'a':n,'b':m,'yaw':yaw,'pitch':pitch,'mm3':round(v,4)})
# Nut insertion is evaluated on the detached support, before servo/cradle installation.
yoke=solids['Pitch_Yoke'];mounts=json.load(open(HERE/'servo_mount_candidate.json'))['mounts'];nutpaths=[]
for row in mounts:
 n=row['id']+'_Nut';axis=np.array([0,0,-1.]) if 'Yaw' in n else np.array([-1.,0,0]);a=solids[n];hits=[]
 for d in np.arange(.25,12.01,.25):
  m=a.m.translate((axis*d).tolist());v=max(0,(m^yoke.m).volume())
  if v>.02:hits.append({'travel_mm':float(d),'mm3':round(v,4)})
 nutpaths.append({'id':n,'direction':axis.tolist(),'sampled_path_mm':12,'step_mm':.25,'host_collisions':hits})
report={'status':'FAIL' if fail or any(a['host_collisions'] for a in nutpaths) else 'PASS','poses':130,'changed_parts':changed,'tested_broadphase_pairs':checks,'dynamic_collisions':fail,'nut_paths':nutpaths,'assembly_order':'Fit nuts on detached yoke first; then servo ear bolts. Nut recesses require an actual4mm AF nut and coupon; fingers/tool grip not fully simulated.','limits':'Nominal rigid geometry only, existing vendor proxies retained. No screw pullout, fatigue or cable qualification.'}
(HERE/'servo_candidate_motion.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('SERVO_CANDIDATE_MOTION_COMPLETE',report['status'],len(fail),flush=True)

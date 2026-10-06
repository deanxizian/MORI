"""Read-only additional shell-first paths: twist or horizontal extraction."""
import sys,json,math
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid
load_collections();assembled();bpy.context.view_layer.update()
data=json.loads((HERE/'upper_shell_paths.json').read_text())
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']}
moving=data['moving'];fixed={n:ss[n] for n in data['fixed']};results=[]
def test(tr):
 for n in moving:
  m=ss[n].m.transform(np.array(tr)[:3,:]);bb=np.array(m.bounding_box())
  for k,s in fixed.items():
   if np.any(bb[3:]<s.lo) or np.any(s.hi<bb[:3]):continue
   v=max(0,(m^s.m).volume())
   if v>.05:return [n,k,v]
 return None
for yaw in [-90,-60,-45,-30,-15,-5,5,15,30,45,60,90]:
 for initial_lift in [0,1,2,3,4]:
  fail=None
  for frac in np.linspace(0,1,abs(yaw)+1):
   tr=Matrix.Translation((0,0,initial_lift*frac))@Matrix.Rotation(math.radians(yaw*frac),4,'Z')
   if (hit:=test(tr)):fail={'phase':'initial','fraction':float(frac),'hit':hit};break
  if fail is None:
   for dz in range(initial_lift,121,2):
    if (hit:=test(Matrix.Translation((0,0,dz))@Matrix.Rotation(math.radians(yaw),4,'Z'))):fail={'phase':'lift','z':dz,'hit':hit};break
  results.append({'yaw_deg':yaw,'initial_lift_mm':initial_lift,'status':'FAIL' if fail else 'PASS','first_hit':fail})
 print('SHELL_TWIST',yaw,flush=True)
(HERE/'upper_shell_yaw_paths.json').write_text(json.dumps({'rows':results,'limits':'Bare shell and chassis as in upper_shell_paths.json; finite60 twist-then-lift alternatives only, no claim that every possible path is impossible.'},indent=2))

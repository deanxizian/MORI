import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from common import *
from validate import Solid,broad
from interface_completion import axial
load_collections();assembled();ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']}
r=next(r for r in json.loads((ROOT/'reports/prearrival_geometry.json').read_text())['servo_ears'] if r['id']=='Head_Pitch_Ear_0');e=np.array(r['ear_top_mm']);a=np.array([1,0,0]);id=r['id']+'_Screw';h=2.;length=8
bolt=axial(1,length+.02,e-a*(length-.02)/2,a)+axial(1.9,h,e+a*h/2,a);socket=axial(1.5/math.sqrt(3),1.12,e+a*(h-.55+.01),a,6);bolt-=socket
coll=[]
for n,s in ss.items():
 if n!=id:
  v=max(0,(bolt^s.m).volume())
  if v>.02:coll.append(dict(id=n,mm3=v))
p=e+a*(h-.7);tool=axial(.87,50,p+a*25,a)+axial(.87,14,p+a*50+[0,7,0],[0,1,0])+manifold.Manifold.sphere(.87,32).translate((p+a*50).tolist())
bench={n:ss[n] for n in ss if n.startswith(('Pitch_Yoke','Pitch_Bearing','Pitch_Servo','Head_Pitch_')) and n!=id};hits=[]
for angle in range(-120,121,2):
 tr=Matrix.Translation(Vector(p))@Matrix.Rotation(math.radians(angle),4,'X')@Matrix.Translation(-Vector(p));m=tool.transform(np.array(tr)[:3,:])
 for n,s in bench.items():
  v=max(0,(m^s.m).volume())
  if v>.02:hits.append(dict(angle=angle,id=n,mm3=v))
good=[a for a in range(-120,121,2) if not any(r['angle']==a for r in hits)];longest=0;run=0
for angle in range(-120,121,2):run=run+2 if angle in good else 0;longest=max(longest,run)
d=dict(status='PASS' if not coll and longest>=60 else 'FAIL',collisions=coll,head_mm=[3.8,2],screw='M2x8 DIN912,1.5AF',tool_clear_angle_span_deg=longest,tool_hits=hits);(ROOT/'studies/interface_completion/upper_pitch_tool_finish.json').write_text(json.dumps(d,indent=2));print(d,flush=True)

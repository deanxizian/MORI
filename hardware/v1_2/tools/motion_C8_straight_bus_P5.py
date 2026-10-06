"""Rotate input bypass capacitor so the supply bus no longer wraps around it."""
import json
import pcbnew as k
from layout_P5 import *
from close_P5 import connected
from body_P5 import create
from geometry_guard_P5 import Guard,obstacles
name,d,p,r=paths('motion');b=k.LoadBoard(str(p));connected(b);backup=r/'before_C8_straight_bus.kicad_pcb';k.SaveBoard(str(backup),b)
f=b.FindFootprintByReference('C8');setplace(f,45.5,7.6,-90,side='B')
for t in list(b.GetTracks()):
 if t.GetNetname()=='/+5V_MOTION' or t.m_Uuid.AsString() in ['5808342f-4872-41c3-a09c-cf1d0ed1d25e','a4e146d9-3496-41ae-938f-c014b84223fc'] or (isinstance(t,k.PCB_VIA)and math.dist(xy(t.GetPosition()),(48,5.1))<.02):b.Delete(t)
create(b,'motion')
# Displace only foreign thin copper crossing this newly placed component.
from body_keepouts_P3R1 import rectangle
sh=rectangle(rect(f));removed=[]
for t in list(b.GetTracks()):
 if t.GetNetname() in ['/GND','/+5V_MOTION']:continue
 if any(t.IsOnLayer(l) and t.GetEffectiveShape(l).Collide(sh,mm(.21)) for l in [F,B]):
  assert isinstance(t,k.PCB_VIA) or t.GetWidth()<=mm(.25)
  removed.append(dict(net=t.GetNetname(),uuid=t.m_Uuid.AsString()));b.Delete(t)
routes=[('/+5V_MOTION',[(40.39,2.26),(40.39,4.8),(41.79,6.2),(57.9,6.2),(58.6232,5.4768),(58.6232,3.1496),(58.5216,3.048)],.5),('/+5V_MOTION',[(45.5,6.825),(45.5,6.2)],.5)]
for net,ps,w in routes:
 g=Guard(b,net);checks=[g.line_clear(a,z,B,w) for a,z in zip(ps,ps[1:])];print(net,checks,flush=True)
 assert all(checks)
 track(b,net,ps,w,B)
from plane_finish_P5 import simple
g=Guard(b,'/GND');options=[]
for ix in range(425,486):
 for iy in range(90,121):
  v=(ix*.1,iy*.1)
  if not g.via_clear(v):continue
  for pts in simple((45.5,8.375),v):
   if all(g.line_clear(a,z,B,.2) for a,z in zip(pts,pts[1:])):
    options.append((sum(math.dist(a,z)for a,z in zip(pts,pts[1:])),v,pts));break
assert options,'No ground port'
_,v,pts=min(options);print('GND selected',v,pts);track(b,'/GND',pts,.2,B);via(b,'/GND',*v,grid=False)
k.SaveBoard(str(p),b)
(r/'C8_straight_bus.json').write_text(json.dumps(dict(C8=[45.5,7.6,-90,'B'],removed=removed,routes=routes),indent=2)+'\n')
from close_P5 import run
run('motion',sorted({v['net'] for v in removed}))

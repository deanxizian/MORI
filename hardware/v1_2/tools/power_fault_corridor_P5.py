"""A clear horizontal fault-return lane below the wheel-output connector."""
import json
import pcbnew as k
from layout_P5 import *
from close_P5 import connected
from geometry_guard_P5 import Guard,obstacles
name,d,p,r=paths('power');b=k.LoadBoard(str(p));connected(b);k.SaveBoard(str(r/'before_fault_corridor.kicad_pcb'),b)
net='/FAULT_N';ps=[(69.2658,33.8582),(69.2658,30.5),(68.4658,29.7),(61.5,29.7),(61,30.2),(50.5,30.2),(49.712,30.988),(47.1932,30.988)];new=track(b,net,ps,.2,B);displaced=[]
for t in list(b.GetTracks()):
 if t.GetNetname()==net:continue
 if t.IsOnLayer(B)and any(q.GetEffectiveShape(B).Collide(t.GetEffectiveShape(B),mm(.205))for q in new):
  assert (isinstance(t,k.PCB_VIA)and t.GetNetname()not in ['/GND','/H_VM','/W_VM','/BAT_MON','/H_PRE'])or(not isinstance(t,k.PCB_VIA)and t.GetWidth()<=mm(.25)),(t.GetNetname(),t.m_Uuid.AsString(),xy(t.GetStart()),xy(t.GetEnd()))
  displaced.append(dict(net=t.GetNetname(),uuid=t.m_Uuid.AsString()));b.Delete(t)
g=Guard(b,net);checks=[g.line_clear(a,z,B,.2)for a,z in zip(ps,ps[1:])];print(checks,displaced,flush=True)
if not all(checks):
 for a,z in zip(ps,ps[1:]):
  if g.line_clear(a,z,B,.2):continue
  for i in range(101):
   v=(a[0]+(z[0]-a[0])*i/100,a[1]+(z[1]-a[1])*i/100);obs=obstacles(b,net,v,B,.2)
   if obs:print(v,obs);break
assert all(checks)
k.SaveBoard(str(p),b);(r/'fault_corridor.json').write_text(json.dumps(dict(path=ps,displaced=displaced),indent=2)+'\n')

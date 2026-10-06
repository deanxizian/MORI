"""Keep the head divider escape outside the comparator and connector bodies."""
import json
import pcbnew as k
from layout_P5 import *
from close_P5 import connected
from geometry_guard_P5 import Guard
name,d,p,r=paths('power');b=k.LoadBoard(str(p));connected(b);k.SaveBoard(str(r/'before_H_sense_corridor.kicad_pcb'),b)
old={'a4eb11d5-d31f-4c99-ba8e-92874f1ec02b','59df0826-6949-447b-b92e-4fabf50c86ae','a94c85cb-93f3-4436-9289-1dfb9fe1102c'}
for t in list(b.GetTracks()):
 if t.m_Uuid.AsString()in old:b.Delete(t)
net='/H_SENSE';routes=[(F,[(62.825,38.5),(65.675,38.5)]),(F,[(63.9,38.5),(63.9,39.7)]),(F,[(62.525,35.135),(61.7914,35.135),(60.96,35.9664)]),(F,[(63.9,39.7),(60.7,39.7),(60.2,39.2),(60.2,36.7264),(60.96,35.9664)])];vs=[]
new=[]
for l,ps in routes:new+=track(b,net,ps,.2,l)
for v in vs:
 via(b,net,*v,grid=False)
 new+=[next(t for t in b.GetTracks()if isinstance(t,k.PCB_VIA)and xy(t.GetPosition())==v)]
displaced=[]
for t in list(b.GetTracks()):
 if t.GetNetname()==net:continue
 if any(t.IsOnLayer(l)and q.IsOnLayer(l)and q.GetEffectiveShape(l).Collide(t.GetEffectiveShape(l),mm(.205))for q in new for l in [F,B]):
  assert not isinstance(t,k.PCB_VIA) and t.GetWidth()<=mm(.25),(t.GetNetname(),t.m_Uuid.AsString(),xy(t.GetStart()),xy(t.GetEnd()))
  displaced.append(dict(net=t.GetNetname(),uuid=t.m_Uuid.AsString()));b.Delete(t)
g=Guard(b,net)
for l,ps in routes:
 checks=[g.line_clear(a,z,l,.2)for a,z in zip(ps,ps[1:])];print(l,checks,flush=True);assert all(checks)
# Via checks must exclude the newly added own vias from duplicate-distance check.
for q in new:
 if isinstance(q,k.PCB_VIA):assert all(g.clear(xy(q.GetPosition()),l,.8,True) for l in [F,B])
k.SaveBoard(str(p),b);(r/'head_sense_corridor.json').write_text(json.dumps(dict(routes=routes,vias=vs,displaced=displaced,removed_stale_H_VM=list(old)),indent=2)+'\n')
print('displaced',displaced,flush=True)

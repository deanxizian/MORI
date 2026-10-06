"""Reserve straight outward fanout before routing each protection comparator."""
import json,math
import pcbnew as k
from layout_P5 import *
from body_P5 import create
from close_P5 import connected
from geometry_guard_P5 import Guard
name,d,p,r=paths('power');b=k.LoadBoard(str(p));connected(b);k.SaveBoard(str(r/'before_comparator_spacing.kicad_pcb'),b);fs={f.GetReference():f for f in b.GetFootprints()}
poses={'R23':(65.5,19.5,180),'R24':(69,19.8,180),'R25':(65.5,21.2,0),'C21':(70.5,22,0),'R44':(72.6,28.5,0),'C40':(70.5,32.595,0)}
log=[]
for ref,pos in poses.items():
 f=fs[ref];log.append(dict(ref=ref,old=[*xy(f.GetPosition()),f.GetOrientationDegrees()],new=pos));setplace(f,*pos)
for ref in poses:
 bad=[g.GetReference()for g in b.GetFootprints()if g.GetReference()!=ref and g.GetLayer()==F and hit(courtyard(fs[ref]),courtyard(g),gap=0)];assert not bad,(ref,bad)
# Protection sense/logic routes are rebuilt after their connected groups move.
rebuild={'/W_SENSE','/W_OVSENSE','/W_REF','/FAULT_N','/W_BRAKE_GATE','/H_OVSENSE','/H_BRAKE_GATE'}
for t in list(b.GetTracks()):
 a,z=xy(t.GetStart()),xy(t.GetEnd());n=t.GetNetname()
 local_w=n=='/W_VM' and all(63.8<=v[0]<=70.7 and 16.2<=v[1]<=20.5 for v in [a,z])
 local_h=n=='/H_VM' and all(67<=v[0]<=73 and 29<=v[1]<=37 for v in [a,z])
 if n in rebuild or (local_w or local_h)and(isinstance(t,k.PCB_VIA)or t.GetWidth()<=mm(.25)):b.Delete(t)
create(b,'power');routes=[]
def add(n,ps,v=None):
 g=Guard(b,n);ok=all(g.line_clear(a,z,F)for a,z in zip(ps,ps[1:]))and(v is None or g.via_clear(v));print(n,ps,ok,flush=True)
 if ok:
  track(b,n,ps,.2,F)
  if v:via(b,n,*v,grid=False)
  routes.append(dict(net=n,points=ps,via=v))
for n,x in [('/W_OVSENSE',65.365),('/FAULT_N',66.635),('/W_VM',67.905)]:add(n,[(x,16.475),(x,17.85)],(x,17.85))
add('/H_VM',[(67.475,32.595),(69.725,32.595)])
add('/FAULT_N',[(67.475,33.865),(68.665,33.865),(69,34.2),(69.65,34.2)],(69.65,34.2))
add('/H_OVSENSE',[(67.475,35.135),(69,35.135)],(69,35.135))
add('/GND',[(71.275,32.595),(72.475,32.595)],(72.475,32.595))
add('/FAULT_N',[(44.5,31),(47.2,31)],(47.2,31))
k.SaveBoard(str(p),b);update('power',b);(r/'comparator_spacing.json').write_text(json.dumps(dict(placements=log,routes=routes),indent=2)+'\n')

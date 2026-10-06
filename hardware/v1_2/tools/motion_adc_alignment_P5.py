"""Align each ADC RC capacitor's signal pad with its series resistor."""
import json
import pcbnew as k
from layout_P5 import *
from close_P5 import connected
from body_P5 import create
from geometry_guard_P5 import Guard
name,d,p,r=paths('motion');b=k.LoadBoard(str(p));c=connected(b);k.SaveBoard(str(r/'before_ADC_alignment.kicad_pcb'),b);refs=['C9','C10','C11'];nets=['/BAT_ADC','/WHEEL_ADC','/CURRENT_ADC'];xs=[11.125,14.225,17.625];remove=set();log=[]
actual={t.m_Uuid.AsString():t for t in b.GetTracks()};parent_ref={q.m_Uuid.AsString():f.GetReference()for f in b.GetFootprints()for q in f.Pads()}
for ref in refs:
 f=b.FindFootprintByReference(ref);q=next(q for q in f.Pads()if q.GetNetname()=='/GND');todo=[q];seen=set();otherpads=[]
 while todo:
  t=todo.pop();uid=t.m_Uuid.AsString()
  if uid in seen:continue
  seen.add(uid);todo.extend(c.GetConnectedTracks(t));todo.extend(c.GetConnectedPads(t))
  if uid in parent_ref and parent_ref[uid]not in refs:otherpads.append(parent_ref[uid])
 assert not otherpads,(ref,otherpads)
 remove.update(seen&actual.keys())
for ref,x in zip(refs,xs):setplace(b.FindFootprintByReference(ref),x+.775,28,0,side='B')
for ref,x in zip(['R14','R15','R16'],xs):setplace(b.FindFootprintByReference(ref),x,25,-90,side='B')
for t in list(b.GetTracks()):
 if t.m_Uuid.AsString()in remove:b.Delete(t);continue
 if isinstance(t,k.PCB_VIA)or t.GetNetname()not in nets or t.GetLayer()!=B:continue
 if all(25.824<=v[1]<=28.001 for v in [xy(t.GetStart()),xy(t.GetEnd())]):b.Delete(t)
create(b,'motion')
for net,x,left in zip(nets,xs,[10.2,13.7,16.7]):
 for ps in [[(x,25.825),(x,28)],[(left,28),(x,28)]]:
  assert all(Guard(b,net).line_clear(a,z,B,.2)for a,z in zip(ps,ps[1:])),(net,ps)
  track(b,net,ps,.2,B)
assert Guard(b,'/WHEEL_ADC_IN').line_clear((15,24.175),(14.225,24.175),B,.2)
track(b,'/WHEEL_ADC_IN',[(15,24.175),(14.225,24.175)],.2,B)
for ref in refs:
 f=b.FindFootprintByReference(ref);q=next(q for q in f.Pads()if q.GetNetname()=='/GND');a=xy(q.GetPosition());g=Guard(b,'/GND');pick=next(g.portals(a,B,radius=3,step=.2),None);assert pick,ref
 _,v,ps=pick;track(b,'/GND',ps,.2,B);via(b,'/GND',*v,grid=False);log.append(dict(ref=ref,position=xy(f.GetPosition()),GND_path=ps,via=v));print(ref,ps,flush=True)
k.SaveBoard(str(p),b);(r/'ADC_alignment.json').write_text(json.dumps(log,indent=2)+'\n')

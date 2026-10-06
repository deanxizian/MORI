"""Space comparator feedback groups to reserve direct pin-escape corridors."""
import json
import pcbnew as k
from layout_P5 import *
from close_P5 import connected
from body_P5 import create
from body_keepouts_P3R1 import rectangle
name,d,p,r=paths('power');b=k.LoadBoard(str(p));connected(b);k.SaveBoard(str(r/'before_feedback_corridors.kicad_pcb'),b)
moves={'R23':(70.5,18.25,180),'R41':(62,38.5,0)}
for ref,pos in moves.items():setplace(b.FindFootprintByReference(ref),*pos)
for ref in moves:
 f=b.FindFootprintByReference(ref);bad=[g.GetReference()for g in b.GetFootprints()if g!=f and g.GetLayer()==f.GetLayer()and hit(courtyard(f),courtyard(g),0)];print(ref,'courtyard bounding candidates',bad);assert not set(bad)-{'C30'},(ref,bad)
removed=[]
for t in list(b.GetTracks()):
 remove=t.GetNetname()in['/W_SENSE','/W_OVSENSE','/H_SENSE']
 for ref in moves:
  f=b.FindFootprintByReference(ref);sh=rectangle(rect(f));own={q.GetNetname()for q in f.Pads()}
  if t.GetNetname()not in own and any(t.IsOnLayer(l)and t.GetEffectiveShape(l).Collide(sh,mm(.21))for l in [F,B]):remove=True
  for q in f.Pads():
   if q.GetNetname()!=t.GetNetname() and any(q.IsOnLayer(l)and t.IsOnLayer(l)and t.GetEffectiveShape(l).Collide(q.GetEffectiveShape(l),mm(.205))for l in [F,B]):remove=True
 if remove:
  assert isinstance(t,k.PCB_VIA)or t.GetWidth()<=mm(.25) or (t.GetNetname()=='/W_VM' and t.GetLength()<mm(2) and 63<xy(t.GetStart())[0]<66 and 20<xy(t.GetStart())[1]<23),(t.GetNetname(),k.ToMM(t.GetWidth()),xy(t.GetStart()),xy(t.GetEnd()))
  removed.append(dict(uuid=t.m_Uuid.AsString(),net=t.GetNetname()));b.Delete(t)
create(b,'power');k.SaveBoard(str(p),b);(r/'feedback_corridors.json').write_text(json.dumps(dict(moves=moves,removed=removed),indent=2)+'\n')
from port_escape_P5 import run
run('power',[('R52','2'),('U20','5')],protected_nets=['/W_REF','/W_OVSENSE','/H_SENSE','/FAULT_N','/BAT_ADC','/WHEEL_ADC'])

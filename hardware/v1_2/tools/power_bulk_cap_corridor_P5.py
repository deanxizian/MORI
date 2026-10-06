"""Keep the bulk capacitor on a load-width path; move dividers out of that path."""
import json,math
import pcbnew as k
from layout_P5 import *
from body_P5 import create
from close_P5 import connected
from geometry_guard_P5 import Guard
name,d,p,r=paths('power');b=k.LoadBoard(str(p));connected(b);k.SaveBoard(str(r/'before_bulk_cap_corridor.kicad_pcb'),b);fs={f.GetReference():f for f in b.GetFootprints()}
poses={'R52':(45.5,21,180),'R53':(47.5,24.5,-90)}
for ref,pos in poses.items():setplace(fs[ref],*pos)
for ref in poses:
 bad=[g.GetReference()for g in b.GetFootprints()if g.GetReference()!=ref and g.GetLayer()==F and hit(courtyard(fs[ref]),courtyard(g),gap=0)];assert not bad,(ref,bad)
for t in list(b.GetTracks()):
 n=t.GetNetname();a,z=xy(t.GetStart()),xy(t.GetEnd())
 if n=='/WHEEL_ADC' or n=='/BAT_ADC'and all(44<=v[0]<=48 and 34<v[1]<36 for v in [a,z]) or n=='/W_VM'and not isinstance(t,k.PCB_VIA)and t.GetWidth()<mm(.59)and all(43<v[0]<50 and 18<v[1]<25 for v in [a,z]):b.Delete(t)
create(b,'power');routes=[]
for n,ps,w in [('/W_VM',[(52.120799,16.205199),(48.4,19.925998),(48.4,22),(52,22)],1.5),('/W_VM',[(46.325,21),(48.4,21)],.2)]:
 ok=all(Guard(b,n).line_clear(a,z,F,w)for a,z in zip(ps,ps[1:]));print(n,w,ok,flush=True)
 if ok:track(b,n,ps,w,F);routes.append(dict(net=n,points=ps,width=w))
k.SaveBoard(str(p),b);update('power',b);(r/'bulk_cap_corridor.json').write_text(json.dumps(dict(placements=poses,routes=routes,J10_left_escape_pins=['5','6'],reason='C10 must not be fed through a 0.2 mm sensing branch; BAT/WHEEL ADC connector tails now escape toward their divider circuitry.'),indent=2)+'\n')

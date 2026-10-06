"""Place sense dividers in electrical order before routing their branches."""
import json
import pcbnew as k
from layout_P5 import *
from body_P5 import create
from close_P5 import connected
from geometry_guard_P5 import Guard
name,d,p,r=paths('power');b=k.LoadBoard(str(p));connected(b);k.SaveBoard(str(r/'before_divider_reorder.kicad_pcb'),b);fs={f.GetReference():f for f in b.GetFootprints()};changes={}
for ref,pos in [('R52',(48,20.5,-90)),('R53',(48,24,-90)),('R50',(39.5,24,0))]:
 f=fs[ref];changes[ref]=dict(old=[*xy(f.GetPosition()),f.GetOrientationDegrees()],new=pos);setplace(f,*pos)
for ref in changes:
 a=courtyard(fs[ref]);bad=[g.GetReference()for g in b.GetFootprints()if g.GetReference()!=ref and g.GetLayer()==F and hit(a,courtyard(g),gap=0)];assert not bad,(ref,bad)
removed=[]
for t in list(b.GetTracks()):
 a,z=xy(t.GetStart()),xy(t.GetEnd());n=t.GetNetname()
 local=n=='/W_VM' and all(46.9<=v[0]<=48.4 and 24<=v[1]<=27.9 for v in [a,z])
 if n in ['/WHEEL_ADC','/BAT_ADC'] or local:removed.append(t.m_Uuid.AsString());b.Delete(t)
create(b,'power');routes=[]
for n,ps,w in [('/BAT_MON',[(36.455,23),(37.675,23),(38.675,24)],.2),('/W_VM',[(48,19.675),(48,19.1),(49,18.1)],.2),('/WHEEL_ADC',[(48,21.325),(48,23.175)],.2)]:
 ok=all(Guard(b,n).line_clear(a,z,F,w)for a,z in zip(ps,ps[1:]));print(n,ok,flush=True)
 if ok:track(b,n,ps,w,F);routes.append(dict(net=n,points=ps))
k.SaveBoard(str(p),b);update('power',b);(r/'divider_reorder.json').write_text(json.dumps(dict(placements=changes,removed=removed,routes=routes),indent=2)+'\n')

"""Open the connector-left ADC corridor without narrowing a load conductor."""
import json,math
import pcbnew as k
from layout_P5 import *
from body_P5 import create
from close_P5 import connected
from geometry_guard_P5 import Guard,obstacles
name,d,p,r=paths('power');b=k.LoadBoard(str(p));connected(b);k.SaveBoard(str(r/'before_adc_corridor.kicad_pcb'),b);fs={f.GetReference():f for f in b.GetFootprints()}
setplace(fs['JP60'],35.5,27,0)
bad=[g.GetReference()for g in b.GetFootprints()if g.GetReference()!='R51'and g.GetLayer()==F and hit(courtyard(fs['R51']),courtyard(g),gap=0)];assert not bad,bad
oldids={'69866ddf-22d9-4a1e-b073-b77c9de1a5a9','ae18d71c-9d9a-4e07-94e9-e6ebdbaccd74','66260711-c2fd-4d1c-bc84-54fdc2a623f9','c12bd531-debc-44f2-97f9-c4e41298e775'}
for t in list(b.GetTracks()):
 if t.GetNetname()=='/BAT_ADC'or t.m_Uuid.AsString()in oldids or t.m_Uuid.AsString()=='f17db143-8782-4795-ae4d-416be7b2f96b':b.Delete(t)
create(b,'power');routes=[]
def add(n,ps,w,l):
 ok=all(Guard(b,n).line_clear(a,z,l,w)for a,z in zip(ps,ps[1:]));print(n,w,l,ok,flush=True)
 if ok:track(b,n,ps,w,l);routes.append(dict(net=n,points=ps,width=w,layer=l))
 return ok
new=(40,28.549599);g=Guard(b,'/H_PRE');print('via',g.via_clear(new,1.),[(l,obstacles(b,'/H_PRE',new,l,1.,True))for l in [F,B]],flush=True)
assert g.via_clear(new,1.)
assert add('/H_PRE',[(42.8752,22.6568),(40,25.532),(40,28.549599)],1,B)
assert add('/H_PRE',[(40,28.549599),(40,29.3928),(38.5064,30.8864)],1,F)
via(b,'/H_PRE',*new,vd=1,dr=.45,grid=False)
assert add('/BAT_ADC',[(40.325,24),(41.5,24)],.2,F)
assert add('/BAT_ADC',[(41.5,24),(41.5,35),(44.5,35)],.2,F)
k.SaveBoard(str(p),b);update('power',b);(r/'adc_corridor.json').write_text(json.dumps(dict(R51=[41.8,22.5,90],load_via=new,routes=routes),indent=2)+'\n')

import sys,json
import pcbnew as k
from layout_P5 import *
from body_P5 import create
from geometry_guard_P5 import Guard
from close_P5 import connected
name,d,p,r=paths('motion');b=k.LoadBoard(str(p));connected(b)
for t in list(b.GetTracks()):
 if t.GetNetname()=='/S288_BUS' or t.m_Uuid.AsString().startswith(('a4199a7b','58b1d907')):b.Delete(t)
create(b,'motion');log=[]
def add(n,ps,w,l):
 ok=all(Guard(b,n).line_clear(a,z,l,w)for a,z in zip(ps,ps[1:]));print(n,ok,flush=True)
 if ok:track(b,n,ps,w,l);log.append(dict(net=n,points=ps,width=w,layer=l))
add('/GND',[(46.775,6),(47.1,6),(48,5.1)],.2,B)
if Guard(b,'/GND').via_clear((48,5.1)):via(b,'/GND',48,5.1,grid=False)
add('/+5V_MOTION',[(58.5,3),(58.5,6.15),(48.85,6.15),(48.05,6.95),(45.65,6.95),(44.7,6)],.5,B)
add('/S288_BUS',[(51,3),(51,.7),(48.2,.7)],.2,F)
for n,ps in [('/FAULT_N',[(54.5,10),(54.5,7.8),(54,7.3),(48.5,7.3)]),('/CHG_N',[(56.5,10),(56.5,7.3),(56,6.8),(48.5,6.8)]),('/BAT_ADC_IN',[(58.5,10),(58.5,6.8),(58,6.3),(48.5,6.3)])]:add(n,ps,.2,F)
k.SaveBoard(str(p),b);(r/'top_bus_finish.json').write_text(json.dumps(log,indent=2)+'\n')

"""Ordered signal lanes in the free space between connector rows."""
import json
import pcbnew as k
from layout_P5 import *
from close_P5 import connected
from geometry_guard_P5 import Guard,obstacles
name,d,p,r=paths('motion');b=k.LoadBoard(str(p));connected(b);k.SaveBoard(str(r/'before_status_bus_rows.kicad_pcb'),b)
nets=['/FAULT_N','/CHG_N','/BAT_ADC_IN','/WHEEL_ADC_IN','/CURRENT_ADC_IN']
for t in list(b.GetTracks()):
 if t.GetNetname() in nets or (t.GetNetname()=='/+5V_MOTION' and max(xy(t.GetStart())[0],xy(t.GetEnd())[0])>45.5):b.Delete(t)
routes=[('/+5V_MOTION',[(58.5,3),(58.5,6.15),(45.45,6.15),(45.3,6),(44.7,6)],.5,B),
('/FAULT_N',[(54.5,10),(54.5,7.8),(54,7.3),(48.5,7.3)],.2,F),
('/CHG_N',[(56.5,10),(56.5,7.3),(56,6.8),(48.5,6.8)],.2,F),
('/BAT_ADC_IN',[(58.5,10),(58.5,6.8),(58,6.3),(48.5,6.3)],.2,F),
('/WHEEL_ADC_IN',[(60.5,10),(60.5,7.8),(60,7.3),(48.5,7.3)],.2,B),
('/CURRENT_ADC_IN',[(62.5,10),(62.5,7.3),(62,6.8),(48.5,6.8)],.2,B)]
log=[]
for n,ps,w,l in routes:
 g=Guard(b,n);ok=all(g.line_clear(a,z,l,w)for a,z in zip(ps,ps[1:]));print(n,ok,flush=True)
 if ok:track(b,n,ps,w,l);log.append(dict(net=n,points=ps,width=w,layer=l))
 else:
  import math
  bad=set()
  for a,z in zip(ps,ps[1:]):
   N=math.ceil(math.dist(a,z)/.1)
   for i in range(N+1):
    v=(a[0]+(z[0]-a[0])*i/N,a[1]+(z[1]-a[1])*i/N)
    if not g.clear(v,l,w):bad.update(obstacles(b,n,v,l,w))
  print(bad,flush=True)
k.SaveBoard(str(p),b);(r/'status_bus_rows.json').write_text(json.dumps(log,indent=2)+'\n')

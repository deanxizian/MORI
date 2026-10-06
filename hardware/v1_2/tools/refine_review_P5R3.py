from review_P5R3 import *
from geometry_guard_P5 import Guard
e=Edit('power');e.move('C76',(26.02,44.1),270)
for t in list(e.b.GetTracks()):
 if isinstance(t,k.PCB_VIA)and xy(t.GetPosition())==(24.05,42.2):t.SetWidth(mm(.8));t.SetDrill(mm(.3))
e.remove(ids=['d8d1146c'])
e.remove(net='/+5V_MOTION',predicate=lambda t:not isinstance(t,k.PCB_VIA)and any(xy(t.GetStart())==p for p in[(7.478,24.003),(6.978,24.503),(6.978,29.478)])and k.ToMM(t.GetWidth())<.4)
e.add('/+5V_MOTION',F,[(8.185,24.71),(7.478,25.417),(7.478,29.978)],.2)
e.remove(net='/WHEEL_ADC',predicate=lambda t:not isinstance(t,k.PCB_VIA)and xy(t.GetStart())in[(44.675,21),(44.675,22.6),(45.175,23.675)])
e.add('/WHEEL_ADC',F,[(44.675,21),(44.675,22.0642),(44.1392,22.6)],.2)
for ref,num in [('R51',2),('U40',4)]:
 g=Guard(e.b,'/GND')
 for dist,p,route in g.portals(e.pos(ref,num),F,radius=4,step=.15,vd=.8):
  if all(g.line_clear(u,v,F,.3)for u,v in zip(route,route[1:])):
   e.add('/GND',F,route,.3);e.via('/GND',p);print('ground return',ref,p,flush=True);break
 else:print('no new stitch',ref,flush=True)
e.save()

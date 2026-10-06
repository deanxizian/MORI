from review_P5R5 import *
from close_P5 import clusters
from route_native_P5 import connect
from geometry_guard_P5 import Guard,obstacles

e=Edit('power');e.remove(net='/M5_EN');g=Guard(e.b,'/M5_EN')
print('EN via',g.via_clear((38,25.7)),[obstacles(e.b,'/M5_EN',(38,25.7),l,.8,True)for l in[F,B]],flush=True)
pts=[(28.35,26),(29.35,26),(29.65,25.7),(38,25.7)]
print('EN escape',[g.line_clear(a,z,F,.2)for a,z in zip(pts,pts[1:])],flush=True)
if g.via_clear((38,25.7))and all(g.line_clear(a,z,F,.2)for a,z in zip(pts,pts[1:])):
 e.add('/M5_EN',F,pts,.2);e.via('/M5_EN',(38,25.7))
e.save()
for net in ['/WHEEL_ADC','/M5_EN']:
 cs=clusters(e.b,net);assert len(cs)==2
 starts,goals=cs
 print(net,'points',[len(c)for c in cs],flush=True)
 try:
  result=connect(e.b,net,next(iter(starts)),next(iter(goals)),[F,B],[F,B],(80,55),step=.1,width=.2,vd=.8,dr=.3,time_limit=50,max_nodes=900000,heuristic_weight=3,start_points=starts,goal_points=goals)
  print(result,flush=True);e.save()
 except RuntimeError as ex:print(ex,flush=True)

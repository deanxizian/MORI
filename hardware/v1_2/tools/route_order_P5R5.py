from review_P5R5 import *
from close_P5 import clusters
from route_native_P5 import connect

e=Edit('power');e.remove(net='/+5V_MOTION',predicate=lambda t:not isinstance(t,k.PCB_VIA)and t.GetLayer()==B and k.ToMM(t.GetWidth())<.4)
e.remove(net='/M5_EN');e.add('/M5_EN',F,[(28.35,26),(29.89,26)],.2);e.via('/M5_EN',(29.89,26))
old=k.LoadBoard(str(source('power')[2]));keep=['18fa7c2a','457a2a70','56ee8ba7','5f707fae','6f4e9e04','8c01c578','f8eeeb1e','2471f3b4','85f2e8e6','f4547de5','1ae637d5','38f1077b','c7f81bb3']
for t in old.GetTracks():
 if any(t.m_Uuid.AsString().startswith(u)for u in keep):
  q=t.Duplicate();q.SetNetCode(e.b.GetNetsByName()['/M5_EN'].GetNetCode());e.b.Add(q)
e.save()
for net in ['/M5_EN','/+5V_MOTION']:
 for iteration in range(3):
  cs=clusters(e.b,net)
  if len(cs)==1:break
  starts,goals=cs[:2]
  print(net,'clusters',len(cs),[len(c)for c in cs],flush=True)
  try:
   result=connect(e.b,net,next(iter(starts)),next(iter(goals)),[F,B],[F,B],(80,55),step=.1,width=.2,vd=.8,dr=.3,time_limit=50,max_nodes=900000,heuristic_weight=3,start_points=starts,goal_points=goals)
   print(result,flush=True);e.save()
  except RuntimeError as ex:print(ex,flush=True);break

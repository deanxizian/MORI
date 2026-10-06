"""Multi-endpoint signal repair with logged, limited copper displacement.

Pads, both body projections, load conductors, Kelvin/buck loops, and ground
ports remain hard obstacles. No electrical DRC rule is waived.
"""
import sys,json,time,math
import pcbnew as k
from layout_P5 import *
from close_P5 import clusters
from power_route_P5 import MAJOR
from route_native_P5 import connect

def repair(kind,net):
 n,d,p,r=paths(kind);b=k.LoadBoard(str(p));size=json.loads((d/'connectivity.json').read_text())['size'];net=net if net.startswith('/')else'/'+net;cs=sorted(clusters(b,net),key=len,reverse=True)
 if len(cs)<2:return []
 protected=set(MAJOR)|{'/GND','/+3V3','/KELVIN_P','/KELVIN_N','/M5_FB','/C5_FB','/M5_BOOT','/C5_BOOT','/FAULT_N'}
 removable=[t for t in b.GetTracks()if t.GetNetname()!=net and t.GetNetname()not in protected and (isinstance(t,k.PCB_VIA)or t.GetWidth()<=mm(.25))]
 for t in removable:b.Remove(t)
 soft=[(t.GetEffectiveShape(l),l)for t in removable for l in [F,B]if t.IsOnLayer(l)]
 before={t.m_Uuid.AsString()for t in b.GetTracks()};done=False
 for goal in cs[1:]:
  try:
   q=connect(b,net,next(iter(cs[0])),next(iter(goal)),[],[],size,step=.1016,width=.2,time_limit=50,max_nodes=500000,heuristic_weight=1.6,soft_shapes=soft,start_points=cs[0],goal_points=goal);done=True;break
  except RuntimeError as e:print(net,'blocked',e,flush=True)
 if not done:
  for t in removable:b.Add(t)
  return None
 new=[t for t in b.GetTracks()if t.m_Uuid.AsString()not in before];displaced=[]
 for t in removable:
  if any(t.IsOnLayer(l)and q.IsOnLayer(l)and t.GetEffectiveShape(l).Collide(q.GetEffectiveShape(l),mm(.205))for q in new for l in [F,B]):
   displaced.append(dict(net=t.GetNetname(),uuid=t.m_Uuid.AsString()));b.Add(t);b.Delete(t)
  else:b.Add(t)
 k.SaveBoard(str(p),b);(r/('negotiated_'+str(time.time_ns())+'.json')).write_text(json.dumps(dict(net=net,result=q if isinstance(q,dict)else None,displaced=displaced),indent=2)+'\n')
 print('REPAIR',net,'remaining',len(clusters(b,net)),'displaced',sorted({v['net']for v in displaced}),flush=True)
 return sorted({v['net']for v in displaced})
if __name__=='__main__':
 kind=sys.argv[1]
 for net in sys.argv[2:]:repair(kind,net)

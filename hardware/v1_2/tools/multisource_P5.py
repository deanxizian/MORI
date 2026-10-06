"""Join copper islands from every legal endpoint, avoiding repeated nearest-pair traps."""
import sys,time,json
import pcbnew as k
from layout_P5 import paths
from close_P5 import clusters,width_for
from route_native_P5 import connect

def run(kind,nets,widths=None,targets=None):
 name,d,p,r=paths(kind);b=k.LoadBoard(str(p));size=json.loads((d/'connectivity.json').read_text())['size'];log=[]
 for n in nets:
  n=n if n.startswith('/') else '/'+n;w=(widths or {}).get(n,width_for(kind,n))
  for iteration in range(25):
   cs=sorted(clusters(b,n,(targets or {}).get(n)),key=len,reverse=True)
   if len(cs)<2:break
   done=False
   for goal in cs[1:]:
    try:
     q=connect(b,n,next(iter(cs[0])),next(iter(goal)),[],[],size,step=.1016,width=w,vd=1 if w>.6 else .8,dr=.45 if w>.6 else .3,time_limit=40,max_nodes=500000,heuristic_weight=1.7,start_points=cs[0],goal_points=goal)
     log.append(q);k.SaveBoard(str(p),b);done=True;break
    except RuntimeError as e:print(n,'blocked',e,flush=True)
   if not done:break
  print(kind,n,'islands',len(clusters(b,n,(targets or {}).get(n))),flush=True)
 k.SaveBoard(str(p),b);(r/('multisource_'+str(int(time.time()))+'.json')).write_text(json.dumps(log,indent=2)+'\n')
if __name__=='__main__':run(sys.argv[1],sys.argv[2:])

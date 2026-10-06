"""Create a checked layer-access via for an otherwise single-layer net island.
Uses native shapes and existing outward traces; never modifies other nets.
Native DRC is required after use.
"""
import sys,math,json,time
import pcbnew as k
from layout_P5 import *
from close_P5 import clusters
from geometry_guard_P5 import Guard

def run(kind,nets):
 n,d,p,r=paths(kind);b=k.LoadBoard(str(p));log=[]
 for net in nets:
  if not net.startswith('/'):net='/'+net
  cs=clusters(b,net)
  if len(cs)<2:continue
  for csidx,c in enumerate(cs):
   if {l for ls in c.values() for l in ls}=={F,B}:continue
   other=[q for i,z in enumerate(cs) if i!=csidx for q in z];g=Guard(b,net);candidates=[]
   for t in b.GetTracks():
    if t.GetNetname()!=net or isinstance(t,k.PCB_VIA):continue
    a,z=xy(t.GetStart()),xy(t.GetEnd())
    if a not in c and z not in c:continue
    for i in range(1,20):
     v=(a[0]+(z[0]-a[0])*i/20,a[1]+(z[1]-a[1])*i/20)
     if g.via_clear(v):candidates.append((min(math.dist(v,q) for q in other),v,t.GetLayer(),[]))
   if not candidates:
    for a,ls in sorted(c.items(),key=lambda row:min(math.dist(row[0],q) for q in other))[:4]:
     for l in ls:
      for dist,v,ps in g.portals(a,l,radius=3.5,step=.2):
       candidates.append((dist*2+min(math.dist(v,q) for q in other),v,l,ps))
       if len(candidates)>15:break
   if not candidates:print(kind,net,'NO ACCESS',csidx,flush=True);continue
   score,v,l,ps=min(candidates,key=lambda q:q[0])
   if ps:track(b,net,ps,.2,l)
   via(b,net,*v,grid=False);log.append(dict(net=net,via=v,escape=ps,layer=l));print(kind,net,'ACCESS',v,flush=True)
   k.SaveBoard(str(p),b)
 (r/('layer_access_'+str(int(time.time()))+'.json')).write_text(json.dumps(log,indent=2)+'\n')
if __name__=='__main__':run(sys.argv[1],sys.argv[2:])

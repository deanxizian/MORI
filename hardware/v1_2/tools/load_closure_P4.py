"""Finish relocated power terminals at their documented load widths."""
import pcbnew as k,json,math
from helpers_P4 import paths
from layout_P3R1 import xy,F,B
from route_local_P4 import connect
_,d,p,r=paths('power');b=k.LoadBoard(str(p));log=[]
jobs=[('/PACK_FUSED',(14,7),(1.65,12),[F,B],[F],2),('/+5V_MOTION',(17.775,20),(4.5,21),[F],[F,B],.8)]
# BAT_MON reference anchors actually present in its main wide trunk.
ts=[t for t in b.GetTracks() if t.GetNetname()=='/BAT_MON' and t.Type()!=k.PCB_VIA_T and k.ToMM(t.GetWidth())>=1.99]
ends=sorted({(xy(t.GetStart()),t.GetLayer()) for t in ts}|{(xy(t.GetEnd()),t.GetLayer()) for t in ts},key=lambda x:math.dist((45,51),x[0]))
for n,a,z,al,zl,w in jobs:
 try:
  v=connect(b,n,a,z,al,zl,(80,55),step=.05,width=w,vd=1,dr=.45,max_nodes=500000,time_limit=35);log.append(dict(status='ROUTED',width_mm=w,**v))
 except RuntimeError as e:print('BLOCKED LOAD',n,e);log.append(dict(status='BLOCKED',net=n,error=str(e)))
 k.SaveBoard(str(p),b)
for z,l in ends[:8]:
 try:
  v=connect(b,'/BAT_MON',(45,51),z,[F,B],[l],(80,55),step=.1,width=2,vd=1,dr=.45,max_nodes=350000,time_limit=20);log.append(dict(status='ROUTED',width_mm=2,**v));break
 except RuntimeError as e:print('BAT_MON anchor',z,e)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);(r/'load_closure.json').write_text(json.dumps(log,indent=2)+'\n')

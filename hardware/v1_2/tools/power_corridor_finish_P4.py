"""Rebuild only the displaced wheel supply corridor at its original width.

The optional service connector is kept in the top connector row. Source and
return paths retain their native pin assignments. Follow with native DRC.
"""
import pcbnew as k,json
from helpers_P4 import paths
from layout_P3R1 import track,via,xy,F,B
from geometry_guard_P3R1 import Guard
from route_local_P4 import connect
_,d,p,r=paths('power');b=k.LoadBoard(str(p));k.SaveBoard(str(r/'before_wheel_corridor_repair.kicad_pcb'),b)
remove={'bd6be16d-6926-46d7-ac56-c53004b238f8','38370b16-700d-4f6b-8dc8-f70bdf1b98c5','abc5ec09-798c-4610-9135-6b143e5b9e82'}
for t in list(b.GetTracks()):
 if t.GetNetname()=='/W9_IN' or t.m_Uuid.AsString() in remove:b.Delete(t)
fps={f.GetReference():f for f in b.GetFootprints()}
def pad(ref,n):return next(q for q in fps[ref].Pads() if q.GetNumber()==n)
log=[]
for net,a,z,al,zl,w in [('/W9_IN',xy(pad('J3','2').GetPosition()),xy(pad('D10','1').GetPosition()),[F,B],[B],1.5),('/W_VM',(53.5,14.5),(64.5,18),[F,B],[F,B],1.5)]:
 try:
  v=connect(b,net,a,z,al,zl,(80,55),step=.05,width=w,vd=1,dr=.45,max_nodes=700000,time_limit=50);log.append(dict(status='ROUTED',width_mm=w,**v))
 except RuntimeError as e:log.append(dict(status='BLOCKED',net=net,error=str(e)));print('BLOCKED',net,e,flush=True)
 k.SaveBoard(str(p),b)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);(r/'wheel_corridor_repair.json').write_text(json.dumps(log,indent=2)+'\n')

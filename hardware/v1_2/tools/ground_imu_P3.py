import pcbnew as k
import json
from layout_P3 import paths,xy,F,B
from route_local_P2 import connect
from close_routes_P2 import merge_lines,snap_via_ends
name,d,p,r=paths('imu');b=k.LoadBoard(str(p));fps={f.GetReference():f for f in b.GetFootprints()}
for t in list(b.GetTracks()):
 if t.GetNetname()=='/GND':b.Delete(t)
def pos(ref,n):return xy(next(p for p in fps[ref].Pads() if p.GetNumber()==str(n)).GetPosition())
pairs=[(('U1',2),('U1',3)),(('U1',6),('U1',7)),(('U1',9),('U1',10)),(('U1',10),('U1',11)),(('U1',3),('J1',2)),(('U1',7),('C3',2)),(('U1',9),('C1',2)),(('C3',2),('C2',2)),(('C1',2),('J1',8)),(('J1',2),('J1',8)),(('C3',2),('J1',2))]
log=[]
for a,z in pairs:log.append(connect(b,'/GND',pos(*a),pos(*z),[F],[F],(20,16),step=.05))
merge_lines(b);snap_via_ends(b);k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);(r/'ground_routes.json').write_text(json.dumps(log,indent=2)+'\n')

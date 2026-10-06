import sys,json
import pcbnew as k
from layout_P5 import *
from geometry_guard_P5 import Guard,obstacles
name,d,p,r=paths('imu');b=k.LoadBoard(str(p));fan=json.loads((r/'fanout.json').read_text())['routes'];delids={u for q in fan if q['ref']=='J1' and q['net']=='/GND' for u in q['tracks']}
for t in list(b.GetTracks()):
 if t.GetNetname() in ['/MISO','/DRDY'] or t.m_Uuid.AsString() in delids:b.Delete(t)
g=Guard(b,'/MISO');vs=[(11.3792,6.9088),(5.6388,7.0104)]
for v in vs:assert g.via_clear(v),('via',v)
jobs=[(F,[(10.8792,3.5),(10.8792,6.4088),vs[0]]),(F,[(6.1388,8.025),(6.1388,7.5104),vs[1]]),(B,[vs[0],(11.3792,7.4),(10.8792,7.9),(6.1388,7.9),(5.6388,7.4),vs[1]])]
for l,ps in jobs:
 for a,z in zip(ps,ps[1:]):assert g.line_clear(a,z,l),('segment',a,z,b.GetLayerName(l))
 track(b,'/MISO',ps,.2,l)
for v in vs:via(b,'/MISO',*v,grid=False)
k.SaveBoard(str(p),b);(r/'MISO_corridor.json').write_text(json.dumps(dict(vias=vs,paths=jobs),indent=2)+'\n')
print('MISO manual corridor saved')

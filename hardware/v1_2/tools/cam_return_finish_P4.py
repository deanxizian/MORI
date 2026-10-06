"""Keep C7 close to TXU0202 and establish its ground return before VCC routing."""
import pcbnew as k,json,math
from helpers_P4 import paths
from layout_P3R1 import track,via,xy,F,B
from geometry_guard_P3R1 import Guard
from route_local_P4 import connect
_,d,p,r=paths('motion');b=k.LoadBoard(str(p));k.SaveBoard(str(r/'before_CAM_supply_refresh.kicad_pcb'),b)
for t in list(b.GetTracks()):
 if t.GetNetname()=='/CAM_3V3':b.Delete(t)
g=Guard(b,'/GND');port=next(g.portals((36.725,14),B,radius=4,step=.1),None)
assert port
_,pos,ps=port;track(b,'/GND',ps,.2,B);via(b,'/GND',*pos,grid=False);print('C7 ground escape',pos,flush=True)
log=[dict(net='/GND',points_mm=ps,via_mm=pos)]
root=next(q for f in b.GetFootprints() if f.GetReference()=='C7' for q in f.Pads() if q.GetNetname()=='/CAM_3V3');pads=[q for f in b.GetFootprints() if f.GetReference()!='C7' for q in f.Pads() if q.GetNetname()=='/CAM_3V3']
# Route local IC-capacitor branch first; retain both remote reference and local bypass.
for q in sorted(pads,key=lambda q:math.dist(xy(q.GetPosition()),xy(root.GetPosition()))):
 a,z=xy(q.GetPosition()),xy(root.GetPosition());al=[l for l in [F,B] if q.IsOnLayer(l)];zl=[l for l in [F,B] if root.IsOnLayer(l)]
 try:res=connect(b,'/CAM_3V3',a,z,al,zl,(70,35),step=(.05 if math.dist(a,z)<10 else .1),width=.2,vd=.8,dr=.3,max_nodes=600000,time_limit=40,heuristic_weight=1.5);log.append(res)
 except RuntimeError as e:print('CAM branch',e,flush=True);log.append(dict(error=str(e)))
 k.SaveBoard(str(p),b)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);(r/'CAM_supply_refresh.json').write_text(json.dumps(log,indent=2)+'\n')

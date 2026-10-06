"""Route CHG_N locally after securing the comparator/control ground return."""
import pcbnew as k,json,math
from helpers_P4 import paths
from layout_P3R1 import track,via,xy,F,B
from geometry_guard_P3R1 import Guard
from route_local_P4 import connect
_,d,p,r=paths('power');b=k.LoadBoard(str(p));k.SaveBoard(str(r/'before_CHG_local.kicad_pcb'),b)
for t in list(b.GetTracks()):
 if t.GetNetname()=='/CHG_N':b.Delete(t)
ps=[(53.4375,38),(54.5,38),(55,37.5),(57.2,37.5),(57.605,37.095),(60.525,37.095)];assert all(Guard(b,'/GND').line_clear(a,z,B,.2) for a,z in zip(ps,ps[1:]));track(b,'/GND',ps,.2,B)
pads=[(f.GetReference(),q) for f in b.GetFootprints() for q in f.Pads() if q.GetNetname()=='/CHG_N'];print('CHG terminals',[(f,q.GetNumber(),xy(q.GetPosition())) for f,q in pads],flush=True)
root=next(q for f,q in pads if f=='Q50');source=xy(root.GetPosition());port=next(Guard(b,'/CHG_N').portals(source,B,radius=3,step=.1),None);print('Q50 port',port,flush=True)
if port:
 _,source,ps=port;track(b,'/CHG_N',ps,.2,B);via(b,'/CHG_N',*source,grid=False)
log=[]
for ref,q in sorted(pads,key=lambda rq:math.dist(xy(rq[1].GetPosition()),source)):
 if ref=='Q50':continue
 a=xy(q.GetPosition());al=[l for l in [F,B] if q.IsOnLayer(l)]
 try:
  v=connect(b,'/CHG_N',a,source,al,[F,B],(80,55),step=.1,width=.2,vd=.8,dr=.3,max_nodes=550000,time_limit=35,heuristic_weight=1.5);log.append(v)
 except RuntimeError as e:print(e,flush=True);log.append(dict(ref=ref,error=str(e)))
 k.SaveBoard(str(p),b)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);(r/'charge_signal_local.json').write_text(json.dumps(log,indent=2)+'\n')

"""Join split ground regions at shape-checked plane overlaps. P3R1 only."""
import sys,json,math
import pcbnew as k
from layout_P3R1 import paths,xy,pt,F,B,via
from geometry_guard_P3R1 import Guard
kind=sys.argv[1];_,d,p,r=paths(kind);b=k.LoadBoard(str(p));log=[]
for z in list(b.Zones()):
 if z.GetIsRuleArea() or z.GetNetname()!='/GND':continue
 poly=z.GetFilledPolysList(z.GetLayer());other=[q for q in b.Zones() if not q.GetIsRuleArea() and q.GetLayer()!=z.GetLayer() and q.GetNetname()=='/GND'][0].GetFilledPolysList(B if z.GetLayer()==F else F)
 for i in range(1,poly.OutlineCount()):
  guard=Guard(b,'/GND');bb=poly.COutline(i).BBox();x1,y1,x2,y2=[k.ToMM(v) for v in [bb.GetX(),bb.GetY(),bb.GetRight(),bb.GetBottom()]];cand=[]
  for ix in range(math.ceil(x1/.254),math.floor(x2/.254)+1):
   for iy in range(math.ceil(y1/.254),math.floor(y2/.254)+1):
    pos=(ix*.254,iy*.254);v=pt(*pos)
    if poly.Contains(v,i) and other.Contains(v) and guard.via_clear(pos):
     if any(isinstance(t,k.PCB_VIA) and math.dist(xy(t.GetPosition()),pos)<1 for t in b.GetTracks()):continue
     cand.append((math.dist(pos,((x1+x2)/2,(y1+y2)/2)),pos))
  if cand:
   pos=min(cand)[1];via(b,'GND',*pos,grid=False);log.append(dict(layer=k.LayerName(z.GetLayer()),polygon=i,via=pos))
  else:print('no plane-overlap via',k.LayerName(z.GetLayer()),i,flush=True)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);(r/'island_stitches.json').write_text(json.dumps(log,indent=2)+'\n');print(kind,'added',len(log),'ground stitches')

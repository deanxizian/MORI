"""Join actual isolated ground copper through clear same-net plane overlaps.

All copper layers take part in connectivity; routing remains F/B only. This
avoids confusing a motion-board plane connection with a separate ground island.
"""
import sys,json,math,runpy
import pcbnew as k
from helpers_P4 import paths
from layout_P3R1 import xy,pt,F,B,via
from geometry_guard_P3R1 import Guard
kind=sys.argv[1];_,d,p,r=paths(kind);b=k.LoadBoard(str(p));log=[]
# Reuse read-only polygon/component graph with internal plane connectivity.
src=(d.parents[1]/'tools/bridge_ground_P3R1.py').read_text();src=src[src.index('def regions():'):src.index('\nlog=[]')]
src=src.replace('for l in [F,B]:','for l in ([F,B,k.In1_Cu,k.In2_Cu] if kind==\'motion\' else [F,B]):')
src=src.replace("if label!='zone':continue","if label!='zone' or l not in [F,B]:continue")
exec(src)
for _ in range(12):
 k.ZONE_FILLER(b).Fill(b.Zones());groups=regions();print(kind,'groups',len(groups),[len(g) for g in groups],flush=True)
 if len(groups)==1:break
 g=Guard(b,'/GND');main=groups[0];added=False
 for group in groups[1:]:
  for x,y,l in sorted(samples(group,g,.2)):
   if not g.via_clear((x,y)):continue
   pos=pt(x,y)
   if any(label=='zone' and ll!=l and sh.Collide(pos,0) for label,sh,ll in main):
    via(b,'/GND',x,y,grid=False);log.append(dict(point=[x,y],from_layer=l,status='overlap_stitch'));added=True;print('stitched',x,y,flush=True);break
  if added:break
 if not added:print('no direct overlap; explicit return bridge needed',flush=True);break
 k.SaveBoard(str(p),b)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);(r/'ground_overlap_stitches.json').write_text(json.dumps(log,indent=2)+'\n')

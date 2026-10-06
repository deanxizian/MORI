"""Stitch isolated outer GND polygons at clear overlap locations; no body exceptions."""
import sys,json,math
import pcbnew as k
from update_native_P5R7 import *
F,B=k.F_Cu,k.B_Cu
from geometry_guard_P5 import Guard
kind='motion';name,d,p=paths(kind);r=HERE/'reports/motion';(r/'before_final_stitch.kicad_pcb').write_bytes(p.read_bytes());b=k.LoadBoard(str(p));k.ZONE_FILLER(b).Fill(b.Zones())
polys=[];keys=[];layers={F,B}
if kind=='motion':layers.update([k.In1_Cu])
for z in b.Zones():
 if z.GetIsRuleArea() or z.GetNetname()!='/GND':continue
 l=z.GetLayer()
 if l not in layers:continue
 s=z.GetFilledPolysList(l)
 for i in range(s.OutlineCount()):keys.append((z.GetZoneName(),i,l));polys.append((s,i,l))
parent=list(range(len(polys)))
def root(i):
 while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
 return i
def union(ids):
 for j in ids[1:]:parent[root(j)]=root(ids[0])
def at(v,ls):return [i for i,(s,j,l)in enumerate(polys)if l in ls and s.Contains(v,j)]
for f in b.GetFootprints():
 for q in f.Pads():
  if q.GetNetname()=='/GND' and q.GetAttribute()==k.PAD_ATTRIB_PTH:union(at(q.GetPosition(),layers))
for t in b.GetTracks():
 if isinstance(t,k.PCB_VIA) and t.GetNetname()=='/GND':union(at(t.GetPosition(),layers))
size=json.loads((d/'connectivity.json').read_text())['size'];g=Guard(b,'/GND');log=[]
# Candidate order favours the middle of each island's bounding box, and a
# 0.5 mm design grid; exact package/clearance checks still use native shapes.
cands=[]
for x in [v*.5 for v in range(3,int(size[0]*2)-2)]:
 for y in [v*.5 for v in range(3,int(size[1]*2)-2)]:
  ids=at(pt(x,y),layers)
  if len({root(i)for i in ids})<2:continue
  if any(x1-.4<=x<=x2+.4 and y1-.4<=y<=y2+.4 for x1,y1,x2,y2 in [(5.85,.99,44.45,6.07),(5.85,28.93,44.45,34.01),(33.66,17.76,38.74,28.42)]):continue
  if not g.via_clear((x,y)):continue
  cands.append((x,y,ids))
while cands:
 useful=[]
 for x,y,ids in cands:
  distinct=len({root(i)for i in ids})
  if distinct>1:
   near=min((math.dist((x,y),q)for q in g.own_vias),default=20)
   useful.append((-distinct,-min(near,5),x,y,ids))
 if not useful:break
 _,_,x,y,ids=min(useful);via(b,'/GND',x,y,grid=False);union(ids);g.own_vias.append((x,y));log.append(dict(position=[x,y],polygons=[keys[i]for i in ids]));cands=[v for v in cands if math.dist(v[:2],(x,y))>1]
# Net propagation from old fills is not used during edits.
for z in b.Zones():
 if not z.GetIsRuleArea():z.UnFill()
k.SaveBoard(str(p),b);(r/'ground_polygon_stitches.json').write_text(json.dumps(dict(stitches=log,remaining_components=len({root(i)for i in range(len(polys))})),indent=2)+'\n');print(kind,'added',len(log),'stitches','components',len({root(i)for i in range(len(polys))}),flush=True)

oldname,oldd,_=paths('motion','P5R6')
(d/(name+'.kicad_pro')).write_text((oldd/(oldname+'.kicad_pro')).read_text().replace(oldname,name).replace('V1.2-H0.5-P5R6','V1.2-H0.5-P5R7'))
checks('motion','ground_stitched')

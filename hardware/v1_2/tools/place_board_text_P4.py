"""Move board-level references out of exposed copper and other silk.

Reference names stay local to their original component region. Component
geometry and copper are not changed by this script.
"""
import pcbnew as k,sys,json,math,re
from helpers_P4 import paths
from layout_P3R1 import pt,xy,F,B
kind=sys.argv[1];_,d,p,r=paths(kind);b=k.LoadBoard(str(p));j=json.loads((r/'drc.json').read_text());size={'motion':(70,35),'power':(80,55),'imu':(20,16),'rear':(24,25)}[kind]
uids={i['uuid'] for v in j['violations'] if v['type'] in ['silk_over_copper','silk_overlap','silk_edge_clearance'] for i in v['items']};log=[]
def box(o):
 z=o.GetBoundingBox();return [k.ToMM(z.GetX()),k.ToMM(z.GetY()),k.ToMM(z.GetRight()),k.ToMM(z.GetBottom())]
def overlap(a,z,m):return a[0]<z[2]+m and a[2]>z[0]-m and a[1]<z[3]+m and a[3]>z[1]-m
for t in b.GetDrawings():
 if not isinstance(t,k.PCB_TEXT) or t.m_Uuid.AsString() not in uids:continue
 if not re.match(r'^(?:[JCRDLQUF]\d+|JP\d+|TP\d+|MORI\b)',t.GetText()):continue
 old=xy(t.GetPosition());layer=t.GetLayer();cu=F if layer==k.F_SilkS else B;mask=k.F_Mask if cu==F else k.B_Mask;obs=[]
 for f in b.GetFootprints():
  for q in f.Pads():
   if q.IsOnLayer(mask):obs.append((box(q),.06))
  for g in f.GraphicalItems():
   if g.GetLayer()==layer:obs.append((box(g),.10))
  for g in [f.Reference(),f.Value()]:
   if g.GetLayer()==layer and g.IsVisible():obs.append((box(g),.10))
 for v in b.GetTracks():
  if v.Type()==k.PCB_VIA_T:obs.append((box(v),.06))
 for g in b.GetDrawings():
  if g.m_Uuid.AsString()!=t.m_Uuid.AsString() and g.GetLayer()==layer:obs.append((box(g),.10))
 candidates=sorted((math.hypot(i,j),i*.25,j*.25) for i in range(-24,25) for j in range(-24,25))
 found=False
 for _,dx,dy in candidates:
  t.SetPosition(pt(old[0]+dx,old[1]+dy));bb=box(t)
  if bb[0]<.6 or bb[1]<.6 or bb[2]>size[0]-.6 or bb[3]>size[1]-.6:continue
  if any(overlap(bb,z,m) for z,m in obs):continue
  found=True;log.append(dict(text=t.GetText(),old_xy_mm=old,new_xy_mm=xy(t.GetPosition())));break
 if not found:t.SetPosition(pt(*old));print('no local label space',t.GetText(),flush=True)
k.SaveBoard(str(p),b);(r/'text_placement.json').write_text(json.dumps(log,indent=2)+'\n');print('labels moved',len(log))

"""Read-only placement screen against both outer copper projections."""
import sys,math,json
import pcbnew as k
from layout_P5 import *
from close_P5 import connected
from body_keepouts_P3R1 import rectangle
kind,ref=sys.argv[1:3];n,d,p,r=paths(kind);b=k.LoadBoard(str(p));connected(b);f=b.FindFootprintByReference(ref);origin=xy(f.GetPosition());ns={q.GetNetname() for q in f.Pads()}
other=[(g.GetReference(),courtyard(g)) for g in b.GetFootprints() if g!=f and g.GetLayer()==f.GetLayer()]
tracks=[]
for t in b.GetTracks():
 for l in [F,B]:
  if t.IsOnLayer(l):
   sh=t.GetEffectiveShape(l);bb=sh.BBox();box0=[k.ToMM(v) for v in [bb.GetX(),bb.GetY(),bb.GetRight(),bb.GetBottom()]];tracks.append((sh,box0,t.GetNetname(),isinstance(t,k.PCB_VIA)))
results=[]
for a in [0,90,180,270]:
 for ix in range(10,87):
  for iy in range(36,97):
   x,y=ix*.5,iy*.5;setplace(f,x,y,a);cr=courtyard(f)
   if any(hit(cr,c,0) for _,c in other):continue
   fr=rect(f);shape=rectangle(fr);failed=False
   for sh,bo,net,isvia in tracks:
    if net not in ns and hit(fr,bo,.003) and sh.Collide(shape,mm(.002)):failed=True;break
    for q in f.Pads():
     bb=q.GetBoundingBox();qb=[k.ToMM(v) for v in [bb.GetX(),bb.GetY(),bb.GetRight(),bb.GetBottom()]]
     if (isvia or net!=q.GetNetname()) and hit(qb,bo,.21) and sh.Collide(q.GetEffectiveShape(F),mm(.205)):failed=True;break
    if failed:break
   if not failed:results.append(dict(x=x,y=y,a=a,d=math.dist((x,y),origin),rect=fr))
results.sort(key=lambda x:x['d']);print(json.dumps(results[:25],indent=2));(r/(ref+'_placement_candidates.json')).write_text(json.dumps(results,indent=2)+'\n')

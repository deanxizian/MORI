"""Group placement changes to open signal fanout corridors on both PCB faces."""
import sys,json,math
import pcbnew as k
from layout_P3R1 import paths,xy,pt,mm,setplace,track,via,F,B
from body_keepouts_P3R1 import create
from geometry_guard_P3R1 import Guard,obstacles
kind=sys.argv[1];name,d,p,r=paths(kind);b=k.LoadBoard(str(p));fps={f.GetReference():f for f in b.GetFootprints()};changes=[];ports=[]
placements={'motion':{'J3':(59.5,20.5,90,'F'),'R8':(63.5,16.75,0,'B'),'R13':(48.25,18.5,90,'B')},'power':{'J10':(45,29,180,'F'),'J15':(56,28.5,180,'F')}}[kind]
for ref,args in placements.items():
 f=fps[ref];old=list(xy(f.GetPosition()))+[f.GetOrientationDegrees()]
 for t in list(b.GetTracks()):
  if isinstance(t,k.PCB_VIA):continue
  if any(t.GetNetCode()==q.GetNetCode() and q.IsOnLayer(t.GetLayer()) and t.GetEffectiveShape(t.GetLayer()).Collide(q.GetEffectiveShape(t.GetLayer()),mm(.001)) for q in f.Pads()):b.Delete(t)
 setplace(f,*args);changes.append(dict(ref=ref,before=old,after=args))
zones=create(b);k.SaveBoard(str(p),b)
(r/'body_keepouts.json').write_text(json.dumps(zones,indent=2)+'\n')
(r/'header_group_placements.json').write_text(json.dumps(changes,indent=2)+'\n')
print(kind,'header corridor placement updated',flush=True)

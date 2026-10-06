"""Place board-level connector labels beside their actual P4 footprint.

Silkscreen only. Avoid old placement anchors and update face after connector flips.
"""
import pcbnew as k
import json,math,re,sys
from helpers_P4 import paths
from layout_P3R1 import pt,xy,mm
from audit_body_routes_P4 import rect
def bb(o):
 b=o.GetBoundingBox();return [k.ToMM(v) for v in [b.GetX(),b.GetY(),b.GetRight(),b.GetBottom()]]
def overlap(a,z,m):return a[0]<z[2]+m and a[2]>z[0]-m and a[1]<z[3]+m and a[3]>z[1]-m
for kind in sys.argv[1:]:
 _,d,p,r=paths(kind);b=k.LoadBoard(str(p));k.SaveBoard(str(r/'before_connector_labels.kicad_pcb'),b)
 size={'motion':(70,35),'power':(80,55),'imu':(20,16),'rear':(24,25)}[kind]
 fps={f.GetReference():f for f in b.GetFootprints()};pattern=r'(?:J[P]?|USB|SW)\d+'
 existing={t.GetText() for t in b.GetDrawings() if isinstance(t,k.PCB_TEXT) and t.GetLayer() in [k.F_SilkS,k.B_SilkS]}
 for ref,f in fps.items():
  if re.fullmatch(pattern,ref) and ref not in existing and not f.Reference().IsVisible():
   t=k.PCB_TEXT(b);t.SetText(ref);t.SetPosition(f.GetPosition());t.SetLayer(k.B_SilkS if f.IsFlipped() else k.F_SilkS);b.Add(t)
 texts=[t for t in b.GetDrawings() if isinstance(t,k.PCB_TEXT) and t.GetLayer() in [k.F_SilkS,k.B_SilkS] and re.fullmatch(pattern,t.GetText()) and t.GetText() in fps]
 ids={t.m_Uuid.AsString() for t in texts};placed=[];log=[]
 for t in texts:
  f=fps[t.GetText()];body=rect(f);old=xy(t.GetPosition());oldlayer=b.GetLayerName(t.GetLayer());layer=k.B_SilkS if f.IsFlipped() else k.F_SilkS;cu=f.GetLayer();mask=k.B_Mask if f.IsFlipped() else k.F_Mask;t.SetLayer(layer)
  t.SetMirrored(f.IsFlipped());t.SetTextSize(pt(.8,.8));t.SetTextThickness(mm(.12));obs=[]
  for ff in b.GetFootprints():
   rr=rect(ff)
   if ff.GetLayer()==cu and rr:obs.append((rr,.12))
   for q in ff.Pads():
    if q.IsOnLayer(mask):obs.append((bb(q),.08))
   for g in ff.GraphicalItems():
    if g.GetLayer()==layer:obs.append((bb(g),.12))
  for v in b.GetTracks():
   if v.Type()==k.PCB_VIA_T:obs.append((bb(v),.08))
  for g in list(b.GetDrawings())+placed:
   if g.m_Uuid.AsString()==t.m_Uuid.AsString():continue
   if g.m_Uuid.AsString() in ids and g not in placed:continue
   if g.GetLayer()==layer:obs.append((bb(g),.12))
  cx,cy=(body[0]+body[2])/2,(body[1]+body[3])/2
  candidates=[]
  for angle in [0,90]:
   for i in range(math.floor((body[0]-3)/.25),math.ceil((body[2]+3)/.25)+1):
    for j in range(math.floor((body[1]-3)/.25),math.ceil((body[3]+3)/.25)+1):
     x,y=i*.25,j*.25
     # Prefer close, centered positions outside the plastic body.
     dist=math.hypot(x-cx,y-cy);candidates.append((dist+(.3 if angle else 0),x,y,angle))
  done=False
  for _,x,y,angle in sorted(candidates):
   t.SetTextAngle(k.EDA_ANGLE(angle,k.DEGREES_T));t.SetPosition(pt(x,y));box=bb(t)
   if box[0]<.5 or box[1]<.5 or box[2]>size[0]-.5 or box[3]>size[1]-.5:continue
   if any(overlap(box,z,m) for z,m in obs):continue
   done=True;placed.append(t);log.append(dict(ref=t.GetText(),old=old,old_layer=oldlayer,new=[x,y],new_layer=b.GetLayerName(layer),angle=angle));break
  if not done:raise RuntimeError(('No connector label location',kind,t.GetText()))
 k.SaveBoard(str(p),b);(r/'connector_label_anchors.json').write_text(json.dumps(log,indent=2)+'\n');print(kind,len(log),'connector labels anchored')

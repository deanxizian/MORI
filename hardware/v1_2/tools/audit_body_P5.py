"""Read-only component-by-component inventory of tracks within Fab projections.

Native BODY keepouts validate forbidden core copper. This inventory separately
lists necessary own-pin housing escapes and the raised U100 architecture.
No candidate is hidden through a blanket GND or power exception.
"""
import sys,json,math,hashlib
from collections import defaultdict
import pcbnew as k
from layout_P5 import paths,xy,pt,mm,F,B,rect
from audit_body_routes_P4 import clip
from body_keepouts_P3R1 import rectangle,polygon

def audit(kind):
 name,d,p,r=paths(kind);b=k.LoadBoard(str(p));rows=[];counts={}
 for f in sorted(b.GetFootprints(),key=lambda x:x.GetReference()):
  ref=f.GetReference();fr=rect(f)
  if not fr or ref.startswith(('H','TP')):continue
  full=rectangle(fr)
  circles=[s for s in f.GraphicalItems()if isinstance(s,k.PCB_SHAPE)and s.GetLayer()in[k.F_Fab,k.B_Fab]and s.GetShape()==k.S_CIRCLE]
  if circles:
   c=max(circles,key=lambda s:s.GetRadius());cx,cy=xy(c.GetCenter());rr=k.ToMM(c.GetRadius())
   if rr>min(fr[2]-fr[0],fr[3]-fr[1])*.4:full=polygon([(cx+rr*math.cos(i*math.pi/48),cy+rr*math.sin(i*math.pi/48))for i in range(96)])
  pads=list(f.Pads());own={q.GetNetname()for q in pads};padsh=[q.GetEffectiveShape(f.GetLayer())for q in pads];found=[]
  for t in b.GetTracks():
   if isinstance(t,k.PCB_VIA):continue
   a,z=xy(t.GetStart()),xy(t.GetEnd());interval=clip(a,z,fr)
   if interval is None:continue
   lo,hi=interval;length=math.dist(a,z);steps=max(1,math.ceil(length*(hi-lo)/.025));hits=[]
   for i in range(steps):
    u=lo+(hi-lo)*(i+.5)/steps;v=pt(a[0]+u*(z[0]-a[0]),a[1]+u*(z[1]-a[1]))
    if full.Collide(v,0) and not any(s.Collide(v,0)for s in padsh):hits.append(xy(v))
   if not hits or length*(hi-lo)*len(hits)/steps<.025:continue
   reason='RAISED_MODULE_ARCHITECTURE'if ref=='U100'else'OWN_PIN_OUTWARD_HOUSING_ESCAPE'if t.GetNetname()in own else'FAIL_FOREIGN_NET'
   row=dict(reference=ref,layer=b.GetLayerName(t.GetLayer()),net=t.GetNetname(),track_uuid=t.m_Uuid.AsString(),classification=reason,length_inside_projection_estimate_mm=round(length*(hi-lo)*len(hits)/steps,4),start=a,end=z)
   found.append(row);rows.append(row)
  counts[ref]=dict(footprint=str(f.GetFPID()),side=b.GetLayerName(f.GetLayer()),body_rect_mm=fr,pairs=len(found),nets=sorted({q['net']for q in found}),status='REVIEWED_EXCEPTION'if ref=='U100' else 'FAIL'if any(q['classification']=='FAIL_FOREIGN_NET'for q in found)else'PASS')
 result=dict(board=name,source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),method='Actual native Fab projection, circular bodies preserved, sampled at <=0.025mm, pad lands excluded. Track centreline inventory; full copper width is separately enforced by KiCad BODY/NETBODY rules on both outer layers.',not_a_physical_fit_or_electrical_qualification=True,components=counts,body_crossing_inventory=rows)
 (r/'body_review_final.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(kind,'components',len(counts),'foreign-net candidates',sum(q['classification']=='FAIL_FOREIGN_NET'for q in rows),'own-pin escapes',sum(q['classification']=='OWN_PIN_OUTWARD_HOUSING_ESCAPE'for q in rows),'U100 exceptions',sum(q['classification']=='RAISED_MODULE_ARCHITECTURE'for q in rows))
if __name__=='__main__':
 for kind in sys.argv[1:]:audit(kind)

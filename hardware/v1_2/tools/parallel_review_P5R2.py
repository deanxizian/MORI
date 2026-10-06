"""Resolve copper-overlap duplicates missed by exact endpoint graphs."""
import pcbnew as k,math,sys
from review_edit_P5R2 import Edit,xy
e=Edit(sys.argv[1]);tried=set()
while True:
 ts=[t for t in e.b.GetTracks()if not isinstance(t,k.PCB_VIA)];candidates=[]
 for i,t in enumerate(ts):
  a,z=xy(t.GetStart()),xy(t.GetEnd());dx,dy=z[0]-a[0],z[1]-a[1];le=math.dist(a,z)
  if le<.1:continue
  for u in ts[:i]:
   if u.GetLayer()!=t.GetLayer()or u.GetNetname()!=t.GetNetname()or u.GetWidth()!=t.GetWidth():continue
   ua,uz=xy(u.GetStart()),xy(u.GetEnd());dx2,dy2=uz[0]-ua[0],uz[1]-ua[1];lu=math.dist(ua,uz)
   if lu<.1 or abs(dx*dy2-dy*dx2)/(le*lu)>.0001:continue
   sep=abs(dx*(ua[1]-a[1])-dy*(ua[0]-a[0]))/le
   pp=sorted(((v[0]-a[0])*dx+(v[1]-a[1])*dy)/le for v in[ua,uz]);overlap=min(le,pp[1])-max(0,pp[0])
   if sep<k.ToMM(t.GetWidth())-.001 and overlap>.1:
    for q in sorted([t,u],key=lambda q:q.GetLength()):
     uid=q.m_Uuid.AsString()
     if uid not in tried:candidates.append((-overlap,uid,q.GetNetname(),sep))
 if not candidates:break
 _,uid,net,sep=min(candidates);tried.add(uid);e.remove([uid]);e.commit('Offset parallel duplicate on '+net+'; retain same nominal width, native connectivity gate; offset %.6f mm'%sep)

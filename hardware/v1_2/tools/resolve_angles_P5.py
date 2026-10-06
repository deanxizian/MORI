"""Native-DRC-verified removal of acute overlap wedges at track junctions.

Retains widths and connectivity. Does not change corner/clearance rules.
Every tentative endpoint change is accepted or rolled back by KiCad DRC.
"""
import sys,json,math,subprocess,collections
import pcbnew as k
from layout_P5 import paths,xy,pt
from geometry_guard_P5 import Guard
kind=sys.argv[1];_,d,p,r=paths(kind);b=k.LoadBoard(str(p));cli='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli';accepted=r/'angles_accepted.kicad_pcb'
soft={'track_angle','track_not_centered_on_via','track_dangling','via_dangling','silk_over_copper','silk_overlap'}
def inspect():
 k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
 subprocess.run([cli,'pcb','drc','--severity-all','--all-track-errors','--refill-zones','--format','json','-o',str(r/'angle-drc.json'),str(p)],check=True,capture_output=True)
 return json.loads((r/'angle-drc.json').read_text())
def ac(j):return sum(q['type']=='track_angle' for q in j['violations'])
def safe(a,z):
 aa=collections.Counter(q['type'] for q in a['violations'] if q['type'] not in soft);zz=collections.Counter(q['type'] for q in z['violations'] if q['type'] not in soft)
 return len(a['unconnected_items'])<=len(z['unconnected_items']) and ac(a)<ac(z) and all(aa[x]<=zz[x] for x in aa)
def proj(v,a,z):
 dx,dy=z[0]-a[0],z[1]-a[1];dd=dx*dx+dy*dy
 if dd<1e-9:return a,0
 t=((v[0]-a[0])*dx+(v[1]-a[1])*dy)/dd
 return (a[0]+t*dx,a[1]+t*dy),t
cur=inspect();accepted.write_bytes(p.read_bytes());log=[];tried=set();attempts=0
while attempts<180:
 by={t.m_Uuid.AsString():t for t in b.GetTracks()};found=False
 pairs={tuple(sorted(q['uuid'] for q in row['items'])) for row in cur['violations'] if row['type']=='track_angle'}
 for ids in sorted(pairs):
  ts=[by.get(i) for i in ids]
  if len(ts)!=2 or any(t is None or isinstance(t,k.PCB_VIA) for t in ts):continue
  for moving,stem in [ts,ts[::-1]]:
   sa,sz=xy(stem.GetStart()),xy(stem.GetEnd());width=k.ToMM(moving.GetWidth());uid=moving.m_Uuid.AsString();net=moving.GetNetname()
   for start,near,far in [(True,xy(moving.GetStart()),xy(moving.GetEnd())),(False,xy(moving.GetEnd()),xy(moving.GetStart()))]:
    q,t=proj(near,sa,sz)
    if math.dist(near,q)>(width+k.ToMM(stem.GetWidth()))/2+.02 or not -.2<t<1.2:continue
    options=[]
    for e in [sa,sz]:
     if math.dist(near,e)<max(1.5,width+k.ToMM(stem.GetWidth())):options.append(e)
    pp,tt=proj(far,sa,sz)
    if 0<=tt<=1 and math.dist(near,pp)<4 and math.dist(far,pp)<=math.dist(far,near)+.02:options.append(pp)
    options.append(q)
    for new in options:
     new=tuple(round(x,6) for x in new);key=(uid,start,new)
     if key in tried or math.dist(near,new)<.005 or math.dist(far,new)<.08:continue
     tried.add(key)
     if not Guard(b,net).line_clear(far,new,moving.GetLayer(),width):continue
     # No longer local branch than necessary; broad load widths are retained.
     if math.dist(far,new)>math.dist(far,near)+1.5:continue
     (moving.SetStart if start else moving.SetEnd)(pt(*new));attempts+=1;nxt=inspect()
     if safe(nxt,cur):
      log.append(dict(uuid=uid,net=net,old=near,new=new,width_mm=width));cur=nxt;accepted.write_bytes(p.read_bytes());print(kind,'angles',ac(cur),'adjusted',net,flush=True)
      found=True
     else:
      p.write_bytes(accepted.read_bytes());b=k.LoadBoard(str(p))
     # Fresh SWIG objects after every native trial/rollback.
     found=found or 'RETRY';break
    if found:break
   if found:break
  if found:break
 if not found:break
cur=inspect();(r/'drc.json').write_text(json.dumps(cur,ensure_ascii=False,indent=2)+'\n')
(r/'junction_refinements.json').write_text(json.dumps(dict(attempts=attempts,changes=log),indent=2)+'\n')
print(kind,'junction trials',attempts,'accepted',len(log),'remaining angles',ac(cur),'unconnected',len(cur['unconnected_items']),flush=True)

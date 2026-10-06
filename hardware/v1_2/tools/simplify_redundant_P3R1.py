"""Remove redundant small signal copper only after native connectivity comparison.

Each deletion must leave the full pad partition of that net unchanged. This
removes obsolete overlaps left by local rerouting, not a critical/load loop.
Native ERC/DRC and body-route review still follow this editing aid.
"""
import sys,json
import pcbnew as k
from layout_P3R1 import paths,xy
kind=sys.argv[1];_,_,p,r=paths(kind);b=k.LoadBoard(str(p));report=json.loads((r/'drc.json').read_text())
critical={'/GND','/M5_FB','/C5_FB','/M5_SW','/C5_SW','/M5_BOOT','/C5_BOOT','/KELVIN_P','/KELVIN_N',
 '/BAT_MON','/BAT_REV','/BAT_IN','/W9','/W_PRE','/W_VM','/H6','/H_PRE','/H_VM','/M5_VIN','/C5_VIN','/+5V_MOTION','/+5V_CAM'}
angleids={q['uuid'] for v in report['violations'] if v['type']=='track_angle' for q in v['items']}
def partition(net,exclude=None):
 # Recompute copper shape connectivity; never reuse a mutable pcbnew cache.
 # Node identity joins the two layers of each plated pad or through via.
 objs=[q for f in b.GetFootprints() for q in f.Pads() if q.GetNetname()==net]
 pads={q.m_Uuid.AsString() for q in objs}
 objs += [q for q in b.GetTracks() if q.GetNetname()==net and q.m_Uuid.AsString()!=exclude]
 parent=list(range(len(objs)));shapes={}
 def root(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 for i,q in enumerate(objs):
  for l in [k.F_Cu,k.B_Cu]:
   if q.IsOnLayer(l):shapes[i,l]=q.GetEffectiveShape(l)
 for i,q in enumerate(objs):
  for j in range(i):
   if root(i)==root(j):continue
   for l in [k.F_Cu,k.B_Cu]:
    aa,zz=shapes.get((i,l)),shapes.get((j,l))
    if aa is not None and zz is not None and aa.BBox().Intersects(zz.BBox()) and aa.Collide(zz,0):
     parent[root(i)]=root(j);break
 groups={}
 for i,q in enumerate(objs):
  uid=q.m_Uuid.AsString()
  if uid in pads:groups.setdefault(root(i),[]).append(uid)
 return tuple(sorted(tuple(sorted(g)) for g in groups.values()))
choices=[]
for t in b.GetTracks():
 if isinstance(t,k.PCB_VIA) or t.GetNetname() in critical or k.ToMM(t.GetWidth())>.25:continue
 uid=t.m_Uuid.AsString()
 if uid in angleids or t.GetLength()<k.FromMM(.5):choices.append((uid not in angleids,k.ToMM(t.GetLength()),uid))
log=[]
for _,length,uid in sorted(choices):
 t=next((q for q in b.GetTracks() if q.m_Uuid.AsString()==uid),None)
 if t is None:continue
 net=t.GetNetname();before=partition(net);a,z=xy(t.GetStart()),xy(t.GetEnd())
 if partition(net,uid)==before:
  b.Delete(t);log.append(dict(uuid=uid,net=net,start=a,end=z,length_mm=length))
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
(r/'redundant_signal_copper_removed.json').write_text(json.dumps(log,indent=2)+'\n')
print(kind,'removed redundant signal segments',len(log),flush=True)

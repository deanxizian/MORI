"""Remove obsolete long fragments on selected signal nets, keeping local escapes.

Preserve copper within3mm of a terminal. Truncate a long pad-attached straight
segment to its2mm outward escape. This does not touch other nets or rules.
"""
import json,sys,math
import pcbnew as k
from layout_P3R1 import paths,xy,pt,F,B
kind=sys.argv[1];name,d,p,r=paths(kind);b=k.LoadBoard(str(p));nets={'/'+n.lstrip('/') for n in sys.argv[2:]};log=[]
pads={n:[xy(q.GetPosition()) for f in b.GetFootprints() for q in f.Pads() if q.GetNetname()==n] for n in nets}
for t in list(b.GetTracks()):
 net=t.GetNetname()
 if net not in nets:continue
 assert (isinstance(t,k.PCB_VIA) and k.ToMM(t.GetWidth(F))<=.8) or (not isinstance(t,k.PCB_VIA) and k.ToMM(t.GetWidth())<=.25),(net,'unexpected load copper')
 uid=t.m_Uuid.AsString();a,z=xy(t.GetStart()),xy(t.GetEnd());near=lambda v:min(math.dist(v,p) for p in pads[net]);da,dz=near(a),near(z)
 if max(da,dz)<=3:continue
 if not isinstance(t,k.PCB_VIA) and min(da,dz)<1.1 and max(da,dz)>3:
  if dz<da:a,z=z,a
  length=math.dist(a,z);v=(a[0]+2*(z[0]-a[0])/length,a[1]+2*(z[1]-a[1])/length);t.SetStart(pt(*a));t.SetEnd(pt(*v));action='trim'
 else:b.Delete(t);action='remove'
 log.append(dict(uuid=uid,net=net,old_start=a,old_end=z,action=action))
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);(r/'trunks_reset.json').write_text(json.dumps(log,indent=2)+'\n');print(kind,'reset fragments',len(log))

"""Trim native-reported dangling ends to actual same-net copper junctions."""
import pcbnew as k,json,sys,subprocess,math,collections
from helpers_P4 import paths
from layout_P3R1 import xy,pt
kind=sys.argv[1];_,d,p,r=paths(kind);b=k.LoadBoard(str(p));cli='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli';log=[]
def inspect():
 k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
 subprocess.run([cli,'pcb','drc','--severity-all','--all-track-errors','--refill-zones','--format','json','-o',str(r/'trim_drc.json'),str(p)],capture_output=True,check=True)
 return json.loads((r/'trim_drc.json').read_text())
cur=inspect();soft={'silk_over_copper','silk_overlap','silk_edge_clearance','track_angle','track_dangling','via_dangling','track_not_centered_on_via'}
for row in list(cur['violations']):
 if row['type']!='track_dangling':continue
 uid=row['items'][0]['uuid'];t=next((t for t in b.GetTracks() if t.m_Uuid.AsString()==uid),None)
 if t is None or t.Type()==k.PCB_VIA_T:continue
 a,z=xy(t.GetStart()),xy(t.GetEnd());dx,dy=z[0]-a[0],z[1]-a[1];dd=dx*dx+dy*dy;l=t.GetLayer();sh=t.GetEffectiveShape(l);anchors=[]
 def proj(q):return ((q[0]-a[0])*dx+(q[1]-a[1])*dy)/dd
 others=[q for f in b.GetFootprints() for q in f.Pads()]+list(b.GetTracks())
 for q in others:
  if q.m_Uuid.AsString()==uid or q.GetNetCode()!=t.GetNetCode() or not q.IsOnLayer(l):continue
  if not sh.Collide(q.GetEffectiveShape(l),0):continue
  if not isinstance(q,k.PCB_TRACK) or q.Type()==k.PCB_VIA_T:anchors.append(max(0,min(1,proj(xy(q.GetPosition())))));continue
  u,v=xy(q.GetStart()),xy(q.GetEnd());qx,qy=v[0]-u[0],v[1]-u[1];den=dx*qy-dy*qx
  if abs(den)>1e-8:
   tt=((u[0]-a[0])*qy-(u[1]-a[1])*qx)/den
   if -.03<=tt<=1.03:anchors.append(max(0,min(1,tt)))
  else:
   lo,hi=sorted([proj(u),proj(v)])
   if hi>=0 and lo<=1:anchors.extend([max(0,lo),min(1,hi)])
 if not anchors:continue
 lo,hi=min(anchors),max(anchors);backup=p.read_bytes();oldn=len(cur['unconnected_items']);info=dict(uuid=uid,net=t.GetNetname(),old=[a,z])
 if (hi-lo)*math.sqrt(dd)<.05:b.Delete(t);info['action']='remove_unneeded_stub'
 elif lo>.001 or hi<.999:
  aa=(a[0]+lo*dx,a[1]+lo*dy);zz=(a[0]+hi*dx,a[1]+hi*dy);t.SetStart(pt(*aa));t.SetEnd(pt(*zz));info.update(action='trim',new=[aa,zz])
 else:continue
 nxt=inspect();oldhard=collections.Counter(x['type'] for x in cur['violations'] if x['type'] not in soft);newhard=collections.Counter(x['type'] for x in nxt['violations'] if x['type'] not in soft)
 if len(nxt['unconnected_items'])<=oldn and all(newhard[c]<=oldhard[c] for c in newhard):cur=nxt;log.append(info);print(info,flush=True)
 else:p.write_bytes(backup);b=k.LoadBoard(str(p))
cur=inspect();(r/'drc.json').write_text(json.dumps(cur,ensure_ascii=False,indent=2)+'\n');(r/'trim_stubs.json').write_text(json.dumps(log,indent=2)+'\n')

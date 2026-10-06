"""Outward escapes from actual unconnected SMT pads, with native shape tests."""
import pcbnew as k,sys,json,itertools
from helpers_P4 import paths
from layout_P3R1 import track,via,xy,F,B
from geometry_guard_P3R1 import Guard
kind=sys.argv[1];_,d,p,r=paths(kind);b=k.LoadBoard(str(p));j=json.loads((r/'drc.json').read_text());pads={q.m_Uuid.AsString():q for f in b.GetFootprints() for q in f.Pads()};log=[]
uids={i['uuid'] for row in j['unconnected_items'] for i in row['items'] if i['uuid'] in pads}
for uid in uids:
 q=pads[uid]
 if q.GetAttribute()!=k.PAD_ATTRIB_SMD or q.GetNetname()=='/GND':continue
 # A connected via already supplies a real layer-change port for this cluster.
 c=k.CONNECTIVITY_DATA();c.Build(b);seen=set();queue=[q];hasvia=False
 while queue:
  x=queue.pop();uu=x.m_Uuid.AsString()
  if uu in seen:continue
  seen.add(uu)
  if x.Type()==k.PCB_VIA_T:hasvia=True;break
  queue.extend(c.GetConnectedTracks(x));queue.extend(c.GetConnectedPads(x))
 if hasvia:continue
 net=q.GetNetname();a=xy(q.GetPosition());layer=q.GetLayer();g=Guard(b,net);found=False
 for dist,z,ps in itertools.islice(g.portals(a,layer,radius=3,step=.1),8):
  if dist<.7:continue
  track(b,net,ps,.2,layer);via(b,net,*z,grid=False);log.append(dict(ref=q.GetParentFootprint().GetReference(),pin=q.GetNumber(),net=net,points=ps,via=z));print('PORT',log[-1],flush=True);found=True;break
 if not found:print('NO PORT',q.GetParentFootprint().GetReference(),q.GetNumber(),net,a,flush=True)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);(r/'actual_pad_ports.json').write_text(json.dumps(log,indent=2)+'\n')

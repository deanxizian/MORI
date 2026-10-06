"""Remove non-ground copper fragments that reach no component terminal.

This is native connectivity-based cleanup after ripping routes. Ground
stitching can connect zones without touching pads and is deliberately kept.
"""
import sys,json
import pcbnew as k
from layout_P3R1 import paths,xy
kind=sys.argv[1];name,d,p,r=paths(kind);b=k.LoadBoard(str(p));c=k.CONNECTIVITY_DATA();c.Build(b);alltracks={t.m_Uuid.AsString():t for t in b.GetTracks()};seen=set();delete=[];log=[]
for t in list(b.GetTracks()):
 if t.GetNetname()=='/GND' or t.m_Uuid.AsString() in seen:continue
 queue=[t];ids=set();pads=set()
 while queue:
  u=queue.pop();uid=u.m_Uuid.AsString()
  if uid in ids:continue
  ids.add(uid)
  for q in c.GetConnectedPads(u):pads.add(q.m_Uuid.AsString())
  queue.extend(q for q in c.GetConnectedTracks(u) if q.GetNetCode()==t.GetNetCode())
 seen|=ids
 if pads:continue
 for uid in ids:
  if uid in alltracks:delete.append(uid)
 log.append(dict(net=t.GetNetname(),no_component_terminals=True,removed_uuids=sorted(ids)))
for uid in set(delete):b.Delete(alltracks[uid])
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
(r/'orphan_copper_removed.json').write_text(json.dumps(log,ensure_ascii=False,indent=2)+'\n');print(kind,'orphan copper removed',len(set(delete)),flush=True)

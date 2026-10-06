"""Prune open copper fragments after rerouting, driven by real native DRC.

Only dangling tracks/vias and BODY keepout violations are removed. Pads,
netlist, rules, zones and closed connections are preserved. Reroute all
reported airwires before release.
"""
import sys,json,subprocess
import pcbnew as k
from layout_P3R1 import paths,xy
kind=sys.argv[1];name,d,p,r=paths(kind);cli='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli';log=[]
for iteration in range(18):
 subprocess.run([cli,'pcb','drc','--severity-all','--all-track-errors','--schematic-parity','--refill-zones','--format','json','-o',str(r/'drc.json'),str(p)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 j=json.loads((r/'drc.json').read_text());ids={i['uuid'] for v in j['violations'] if v['type'] in ['track_dangling','via_dangling','items_not_allowed'] for i in v['items']}
 if not ids:break
 b=k.LoadBoard(str(p));removed=[]
 blocked_nets=set()
 if '--closed-nets' in sys.argv:
  byid={q.m_Uuid.AsString():q.GetNetname() for f in b.GetFootprints() for q in f.Pads()}
  byid.update({q.m_Uuid.AsString():q.GetNetname() for q in b.GetTracks()})
  byid.update({q.m_Uuid.AsString():q.GetNetname() for q in b.Zones()})
  blocked_nets={byid[i['uuid']] for row in j['unconnected_items'] for i in row['items'] if i['uuid'] in byid}
 for t in list(b.GetTracks()):
  if t.m_Uuid.AsString() in ids and t.GetNetname() not in blocked_nets:
   removed.append(dict(uuid=t.m_Uuid.AsString(),net=t.GetNetname(),start=xy(t.GetStart()),end=xy(t.GetEnd())));b.Delete(t)
 if not removed:break
 k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);log.append(dict(iteration=iteration,removed=removed))
 print(kind,'pruned',iteration,len(removed),flush=True)
(r/'pruned_routes.json').write_text(json.dumps(log,ensure_ascii=False,indent=2)+'\n')

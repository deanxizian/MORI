"""Remove copper flagged by native DRC after a deliberate placement change."""
import json,sys
import pcbnew as k
from layout_P3R1 import paths,xy
kind=sys.argv[1];_,_,p,r=paths(kind);b=k.LoadBoard(str(p));j=json.loads((r/'drc.json').read_text());types={'clearance','shorting_items','hole_clearance','items_not_allowed','solder_mask_bridge'}
ids={i['uuid'] for row in j['violations'] if row['type'] in types for i in row['items']};removed=[]
for t in list(b.GetTracks()):
 if t.m_Uuid.AsString() in ids:
  removed.append(dict(uuid=t.m_Uuid.AsString(),net=t.GetNetname(),start=xy(t.GetStart()),end=xy(t.GetEnd())));b.Delete(t)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);(r/'placement_conflicts_removed.json').write_text(json.dumps(removed,indent=2)+'\n');print(kind,'displaced tracks/vias',len(removed))

"""Reject illegal P5 candidate segments; never waive a native violation."""
import json,sys
import pcbnew as k
from layout_P5 import paths,F,B
from close_routes_P2 import merge_lines,snap_via_ends

def run(kind):
    name,d,p,r=paths(kind);b=k.LoadBoard(str(p));removed=[]
    if (r/'drc.json').exists():
        report=json.loads((r/'drc.json').read_text());bad={i['uuid'] for v in report['violations'] if v['type']=='items_not_allowed' for i in v['items']}
        for t in list(b.GetTracks()):
            if t.m_Uuid.AsString() in bad:removed.append(dict(uuid=t.m_Uuid.AsString(),net=t.GetNetname()));b.Delete(t)
    # Importing a two-layer router session into the four-layer carrier may
    # mark outer-to-outer vias as blind/buried. The actual design uses PTH.
    for t in b.GetTracks():
        if isinstance(t,k.PCB_VIA):t.SetViaType(k.VIATYPE_THROUGH);t.SetLayerPair(F,B)
    merge_lines(b);snap_via_ends(b);k.SaveBoard(str(p),b)
    (r/'candidate_rejected_segments.json').write_text(json.dumps(removed,indent=2)+'\n')
    print(kind,'rejected candidate body crossings',len(removed),flush=True)
if __name__=='__main__':run(sys.argv[1])

"""Remove only native body-keepout violations in the working P3R1 board.

Retain the original track widths/coordinates in a log for repair. The file
remains a working draft until reconnection and fresh ERC/DRC succeed.
"""
import sys,json
import pcbnew as k
from layout_P3R1 import paths,xy
kind=sys.argv[1];name,d,p,r=paths(kind);b=k.LoadBoard(str(p));j=json.loads((r/'drc.json').read_text());ids={i['uuid'] for v in j['violations'] if v['type']=='items_not_allowed' for i in v['items']};log=[]
for t in list(b.GetTracks()):
    if t.m_Uuid.AsString() not in ids:continue
    isvia=isinstance(t,k.PCB_VIA)
    log.append(dict(uuid=t.m_Uuid.AsString(),net=t.GetNetname(),via=isvia,layer=b.GetLayerName(t.GetLayer()),start=xy(t.GetStart()),end=xy(t.GetEnd()),width=k.ToMM(t.GetWidth(k.F_Cu) if isvia else t.GetWidth())))
    b.Delete(t)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
old=json.loads((r/'removed_body_routes.json').read_text()) if (r/'removed_body_routes.json').exists() else []
(r/'removed_body_routes.json').write_text(json.dumps(old+log,ensure_ascii=False,indent=2)+'\n')
print(name,'removed native body violations',len(log),flush=True)

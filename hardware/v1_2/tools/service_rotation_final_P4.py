"""Rotate J6 at its original service bay; reject crowded top-row trial."""
import pcbnew as k,json,math
from helpers_P4 import paths
from layout_P3R1 import setplace,xy,F,B
from body_keepouts_P3R1 import create
from route_local_P4 import connect
_,d,p,r=paths('power');b=k.LoadBoard(str(p));k.SaveBoard(str(r/'rejected_service_top_row.kicad_pcb'),b)
original=k.LoadBoard(str(r/'before_service_connector_move.kicad_pcb'))
old=k.LoadBoard(str(r/'before_master_load_routes.kicad_pcb'));oldids={t.m_Uuid.AsString() for t in old.GetTracks()}
for t in list(b.GetTracks()):
 if t.m_Uuid.AsString()=='f3479535-e574-4355-b541-bafa0e1edd44' or t.GetNetname()=='/W9_IN' or (t.GetNetname()=='/BAT_MON' and t.m_Uuid.AsString() not in oldids):b.Delete(t)
for t in original.GetTracks():
 if t.GetNetname()=='/W9_IN':b.Add(t.Duplicate())
f=next(f for f in b.GetFootprints() if f.GetReference()=='J6');setplace(f,45,51,180,'F');create(b)
ts=[t for t in b.GetTracks() if t.GetNetname()=='/BAT_MON' and t.Type()!=k.PCB_VIA_T and k.ToMM(t.GetWidth())>=1.99]
ends=sorted({(xy(t.GetStart()),t.GetLayer()) for t in ts}|{(xy(t.GetEnd()),t.GetLayer()) for t in ts},key=lambda x:math.dist((40,51),x[0]))
log=[]
for z,l in ends[:5]:
 try:
  result=connect(b,'/BAT_MON',(40,51),z,[F,B],[l],(80,55),step=.1,width=2,vd=1,dr=.45,max_nodes=450000,time_limit=30);log.append(result);break
 except RuntimeError as e:print(e,flush=True)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);(r/'service_rotation_final.json').write_text(json.dumps(dict(final=[45,51,180],rejected=[48,7,0],reason='Top-row trial displaced wheel supply. Rotate original service location so BAT_MON faces the main bus instead of the comparator bay.',route=log),indent=2)+'\n')

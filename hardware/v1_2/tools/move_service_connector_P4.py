"""Move optional raw-battery service J6 beside power inputs, preserving pins.

This removes an unnecessary long 2mm branch through the comparator bay.
"""
import pcbnew as k,json
from helpers_P4 import paths
from layout_P3R1 import setplace,track,F,B
from body_keepouts_P3R1 import create
from geometry_guard_P3R1 import Guard
from route_local_P4 import connect
_,d,p,r=paths('power');b=k.LoadBoard(str(p));k.SaveBoard(str(r/'before_service_connector_move.kicad_pcb'),b)
old=k.LoadBoard(str(r/'before_master_load_routes.kicad_pcb'));oldids={t.m_Uuid.AsString() for t in old.GetTracks()};removed=[]
for t in list(b.GetTracks()):
 if t.GetNetname()=='/BAT_MON' and t.m_Uuid.AsString() not in oldids:removed.append(t.m_Uuid.AsString());b.Delete(t)
f=next(f for f in b.GetFootprints() if f.GetReference()=='J6');setplace(f,48,7,0,'F');create(b)
ps=[(53,7),(53,9.5),(52.5,10),(28.5,10),(28,9.5),(28,7)]
if all(Guard(b,'/BAT_MON').line_clear(a,z,B,2) for a,z in zip(ps,ps[1:])):track(b,'/BAT_MON',ps,2,B);print('direct2mm BAT service path added')
else:
 try:connect(b,'/BAT_MON',(53,7),(28,7),[F,B],[F,B],(80,55),step=.05,width=2,vd=1,dr=.45,max_nodes=600000,time_limit=45)
 except RuntimeError as e:print(e)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);(r/'service_connector_move.json').write_text(json.dumps(dict(J6_before=[40,51,0],J6_after=[48,7,0],reason='Keep the optional raw-battery service branch in the power-input bay; remove the long wide crossing of head analogue signals',removed_old_branch=removed,pin_assignment_unchanged=True),indent=2)+'\n')

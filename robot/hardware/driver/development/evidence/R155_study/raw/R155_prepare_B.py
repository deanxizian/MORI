"""Joint OV and bypass orientation candidate; original supply still must be restored."""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
plan=json.loads((b/'R155A-plan.json').read_text());assert c.sha==plan['board_sha256']
plan.update(revision='R155B',scope=__doc__)
plan['translations']=[{'reference':'C1303','from_mm':[42.9,23.5],'delta_mm':[0,0],'rotation_deg':270},{'reference':'R802','from_mm':[40.6,23.9],'delta_mm':[-.1,0]}]
for id_ in ['57330cbe-4127-4b66-8cbc-91bd347df963','68337903-98f5-4e4f-9ed8-5117238ed520','e6b35010-fab4-43b6-998f-221ea3ad499d']:
 t=c.by_id[id_];plan['delete_copper'].append(id_)
 plan['deleted_copper_expected'][id_]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
plan['routes'] += [
 {'net':'Net-(U1301-INB-_{slash}_OV)','layer':'In2.Cu','width_mm':.2,'points_mm':[[57.275,19.0],[50.8,19.0],[45.4,24.4],[41.1,24.4],[40.6,24.9]]},
 {'net':'MOTION_3V3','layer':'B.Cu','width_mm':.2,'points_mm':[[42.9,22.725],[42.1,22.725],[42.1,24.85],[42.5,25.25],[42.5,25.6]]}
]
p=b/'R155B-plan.json';assert not p.exists();p.write_text(json.dumps(plan,indent=2)+'\n')
print(json.dumps({'revision':plan['revision'],'source':c.sha,'partial':True}))

"""Joint UV/OV escape using the existing lower UV transfer and a local R801 move.

Keep C1301/R1021 at the accepted source positions. Restore the UV input and
divider explicitly through the original upper UV hole. The OV remote connection
remains pending. All ground/supply vias and electrical pin functions are retained.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='65ab9844163d4c7e081471e7a877000ebdfe5d17125324ddd78c0050e63ceede'
uv='Net-(U1301-INA+_{slash}_UV)';ov='Net-(U1301-INB-_{slash}_OV)';en='Net-(U801-EN{slash}UVLO)';supply='/06 {slash} CAM_Buck/UPS_5V'
ids=['28b957b9-08fa-4418-bb55-9f64c132f18b','701710e2-fbf7-4e5e-b5cc-5f0bb012b2e5','2749cb7f-3537-4d2f-9d97-c055dada4198','829970f2-c2e5-49dc-9a0a-f5332c139165','d14a85c3-7a69-4ceb-924e-cfe1772934b7','1bd1ae8f-eb6b-4499-b44c-123ca84ea1d2','f6fe6085-a811-4489-9526-b02a625e8eb6','266c3e5c-3fb1-4f46-bc20-cae4ac685a04']
snap={}
for id_ in ids:
 t=c.by_id[id_];snap[id_]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
via='45a1d39e-cb5b-4ef8-b13d-fe20aed2dfaf'
p={'revision':'R156C','board_sha256':c.sha,'scope':__doc__,
 'translations':[{'reference':'R801','from_mm':[39.5,26.5],'delta_mm':[-.4,0]}],
 'delete_copper':ids,'deleted_copper_expected':snap,
 'reassign_vias':[{'uuid':via,'source_expected':via_snapshot(c.board,c.by_id[via]),'net':ov,'reason':'Reuse the lower original UV hole for OV; UV restored through the unchanged upper hole and explicit replacement traces.'}],
 'routes':[
  {'net':en,'layer':'B.Cu','width_mm':.2,'points_mm':[[39,24.8],[39.1,24.9],[39.1,25.675]]},
  {'net':supply,'layer':'B.Cu','width_mm':.2,'points_mm':[[39.1,27.325],[39.1,28.4],[39,28.5]]},
  {'net':uv,'layer':'B.Cu','width_mm':.2,'points_mm':[[40.75,26.8],[40.75,27.4],[41.55,28.2375]]},
  {'net':uv,'layer':'In3.Cu','width_mm':.2,'points_mm':[[40.75,26.8],[43.45,28.6375]]},
  {'net':ov,'layer':'B.Cu','width_mm':.2,'points_mm':[[41.55,25.9625],[39.95,25.9625],[39.95,27.8375],[40.75,28.6375]]}],
 'vias':[],'adoption_prohibited_until_complete_verification':True}
f=b/'R156C-plan.json';assert not f.exists();f.write_text(json.dumps(p,indent=2)+'\n');print(json.dumps({'revision':'R156C','source':c.sha}))

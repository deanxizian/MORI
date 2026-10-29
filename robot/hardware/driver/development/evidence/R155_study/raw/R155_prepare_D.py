"""Reuse the upper UV transfer for OV; explicitly restore the UV capacitor branch.

Independent native candidate only. No power feed or ground via is reassigned.
The remote OV branch remains to be connected and fully screened.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials')
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='65ab9844163d4c7e081471e7a877000ebdfe5d17125324ddd78c0050e63ceede'
ov='Net-(U1301-INB-_{slash}_OV)';uv='Net-(U1301-INA+_{slash}_UV)'
ids=['78b0e0dc-5356-4cc3-b969-d2dde38b0526','d14a85c3-7a69-4ceb-924e-cfe1772934b7']
snapshots={}
for id_ in ids:
 t=c.by_id[id_]
 snapshots[id_]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
via='fc152bf4-fbba-444c-ae12-f971486b6063'
plan={'revision':'R155D','board_sha256':c.sha,'scope':__doc__,'translations':[],
 'delete_copper':ids,'deleted_copper_expected':snapshots,
 'reassign_vias':[{'uuid':via,'source_expected':via_snapshot(c.board,c.by_id[via]),'net':ov,'reason':'Repurpose the upper UV transfer for short outward OV escape; restore the UV capacitor to the unchanged lower UV transfer explicitly.'}],
 'routes':[
  {'net':ov,'layer':'B.Cu','width_mm':.2,'points_mm':[[41.55,25.9625],[40.75,26.8]]},
  {'net':uv,'layer':'F.Cu','width_mm':.2,'points_mm':[[40.75,25.85],[39.6,25.85],[39.1,26.35],[39.1,28.1375],[39.6,28.6375],[40.75,28.6375]]}],
 'vias':[],'adoption_prohibited_until_complete_verification':True}
p=b/'R155D-plan.json';assert not p.exists();p.write_text(json.dumps(plan,indent=2)+'\n')
print(json.dumps({'revision':'R155D','source':c.sha}))

"""Independent partial OV escape study; supply restoration is mandatory before adoption."""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials')
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='65ab9844163d4c7e081471e7a877000ebdfe5d17125324ddd78c0050e63ceede'
net='Net-(U1301-INB-_{slash}_OV)'
id_='2233b7b0-a172-414b-b05b-4bb9a08a453e';t=c.by_id[id_]
snapshot={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
via='a9324169-c8ab-4683-a35c-6b1360e838b3'
plan={'revision':'R155A','board_sha256':c.sha,'scope':__doc__,'translations':[],
 'delete_copper':[id_],'deleted_copper_expected':{id_:snapshot},
 'reassign_vias':[{'uuid':via,'source_expected':via_snapshot(c.board,c.by_id[via]),'net':net,'reason':'Independent joint-routing study reuses the existing physical hole for OV escape. The detached U1301/C1303 supply must be restored explicitly before any adoption.'}],
 'routes':[{'net':net,'layer':'B.Cu','width_mm':.2,'points_mm':[[40.6,24.9],[41.55,25.85]]}],
 'vias':[],'adoption_prohibited_until_supply_restored':True}
p=b/'R155A-plan.json';assert not p.exists();p.write_text(json.dumps(plan,indent=2)+'\n')
print(json.dumps({'source':c.sha,'revision':'R155A','scope':'partial proposal only'}))

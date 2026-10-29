"""Independent R1702 orientation comparison before routing its wheel-supply sense tap.

Reverse R1702 in place; replace only the two old middle-node traces with an
outward lower escape to R1703. No new supply connection or manufacturing claim.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='65ab9844163d4c7e081471e7a877000ebdfe5d17125324ddd78c0050e63ceede'
ids=['a9295a25-0725-4f1f-ae2c-8822b258bcec','673dca86-7975-4381-ac89-1e83cd82b8e5'];snap={}
for id_ in ids:
 t=c.by_id[id_];snap[id_]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
p={'revision':'R156D','board_sha256':c.sha,'scope':__doc__,
 'translations':[{'reference':'R1702','from_mm':[48,8.5],'delta_mm':[0,0],'rotation_deg':0}],
 'delete_copper':ids,'deleted_copper_expected':snap,
 'routes':[{'net':'Net-(R1702-~-Pad2)','layer':'F.Cu','width_mm':.2,'points_mm':[[48.825,8.5],[48.825,8.8],[47.675,9.95],[47.675,10.4]]}],
 'vias':[],'adoption_prohibited_until_complete_verification':True}
f=b/'R156D-plan.json';assert not f.exists();f.write_text(json.dumps(p,indent=2)+'\n');print(json.dumps({'revision':'R156D','source':c.sha}))

"""Independent R1702/R1703 orientation and placement study for a direct WHEEL_VM sense tap.

Rotate R1702 in place and translate R1703 +0.70 mm in X. Test whether the six
existing 3V3 outer inter-via traces can be removed while the unchanged internal
supply plane preserves every old power-width connection. A lost supply path
rejects this trial; no assumption of redundant copper is accepted without audit.
All original supply and ground vias remain fixed. The new 0.20 mm wheel trace
serves only the 100k divider input, never the actuator load path.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='65ab9844163d4c7e081471e7a877000ebdfe5d17125324ddd78c0050e63ceede'
ids=['a9295a25-0725-4f1f-ae2c-8822b258bcec','673dca86-7975-4381-ac89-1e83cd82b8e5',
'024d6a70-848a-4969-83e4-45865d0a3457','2db4eae1-faa1-4fbd-a6ea-c8c0dd10a604','4354b546-77eb-4f1f-9d4f-754217d4aa28','534eb35f-7ec9-4596-a5dc-de664b28013c','c5637398-0770-4b52-b46a-89e809a40b90','df88716c-16bd-4e44-b2cd-35321f29a61c',
'46b45438-08f9-40a3-97c0-eeccfd4d2b5b','7902a7c8-41c9-4332-8075-aa6ca33ea4b0','8dad5387-a5b7-441f-bacd-b9126b5f49c2']
snap={}
for id_ in ids:
 t=c.by_id[id_];snap[id_]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
p={'revision':'R156E','board_sha256':c.sha,'scope':__doc__,
 'translations':[{'reference':'R1702','from_mm':[48,8.5],'delta_mm':[0,0],'rotation_deg':0},{'reference':'R1703','from_mm':[48.5,10.4],'delta_mm':[.7,0]}],
 'delete_copper':ids,'deleted_copper_expected':snap,
 'routes':[
 {'net':'Net-(R1702-~-Pad2)','layer':'F.Cu','width_mm':.2,'points_mm':[[48.825,8.5],[48.825,8.8],[48.375,9.25],[48.375,10.4]]},
 {'net':'Net-(U1702-INA+)','layer':'F.Cu','width_mm':.2,'points_mm':[[50.025,10.4],[50.025,12.1],[50.375,12.45],[58.9375,12.45]]},
 {'net':'/WHEEL_VM','layer':'F.Cu','width_mm':.2,'points_mm':[[47.175,8.5],[47.175,8.8],[47.4,9.025],[47.4,10.9],[46.9,11.4],[46.9,12.7],[46.355,13.245],[46.355,15.5]]}],
 'vias':[],'adoption_prohibited_until_complete_verification':True}
f=b/'R156E-plan.json';assert not f.exists();f.write_text(json.dumps(p,indent=2)+'\n');print(json.dumps({'revision':'R156E','source':c.sha}))

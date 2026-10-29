"""Joint refinement: move R1022 up, restore 0.2-mm supply-corridor regression,
and remove the two ADC offsets made unnecessary by relocating U303.
All changes remain in an independent trial; preserve native constraints.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R143D-plan.json';assert not out.exists()
c=Copper(str(b/'R143C/MORI_Interface_C3.kicad_pcb'));assert c.sha=='bdc62f0f151cc1755157e20c8b9d8762fccbced28638c81d5376e2817653362e'
p={'revision':'R143D','board_sha256':c.sha,'purpose':__doc__,'translations':[{'reference':'R1022','from_mm':[41,17.6],'delta_mm':[0,-2],'rotation_deg':270}],'delete_copper':[],'deleted_copper_expected':{},'routes':[]}
ids={'011b9455-65d7-5fc9-9a0d-f757684af61c','6a9971ea-9e51-5351-820c-527cacd81391','7fb2d1e6-436a-50cd-9bf0-bb8314a40391','b0ded6b1-445c-52e0-9523-365d1a854c44','bebcdfb8-cc7c-5718-8536-c45b5185d222','cc6c7b2b-921a-43bb-80ea-13d571df12ba','6bdb7300-db2f-542d-bafa-72b3a1339c95'}
for t in c.segments:
 if t.GetLayer()==pcb.B_Cu and t.GetNetname()=='MOTION_3V3' and {xy(t.GetStart()),xy(t.GetEnd())}=={(22.5,13.7),(23.425,13.7)}:ids.add(uid(t))
assert len(ids)==8
for u in sorted(ids):
 t=c.by_id[u];p['delete_copper'].append(u);p['deleted_copper_expected'][u]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
p['routes']=[{'net':'MOTION_3V3','layer':'B.Cu','width_mm':.2,'points_mm':[[22.5,11.4],[22.5,12.4]]},{'net':'MOTION_3V3','layer':'B.Cu','width_mm':.3,'points_mm':[[21.9375,12.4],[22.5,12.4],[22.5,13.7],[23.425,13.7]]},{'net':'/01 {slash} Core/ACT_CURRENT_ADC','layer':'B.Cu','width_mm':.2,'points_mm':[[26.05,11.75],[27.775,13.475]]}]
out.write_text(json.dumps(p,indent=2)+'\n')

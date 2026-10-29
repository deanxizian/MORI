"""Native joint gate/clamp candidate: move capacitor away from MOSFETs and rotate RC resistor."""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R147C-plan.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');p=json.loads((b/'R147B-plan.json').read_text());assert c.sha==p['board_sha256']
p['revision']='R147C';p['scope']=__doc__+' Exact old-net/reference/power checks and local visual review required. Not adopted.'
p['translations']=[{'reference':'C1602','from_mm':[37.95,13.6],'delta_mm':[0,1.35]},{'reference':'R1601','from_mm':[38.6,16.9],'delta_mm':[2.4,.9],'rotation_deg':90,'reconstruct_fixed_via_guards':True,'rotate_fixed_via_guards':True}]
for u in ['cac15144-e39c-4bf1-9030-15cea6f2676f','ef9c2aea-66e3-4f01-99d5-44b9d4b34e9b','14cff36b-d279-4c1e-9bec-a37922be9d9f','b1d640d5-8d49-40f4-af6f-269b615a4d90']:
 p['delete_copper'].remove(u);p['deleted_copper_expected'].pop(u)
p.pop('remove_obsolete_vias')
gate='/16 {slash} Actuator_Direct_Switch/ACT_GATE';p['vias']=[{'net':gate,'position_mm':[37.55,12.8525],'diameter_mm':.5,'drill_mm':.3}]
p['routes']=[]
def route(n,l,w,pts):p['routes'].append({'net':n,'layer':l,'width_mm':w,'points_mm':pts})
route('/UPS_BAT','B.Cu',.3,[[39.15,13],[38.8,13],[38.5,13.3],[38.5,14],[37.95,14]])
route('Net-(U1601-VCAP)','B.Cu',.25,[[37.95,15.9],[37.95,16.5],[37.65,16.8],[37.65,17.575]])
route(gate,'F.Cu',.3,[[38.2475,12.155],[37.55,12.8525],[37.825,13.1275],[37.825,13.95]])
route(gate,'B.Cu',.3,[[37.55,12.8525],[37.1,12.8525],[36.85,13.1025],[36.85,15.25],[36.55,15.55]])
route(gate,'B.Cu',.2,[[39.215,16.9],[39.215,18.865],[39.7,19.35],[40.275,19.35],[41,18.625]])
route('Net-(C1603-~-Pad1)','B.Cu',.2,[[41,16.975],[41.45,16.975],[41.8,17.325],[41.8,19.05],[40.55,20.3],[39.75,20.3]])
route('Net-(D1001-K)','B.Cu',.2,[[33.5,13.2125],[33.5,13.25],[35,14.75],[35.75,14.75],[36.35,14.15],[36.35,11.55],[36.8,11.1],[36.8,8.2125],[37.1,7.9125]])
out.write_text(json.dumps(p,indent=2)+'\n');print(str(out))

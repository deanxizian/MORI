"""Short RC orientation with a separately screened upper gate transfer; all limits retained."""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R147F-plan.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');p=json.loads((b/'R147E-plan.json').read_text());assert c.sha==p['board_sha256']
p['revision']='R147F';p['scope']=__doc__+' Diagnostic candidate, not adopted.'
p['translations']=[{'reference':'C1602','from_mm':[37.95,13.6],'delta_mm':[0,1.35]},{'reference':'R1601','from_mm':[38.6,16.9],'delta_mm':[2.4,0],'reconstruct_fixed_via_guards':True},{'reference':'R1707','from_mm':[42.5,13.35],'delta_mm':[.7,-.25]},{'reference':'R1701','from_mm':[43.1,11.1],'delta_mm':[0,-.25]}]
for u in ['42fba56b-5660-40dc-a131-b5b7c7ba7de9','602bbb37-73f7-4253-a739-c94909b08300','13b9809a-76d2-4d11-8d4a-22b56df86cfe','c9e8726b-0fb9-4a80-8f6a-fa55ee3bebf3']:
 p['delete_copper'].append(u);t=c.by_id[u];p['deleted_copper_expected'][u]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
gate='/16 {slash} Actuator_Direct_Switch/ACT_GATE'
p['vias'].append({'net':gate,'position_mm':[41.35,13.4],'diameter_mm':.5,'drill_mm':.3})
p['routes']=[r for r in p['routes'] if r['net'] not in [gate,'Net-(C1603-~-Pad1)']]
def route(n,l,w,pts):p['routes'].append({'net':n,'layer':l,'width_mm':w,'points_mm':pts})
route(gate,'F.Cu',.3,[[38.2475,12.155],[37.85,12.155],[37.55,12.455],[37.55,12.8525],[37.825,13.1275],[37.825,13.95]])
route(gate,'B.Cu',.3,[[37.55,12.8525],[37.1,12.8525],[36.85,13.1025],[36.85,15.25],[36.55,15.55]])
route(gate,'B.Cu',.2,[[41.35,13.4],[41,13.75],[41,16.075]])
route(gate,'In3.Cu',.2,[[39.215,16.9],[40.25,15.865],[40.25,14.5],[41.35,13.4]])
route('Net-(C1603-~-Pad1)','B.Cu',.2,[[41,17.725],[41,19.25],[40.35,19.9],[39.75,19.9],[39.75,20.3]])
route('/WHEEL_VM','B.Cu',.2,[[42.375,13.1],[42.375,14.025],[42.55,14.2]])
route('Net-(U1701-IN-)','B.Cu',.2,[[44.025,13.1],[44.275,12.85],[45.05,12.85]])
out.write_text(json.dumps(p,indent=2)+'\n');print(str(out))

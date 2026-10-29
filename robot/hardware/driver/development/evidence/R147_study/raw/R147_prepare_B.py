"""Joint capacitor/RC layout away from MOSFET heat; explicit adjacent sense-tail restoration."""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R147B-plan.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');p=json.loads((b/'R147A-plan.json').read_text());assert c.sha==p['board_sha256']
p['revision']='R147B';p['scope']=__doc__+' D1001 K B tail intentionally open pending reference-safe rerouting. Not adopted.'
p['translations']=[{'reference':'C1602','from_mm':[37.95,13.6],'delta_mm':[0,1.35]},{'reference':'R1601','from_mm':[38.6,16.9],'delta_mm':[2.7,.9],'reconstruct_fixed_via_guards':True},{'reference':'R1103','from_mm':[42.6,18.6],'delta_mm':[.3,0]}]
for s in p['translations']:
 if any(z.GetIsRuleArea() and z.GetZoneName().startswith('BODY_'+s['reference']+'_') and '_VIA_' in z.GetZoneName() for z in c.board.Zones()):s['reconstruct_fixed_via_guards']=True
p['delete_copper'].remove('1614f6f7-b337-4071-917f-04e2ce3befdc')
p['delete_copper']+=['5690508f-7ac0-4f7e-9084-7aae1b32560d','599ef9e6-2274-4c92-aed6-b9bffc4a3365','60181a7e-cff0-4d33-bd2c-68687b1a589c','8732ae58-53a6-4615-9655-125a06db4c8f','3db54abc-0af7-46b4-92b9-14094c693db8','01c2633c-f74e-414c-ba53-4503b6f4a80e','cac15144-e39c-4bf1-9030-15cea6f2676f','ef9c2aea-66e3-4f01-99d5-44b9d4b34e9b','14cff36b-d279-4c1e-9bec-a37922be9d9f','b1d640d5-8d49-40f4-af6f-269b615a4d90']
p['deleted_copper_expected']={}
for u in p['delete_copper']:
 t=c.by_id[u];p['deleted_copper_expected'][u]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
p.pop('move_vias',None)
u='10bdeb96-94ec-4dc6-beec-853f3cc22737';p['remove_obsolete_vias']=[{'uuid':u,'source_expected':via_snapshot(c.board,c.by_id[u]),'remaining_contact_layers':['In3.Cu'],'reason':'Old resistor B tail removed; restore gate RC branch via the explicit new transfer at 40.6,17.8.'}]
gate='/16 {slash} Actuator_Direct_Switch/ACT_GATE'
p['vias']=[{'net':gate,'position_mm':q,'diameter_mm':.5,'drill_mm':.3} for q in [[37.825,12.95],[40.6,17.8]]]
p['routes']=[]
def route(n,l,w,pts):p['routes'].append({'net':n,'layer':l,'width_mm':w,'points_mm':pts})
route('/UPS_BAT','B.Cu',.3,[[39.15,13],[38.65,13],[38.3,13.35],[38.3,14],[37.95,14]])
route('Net-(U1601-VCAP)','B.Cu',.25,[[37.95,15.9],[37.95,16.5],[37.65,16.8],[37.65,17.575]])
route(gate,'F.Cu',.3,[[38.2475,12.155],[38.2475,12.5275],[37.825,12.95],[37.825,13.95]])
route(gate,'B.Cu',.3,[[37.825,12.95],[37.15,12.95],[36.85,13.25],[36.85,15.25],[36.55,15.55]])
route(gate,'B.Cu',.2,[[41.3,16.975],[40.95,16.975],[40.6,17.325],[40.6,17.8]])
route(gate,'In3.Cu',.2,[[39.215,16.9],[39.215,17.2],[39.815,17.8],[40.6,17.8]])
route('Net-(C1603-~-Pad1)','B.Cu',.2,[[41.3,18.625],[41.3,19],[40,20.3],[39.75,20.3]])
route('/ACT_BAT_SWITCHED','B.Cu',.2,[[41.95,16.15],[42.2,16.4],[42.2,17.075],[42.9,17.775]])
route('Net-(U1101-IN+)','B.Cu',.2,[[42.9,19.425],[42.9,20.8],[43.0875,20.9875]])
out.write_text(json.dumps(p,indent=2)+'\n');print(str(out))

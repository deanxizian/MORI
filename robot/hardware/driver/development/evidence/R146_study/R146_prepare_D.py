"""Native diagnostic layout only; leaves power restoration for explicit routing."""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R146D-plan.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
p=json.loads((b/'R146C-plan.json').read_text());assert c.sha==p['board_sha256']
p['revision']='R146D';p['scope']=__doc__+' Not adopted; Q1602 remains open.'
p['removed_branch_reason']='Explicit diagnostic replacement of conflicting gate/power/adjacent signal tails. Both UPS_BAT and MOTION_5V must be restored and every original power/ground/reference connection checked before adoption.'
p['translations'][2]['delta_mm']=[.05,.425]
p['translations'].append({'reference':'D301','from_mm':[33.075,14.9],'delta_mm':[-.45,0]})
remove=p['delete_copper']+['5690508f-7ac0-4f7e-9084-7aae1b32560d','599ef9e6-2274-4c92-aed6-b9bffc4a3365','60181a7e-cff0-4d33-bd2c-68687b1a589c']
assert len(set(remove))==len(remove)
p['delete_copper']=remove;p['deleted_copper_expected']={}
for u in remove:
 t=c.by_id[u];p['deleted_copper_expected'][u]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
p['move_vias']=[{'uuid':'10bdeb96-94ec-4dc6-beec-853f3cc22737','source_expected':via_snapshot(c.board,c.by_id['10bdeb96-94ec-4dc6-beec-853f3cc22737']),'position_mm':[39.3,17.325],'reason':'Restore the shifted gate resistor B/In3 connections with native pad clearance.'}]
u='c9ef7bb5-bef9-48b7-b4cf-23501fe0a859'
p['remove_obsolete_vias']=[{'uuid':u,'source_expected':via_snapshot(c.board,c.by_id[u]),'remaining_contact_layers':['In2.Cu'],'reason':'The only B tail was explicitly deleted; restore the two 5 V regions through their existing 44.5,6.4 and 43.55,17.4 transfers before adoption.'}]
gate='/16 {slash} Actuator_Direct_Switch/ACT_GATE';src='/16 {slash} Actuator_Direct_Switch/ACT_FET_SOURCE'
p['vias']=[{'net':gate,'position_mm':[38.05,12.2],'diameter_mm':.5,'drill_mm':.3}]
p['routes']=[]
def route(n,l,w,pts):p['routes'].append({'net':n,'layer':l,'width_mm':w,'points_mm':pts})
for y in [8.345,9.615,10.885]:route(src,'F.Cu',.6,[[38.2475,y],[38.8975,y]])
route('/UPS_BAT','B.Cu',.3,[[39.15,13],[38.97,13.18],[37.95,13.18]])
route(gate,'B.Cu',.2,[[38.65,16.5],[39,16.5],[39.3,16.8],[39.3,17.325]])
route(gate,'In3.Cu',.2,[[38.715,16.4],[39.3,16.985],[39.3,17.325]])
route('Net-(C1603-~-Pad1)','B.Cu',.2,[[38.65,18.15],[39.1,18.6],[39.1,20.3]])
route(gate,'F.Cu',.3,[[37.825,13.95],[37.825,13.3],[38.05,13.075],[38.05,12.2]])
route(gate,'F.Cu',.3,[[38.05,12.2],[38.095,12.155],[38.8975,12.155]])
route(gate,'B.Cu',.3,[[38.05,12.2],[37.1,12.2],[36.85,12.45],[36.85,15.25],[36.55,15.55]])
route('Net-(D1001-K)','B.Cu',.2,[[36.8,8.2125],[36.8,11.1],[36.35,11.55],[36.35,14.4],[36.05,14.7],[34.5,14.7],[33.5,13.7],[33.5,13.2125]])
sense=c.by_id['e4b67b22-d32a-459b-8b55-989fcafd816c'].GetNetname()
route(sense,'F.Cu',.2,[[40.815,7.5],[45.6,7.5],[46.1,8],[46.1,8.85],[45.6,9.35]])
out.write_text(json.dumps(p,indent=2)+'\n');print(str(out))

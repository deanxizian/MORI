"""Prepare a joint actuator gate proposal against the exact R145I source."""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R146A-plan.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='1d32097f2b72c2add4d9a2fd68a2c4ed088b23cbf7606aa1ae3256cc5e48330c'
gate='/16 {slash} Actuator_Direct_Switch/ACT_GATE';src='/16 {slash} Actuator_Direct_Switch/ACT_FET_SOURCE'
remove=['4e3f344e-4464-4105-b162-6d7b012691cc','6eb245da-0958-40df-ae5f-1da41bcda21f','e50977e0-da61-4216-b09b-ff70e6bb72f8',
 '5081ae9b-2f88-480b-9119-e414c71a573b','84e73931-da8a-48b0-9a6d-bd6779d3010c',
 '046ef9c1-a549-4110-bc97-797625e6aabf','cf574466-c886-4f23-8190-6cea0c215513','ed3ea5a9-9b69-4ba6-b3db-df6ca2c391a7','1614f6f7-b337-4071-917f-04e2ce3befdc']
snap={}
for u in remove:
 t=c.by_id[u];snap[u]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
routes=[]
def route(net,ly,w,points):routes.append({'net':net,'layer':ly,'width_mm':w,'points_mm':points})
for y in [8.345,9.615,10.885]:route(src,'F.Cu',.6,[[38.2475,y],[38.8975,y]])
route('/UPS_BAT','B.Cu',.3,[[39.15,13],[38.97,13.18],[37.95,13.18]])
route(gate,'B.Cu',.2,[[38.45,16.275],[38.915,16.275],[39.215,16.575],[39.215,17.1]])
route(gate,'In3.Cu',.2,[[38.715,16.4],[39.215,16.9],[39.215,17.1]])
route(gate,'F.Cu',.3,[[37.825,13.95],[37.825,13.45],[38.05,13.225],[38.05,12.2]])
route(gate,'F.Cu',.3,[[38.05,12.2],[38.095,12.155],[38.8975,12.155]])
route(gate,'F.Cu',.3,[[36.2525,8.345],[36.2525,7.5025],[36.15,7.4]])
route(gate,'In3.Cu',.3,[[36.15,7.4],[36.15,9],[38.05,10.9],[38.05,12.2],[38.05,16.4]])
via=c.by_id['10bdeb96-94ec-4dc6-beec-853f3cc22737']
plan={'revision':'R146A','board_sha256':c.sha,'scope':'Independent joint switch-layout trial; exact old power/ground/reference connections must survive. Not adopted.',
 'translations':[{'reference':'Q1601','from_mm':[41,10.25],'delta_mm':[.65,0]},
                 {'reference':'C1602','from_mm':[37.95,13.6],'delta_mm':[0,.53]},
                 {'reference':'R1601','from_mm':[38.6,16.9],'delta_mm':[-.15,.2],'reconstruct_fixed_via_guards':True}],
 'delete_copper':remove,'deleted_copper_expected':snap,
 'removed_branch_reason':'The thin F VS-to-Q1601 drain tail conflicts with the translated body. Q1601 retains its separate 0.50 mm main drain feed, and U1601 VS retains its original UPS_BAT transfer; every old pad pair and all width checks must independently pass.',
 'move_vias':[{'uuid':uid(via),'source_expected':via_snapshot(c.board,via),'position_mm':[39.215,17.1],'reason':'Maintain physical pad clearance beside the translated gate RC resistor; preserve same net and all via geometry, restoring B/In3 tails.'}],
 'vias':[{'net':gate,'position_mm':v,'diameter_mm':.5,'drill_mm':.3} for v in [[36.15,7.4],[38.05,12.2]]],
 'routes':routes,
 'manufacturer_source':{'url':'https://www.ti.com/lit/ds/symlink/lm74502.pdf','revision':'SNOSDE5A Rev A','section':'11.1, page 19','review':'Keep GATE/SRC close to MOSFETs, short gate connection, suitable power copper, and charge-pump capacitor thermally separated. Geometry checks alone do not qualify these requirements.'}}
out.write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps({'plan':str(out),'translations':plan['translations'],'removed_tracks':len(remove),'routes':len(routes)}))

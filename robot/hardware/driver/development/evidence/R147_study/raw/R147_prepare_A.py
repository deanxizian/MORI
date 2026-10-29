"""Rotate the charge-pump capacitor; retain both MOSFETs and original power links."""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R147A-plan.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='1d32097f2b72c2add4d9a2fd68a2c4ed088b23cbf7606aa1ae3256cc5e48330c'
gate='/16 {slash} Actuator_Direct_Switch/ACT_GATE'
p={'revision':'R147A','board_sha256':c.sha,'scope':__doc__+' Diagnostic only, clamp branch remains open; not adopted.',
 'translations':[{'reference':'C1602','from_mm':[37.95,13.6],'delta_mm':[0,1.05],'rotation_deg':0},{'reference':'R1601','from_mm':[38.6,16.9],'delta_mm':[0,.275],'reconstruct_fixed_via_guards':True}],
 'delete_copper':['4e3f344e-4464-4105-b162-6d7b012691cc','6eb245da-0958-40df-ae5f-1da41bcda21f','e50977e0-da61-4216-b09b-ff70e6bb72f8','5081ae9b-2f88-480b-9119-e414c71a573b','84e73931-da8a-48b0-9a6d-bd6779d3010c','be6222d3-8214-485c-9a6d-42f4705d5d50','c8a51a1b-acd7-4c00-a311-cf74fd76a0b9','e6c12a9f-8169-4789-94c0-3fb54db58daa','cf574466-c886-4f23-8190-6cea0c215513','ed3ea5a9-9b69-4ba6-b3db-df6ca2c391a7','1614f6f7-b337-4071-917f-04e2ce3befdc','23caad3a-a256-4835-b0a8-f9466105f55e','b422bd16-a21a-4191-afb2-6d6e4fa5b55e'],
 'deleted_copper_expected':{},'routes':[],
 'vias':[{'net':gate,'position_mm':[38.15,12.95],'diameter_mm':.5,'drill_mm':.3}]}
for u in p['delete_copper']:
 t=c.by_id[u];p['deleted_copper_expected'][u]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
u='10bdeb96-94ec-4dc6-beec-853f3cc22737'
p['move_vias']=[{'uuid':u,'source_expected':via_snapshot(c.board,c.by_id[u]),'position_mm':[39.35,17.175],'reason':'Restore B/In3 gate connection while preserving clearance to the translated RC resistor pads.'}]
def route(n,l,w,pts):p['routes'].append({'net':n,'layer':l,'width_mm':w,'points_mm':pts})
route('/UPS_BAT','B.Cu',.3,[[39.15,13],[39.15,14.4],[38.9,14.65]])
route('Net-(U1601-VCAP)','B.Cu',.25,[[37,14.65],[37,15.35],[37.65,16],[37.65,17.575]])
route(gate,'B.Cu',.2,[[38.6,16.35],[38.95,16.35],[39.35,16.75],[39.35,17.175]])
route(gate,'In3.Cu',.2,[[38.715,16.4],[39.35,17.035],[39.35,17.175]])
route('Net-(C1603-~-Pad1)','B.Cu',.2,[[38.6,18],[39.1,18.5],[39.1,20.3]])
route(gate,'F.Cu',.3,[[38.2475,12.155],[38.2475,12.8525],[38.15,12.95],[37.825,13.275],[37.825,13.95]])
out.write_text(json.dumps(p,indent=2)+'\n');print(str(out))

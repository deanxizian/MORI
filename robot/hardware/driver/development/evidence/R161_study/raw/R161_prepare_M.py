"""Jointly shorten the old ACT_UV escape and move one non-ground transfer 0.1 mm.
This opens a grounded F-face OV corridor around both existing transfer holes,
instead of cutting the J401 ground thermal or its In2 wheel-power feed.
All original ground transfers and circuit pin nets are retained.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R161M-plan.json';assert not out.exists()
p=json.loads((b/'R161K-plan.json').read_text());p['revision']='R161M';p['scope']+='\n'+__doc__
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');assert c.sha==p['board_sha256']
ids=['5b69c763-ffa8-42a9-acfe-ff8acf08cae4','775ad27c-3614-4a1b-bbc5-2cf8ebd5354a','b49ae62c-c9b4-45a5-9f7a-43d44302b960','a54fc166-ee39-4579-ab69-18bc85473b2b','3a0d3c6c-4ee1-41e4-8105-d3c0ee438f9c']
for u in ids:
 assert u not in p['delete_copper'];t=c.by_id[u];p['delete_copper'].append(u)
 p['deleted_copper_expected'][u]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
u='5cc2b6b0-e919-4910-b0af-8902a95393d9'
p['move_vias'].append({'uuid':u,'source_expected':via_snapshot(c.board,c.by_id[u]),'position_mm':[59.6,18.125],'reason':__doc__})
p['routes'][22]['points_mm']=[[60.55,17],[59.65,17],[59.65,17.325],[59.4,17.3],[58.875,17.725],[58.8,18.2],[58.8,18.8],[59.075,19.075],[60.6,19.075],[60.9,19.375],[60.9,22.9],[61,23]]
p['routes'].extend([
 {'net':'/17 {slash} Actuator_Overcurrent/ACT_UV_N','layer':'F.Cu','width_mm':.2,'points_mm':[[58.6375,16.7],[58.1,17.7]]},
 {'net':'Net-(U402-1Y)','layer':'B.Cu','width_mm':.2,'points_mm':[[59.6,17.175],[59.6,18.125]]},
 {'net':'Net-(U402-1Y)','layer':'In2.Cu','width_mm':.2,'points_mm':[[58.475,16.9],[59.6,18.125]]},
])
out.write_text(json.dumps(p,indent=2)+'\n');print(p['revision'])

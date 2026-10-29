"""Joint Q1602 gate / D1001 K transfer with nearby decoupler and WDI pull-down placement. Independent diagnostic candidate only."""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R148A-plan.json';assert not out.exists();c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');gate='/16 {slash} Actuator_Direct_Switch/ACT_GATE';knet='Net-(D1001-K)'
p={'revision':'R148A','scope':__doc__,'board_sha256':c.sha,'translations':[{'reference':'C1003','from_mm':[35.75,8.25],'delta_mm':[-.15,0]},{'reference':'R303','from_mm':[38.2,6.7],'delta_mm':[0,-.6]}],'delete_copper':[],'deleted_copper_expected':{},'routes':[],'vias':[{'net':knet,'position_mm':[36.6,7.5],'diameter_mm':.5,'drill_mm':.3}]}
for u in ['2aec14aa-0077-5ab2-9589-11e9d03d7bb0','4a8c4fde-1de1-542c-8f8c-d0979fcc5a02','a7f57e5d-19a8-5e7e-8521-c65a9ba7ce89','d8cca0ad-e5f1-5baa-a750-94b5abf51d4d','dd4508e8-5118-511a-a8d6-6da185ef8da9','065b6ab6-13b9-47dd-b8a6-6abbaade1ff6','c256071d-f9ba-4852-af1b-2a35e0cc3270','4a88202c-3f7a-4a82-8966-dd2dbd31d6c5','a8fb154d-c402-4127-941b-414cb3e664cc']:
 t=c.by_id[u];p['delete_copper'].append(u);p['deleted_copper_expected'][u]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
u='ac54e9fd-c736-455d-9d74-9d30a773ab5d';p['reassign_vias']=[{'uuid':u,'source_expected':via_snapshot(c.board,c.by_id[u]),'net':gate,'position_mm':[37.45,7.5]}]
def route(n,l,w,pts):p['routes'].append({'net':n,'layer':l,'width_mm':w,'points_mm':pts})
route(gate,'F.Cu',.2,[[36.2525,8.345],[36.82,8.345],[37.45,7.715],[37.45,7.5]])
route(gate,'B.Cu',.3,[[37.45,7.5],[37.85,7.9],[37.85,12.5525],[37.55,12.8525]])
route(knet,'B.Cu',.2,[[36.6,7.5],[36.3875,7.7125],[36.3875,14.1125],[35.75,14.75]])
route(knet,'In3.Cu',.2,[[29.4123,7.8],[35.9,7.8],[36.2,7.5],[36.6,7.5],[36.6,7.8],[37.15,8.35],[38.2,8.35],[38.75,7.8],[46.575,7.8]])
route('MOTION_3V3','B.Cu',.2,[[35.25,6.55],[35.6,6.9],[35.6,7.475]])
route('/01 {slash} Core/WDI','B.Cu',.2,[[37.625,5.6],[37.625,6.1]])
out.write_text(json.dumps(p,indent=2)+'\n');print(out)

"""Simplified K main approach and gate entry avoiding measured native reference void edges; candidate only."""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');p=json.loads((b/'R148C-plan.json').read_text());p['revision']='R148D';p['scope']=__doc__;c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');assert c.sha==p['board_sha256']
u='924f6575-b6ae-4a6d-b17b-a6f23e40453e';t=c.by_id[u];p['delete_copper'].append(u);p['deleted_copper_expected'][u]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
for r in p['routes']:
 if r['net']=='/16 {slash} Actuator_Direct_Switch/ACT_GATE' and r['layer']=='F.Cu':r['points_mm']=[[36.2525,8.345],[36.87,8.345],[37.3,7.915],[37.2,7.3]]
 if r['net']=='Net-(D1001-K)' and r['layer']=='In3.Cu':r['points_mm']=[[28.7623,7.15],[29.1623,7.55],[36.54,7.55],[36.54,7.8],[36.825,8.085],[38.3,8.085],[38.585,7.8],[46.575,7.8]]
out=b/'R148D-plan.json';assert not out.exists();out.write_text(json.dumps(p,indent=2)+'\n')

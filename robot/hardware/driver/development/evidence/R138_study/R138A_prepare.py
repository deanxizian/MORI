"""Independent layout comparison: source-near series resistor, MCU-side pulldown."""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
p=Path('robot/.state/c3-completion/trials');src=Path('robot/hardware/driver/development/native');c=Copper(src/'MORI_Interface_C3.kicad_pcb')
series=json.loads((p/'R138_near_source_priority_poses.json').read_text())['retained_individual_poses']['R1003'][0]
pulldown=next(r for r in json.loads((p/'R137_back_adc_fine_individual.json').read_text())['retained_individual_poses']['R1033'] if r['position_mm']==[21.1,28.6] and r['angle_deg']==180)
plan={'revision':'R138A','board_sha256':c.sha,'scope':__doc__+' Both parts remain on B. This placement is unadopted. The prior ADC common link and exact CLR/FAULT segments are removed for explicit rerouting; none may be left disconnected in an adopted candidate. MCU route remains unproven.','placement_comparisons':['R138_near_source_priority_poses.json R1003[0]','R137_back_adc_fine_individual.json R1033 (21.1,28.6)/180'],'translations':[],'delete_copper':['a3bd846a-f816-4a29-a3b8-1fa46647bbda','2e941596-56a3-44d9-9be1-4269516af7b1','84bbb131-0677-4df6-8618-dc5ef8345ec4','60c16ff0-1985-5e62-8b16-14517a64d7d7'],'deleted_copper_expected':{},'routes':[],'vias':[]}
for ref,row in [('R1003',series),('R1033',pulldown)]:
 f=next(f for f in c.footprints if f.GetReference()==ref);old=list(xy(f.GetPosition()));plan['translations'].append({'reference':ref,'from_mm':old,'delta_mm':[round(a-b,6) for a,b in zip(row['position_mm'],old)],'rotation_deg':row['angle_deg']})
for u in plan['delete_copper']:
 t=c.by_id[u];assert type(t).__name__=='PCB_TRACK';plan['deleted_copper_expected'][u]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
(p/'R138A-plan.json').write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps({'translations':plan['translations'],'deleted':len(plan['delete_copper'])}))

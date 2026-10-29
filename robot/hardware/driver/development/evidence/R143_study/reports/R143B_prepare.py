"""Build an explicit joint placement plan from immutable R142; not adoption."""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R143B-plan.json';assert not out.exists()
c=Copper(str(b/'R142/MORI_Interface_C3.kicad_pcb'))
assert c.sha=='2a7c04b8430875a0f8f9e4bdde4b789da6b8efb5f84ee991a360f1d5b6d006dd'
p=json.loads((b/'R143A-plan.json').read_text());p['revision']='R143B'
p['purpose']='Independent joint U303/C303 reset-supervisor and R1022 ADC placement. Restore CLR after explicitly reusing its former via for D2. Retain all native rules and all other pad connections; no acceptance until native refill, all electrical/reference regression and local review.'
fs={f.GetReference():f for f in c.footprints}
p['translations']=[]
for ref,pos,angle in [('U303',[21,12.4],0),('C303',[24.2,13.7],0),('R1022',[41,17.6],270)]:
 f=fs[ref];o=list(xy(f.GetPosition()));p['translations'].append({'reference':ref,'from_mm':o,'delta_mm':[round(pos[0]-o[0],6),round(pos[1]-o[1],6)],'rotation_deg':angle})
extra=['53522878-2ddb-52d7-93a6-a12df88268cf','624fe692-481e-582f-8e19-1c25cf9d48d3','6bdc90d4-66d7-5c79-a33d-f2102f11e4aa','525a7ae2-c619-480c-b284-1a1b028034bc','0c67320a-3b36-41f5-9372-e866af4a1d9b','879415a2-d05e-4a60-8fc6-43453ead98fa','7b4c4e31-9dd9-4673-bf37-973c8204164e','4f4d6d69-0c12-4912-8387-df7396dbc26d','d922681a-fe01-45ef-a37a-429c9da5ac6d','d3724c43-a2a4-4a2b-93c9-f441fadeb575']
for u in extra:
 t=c.by_id[u];assert type(t).__name__=='PCB_TRACK';p['delete_copper'].append(u)
 p['deleted_copper_expected'][u]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
p['routes'][1]['points_mm']=[[30.8,13.0],[30.8,13.25],[30.4,13.65],[30.4,14.0]]
p['routes'].append({'net':'MOTION_3V3','layer':'B.Cu','width_mm':.2,'points_mm':[[22.5,13.7],[23.425,13.7]]})
out.write_text(json.dumps(p,indent=2)+'\n')
print('R143B plan',len(p['delete_copper']),'replaced tracks',len(p['translations']),'part transforms')

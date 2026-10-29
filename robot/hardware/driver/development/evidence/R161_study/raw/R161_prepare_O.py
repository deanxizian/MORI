"""Clear the native slot-reference boundary and retire two obsolete transfers.
The old FAULT dead branch stops at the retained multi-layer 45.7 mm junction;
the old OV hole is redundant with the new upstream transfer and continuous B
tracks. All replacement links still require completion before adoption.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R161O-plan.json';assert not out.exists()
p=json.loads((b/'R161N-plan.json').read_text());p['revision']='R161O';p['scope']+='\n'+__doc__
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');assert c.sha==p['board_sha256']
p['routes'][23]['points_mm']=[[61.0,23.0],[61.25,23.0],[62.7,24.45],[63.65,24.45],[64.8,25.6]]
ids=['5808d7e6-a7d5-59ca-8e1f-24590722bbab','80dca04c-cb3d-5375-ad0d-428f6828bafc','da691b71-1e5a-5ed0-9c55-36e49c427375']
for u in ids:
 assert u not in p['delete_copper'];t=c.by_id[u];p['delete_copper'].append(u)
 p['deleted_copper_expected'][u]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
remove=['5a9bd66c-9c9b-4f28-8dfe-b061d59dedaa','4235992b-10c1-49b9-b6d7-b3df51cada3c']
p['move_vias']=[v for v in p['move_vias'] if v['uuid'] not in remove]
for u in remove:p['remove_obsolete_vias'].append({'uuid':u,'source_expected':via_snapshot(c.board,c.by_id[u]),'remaining_contact_layers':[],'reason':__doc__})
out.write_text(json.dumps(p,indent=2)+'\n');print(p['revision'])

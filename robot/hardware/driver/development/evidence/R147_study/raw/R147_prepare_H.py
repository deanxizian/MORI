"""Paired horizontal sense resistors, short pin approaches and removal of obsolete inner gate branch. Trial only."""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R147H-plan.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');p=json.loads((b/'R147G-plan.json').read_text());assert c.sha==p['board_sha256']
d=json.loads((b/'R147-sense-pair-placements.json').read_text())
for ref,pos in [('R1701',[42.5,10.6]),('R1707',[42.4,12.15])]:assert any(r['position_mm']==pos and r['rotation_deg']==0 for r in d['placements'][ref]),ref
p['revision']='R147H';p['scope']=__doc__
p['translations'][2]={'reference':'R1707','from_mm':[42.5,13.35],'delta_mm':[-.1,-1.2],'rotation_deg':0}
p['translations'][3]={'reference':'R1701','from_mm':[43.1,11.1],'delta_mm':[-.6,-.5],'rotation_deg':0}
for u in ['1614f6f7-b337-4071-917f-04e2ce3befdc','3475564a-5171-476b-a733-076099a49495','7c8ee776-b45e-458e-b88b-0226173da45c','98e7827c-04d8-49f1-946f-cc4ae4ac9db7']:
 p['delete_copper'].append(u);t=c.by_id[u];p['deleted_copper_expected'][u]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
p['remove_obsolete_vias'][0]['remaining_contact_layers']=[];p['remove_obsolete_vias'][0]['reason']='Both replaced old B tail and obsolete In3 branch are deleted; no original layer transfer remains.'
u='95ff793a-b4b7-4e87-bdbf-8d8902a9981b';p['remove_obsolete_vias'].append({'uuid':u,'source_expected':via_snapshot(c.board,c.by_id[u]),'remaining_contact_layers':['B.Cu'],'reason':'Obsolete inner gate branch removed; retained B copper remains continuous and joins the new clamp approach on B.'})
p['routes']=[r for r in p['routes'] if r['net'] not in ['/WHEEL_VM','Net-(U1701-IN-)','Net-(U1701-LIMIT)']]
def route(n,l,w,pts):p['routes'].append({'net':n,'layer':l,'width_mm':w,'points_mm':pts})
route('/WHEEL_VM','B.Cu',.2,[[41.575,12.15],[41.575,12.35],[42.1,12.875],[42.1,13.75],[42.55,14.2]])
route('Net-(U1701-IN-)','B.Cu',.2,[[43.225,12.15],[43.225,12.85],[45.05,12.85]])
route('Net-(U1701-LIMIT)','B.Cu',.2,[[43.325,10.6],[43.975,11.25],[43.975,12.35],[45.05,12.35]])
out.write_text(json.dumps(p,indent=2)+'\n');print(out)

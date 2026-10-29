"""Joint sense-resistor arrangement and upper-layer gate branch, preserving the CAM power region."""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R147G-plan.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');p=json.loads((b/'R147F-plan.json').read_text());assert c.sha==p['board_sha256']
p['revision']='R147G';p['scope']=__doc__+' Diagnostic candidate, not adopted.'
p['translations'][2]={'reference':'R1707','from_mm':[42.5,13.35],'delta_mm':[.6,-2.25],'rotation_deg':-90}
p['translations'][3]={'reference':'R1701','from_mm':[43.1,11.1],'delta_mm':[-.25,-2.2],'rotation_deg':0}
for u in ['32847112-70c5-4584-9a32-15beb37698a4','a22764d5-7e09-4478-8eb8-85e40f858816','e76465b2-c675-4426-864b-7e96647a51f0','fdb496d7-3dee-4423-94c3-c8615b8a236d','3327739b-54e7-429a-b786-eb7f7c2fe31a','8a5453a3-8ddd-464a-8a54-ac56b38ede0d']:
 p['delete_copper'].append(u);t=c.by_id[u];p['deleted_copper_expected'][u]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
u='10bdeb96-94ec-4dc6-beec-853f3cc22737';p['remove_obsolete_vias']=[{'uuid':u,'source_expected':via_snapshot(c.board,c.by_id[u]),'remaining_contact_layers':['In3.Cu'],'reason':'Old RC B tail removed; gate RC now uses the separate upper transfer. Original inner branch remains connected to the clamp.'}]
gate='/16 {slash} Actuator_Direct_Switch/ACT_GATE';p['vias'][1]['position_mm']=[41.45,13.1]
p['routes']=[r for r in p['routes'] if not (r['net'] in ['/WHEEL_VM','Net-(U1701-IN-)'] or (r['net']==gate and (r['layer']=='In3.Cu' or r['points_mm'][0]==[41.35,13.4])))]
def route(n,l,w,pts):p['routes'].append({'net':n,'layer':l,'width_mm':w,'points_mm':pts})
route(gate,'B.Cu',.2,[[41.45,13.1],[41,13.55],[41,16.075]])
route(gate,'In3.Cu',.2,[[37.55,12.8525],[38.3025,12.1],[41.45,12.1],[41.45,13.1]])
route('/WHEEL_VM','B.Cu',.2,[[43.1,10.275],[42.25,10.275],[42.25,13.9],[42.55,14.2]])
route('Net-(U1701-IN-)','B.Cu',.2,[[43.1,11.925],[43.1,12.275],[43.675,12.85],[45.05,12.85]])
route('Net-(U1701-LIMIT)','B.Cu',.2,[[43.675,8.9],[43.9,9.125],[43.9,12.35],[45.05,12.35]])
out.write_text(json.dumps(p,indent=2)+'\n');print(str(out))

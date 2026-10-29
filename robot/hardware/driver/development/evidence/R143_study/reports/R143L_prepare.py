"""Separate the ADC via/placement check from the problematic inner-plane route.
Reroute three exact UPS_5V capacitor-feed tracks around the proposed via, keep
all source constraints, and leave the new In3 ADC branch for a power-aware pass.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R143L-plan.json';assert not out.exists()
c=Copper(str(b/'R143K/MORI_Interface_C3.kicad_pcb'));m=json.loads((b/'R143K/edit_manifest.json').read_text())
p={'revision':'R143L','board_sha256':c.sha,'purpose':__doc__,'translations':[{'reference':'R1022','from_mm':[23.3,16.2],'delta_mm':[.1,0],'rotation_deg':270}],'delete_copper':[],'deleted_copper_expected':{},'routes':[],'vias':[]}
ids={r['uuid'] for r in m if r['kind']=='track' and r['net']=='/01 {slash} Core/WHEEL_ADC'}
feed=[]
for t in c.segments:
 if t.GetNetname()=='/06 {slash} CAM_Buck/UPS_5V' and t.GetLayer()==pcb.F_Cu and c.shapes[uid(t),'F.Cu'].distance(Point(22.45,15.85))<.45:
  ids.add(uid(t));feed.append(t)
assert len(feed)==3 and {t.GetWidth()/1e6 for t in feed}=={.3}
for u in sorted(ids):
 t=c.by_id[u];p['delete_copper'].append(u);p['deleted_copper_expected'][u]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
v=c.by_id[next(r['uuid'] for r in m if r['kind']=='via')];assert via_contact_layers(c.board,v,ids)==[]
p['remove_obsolete_vias']=[{'uuid':uid(v),'source_expected':via_snapshot(c.board,v),'remaining_contact_layers':[],'reason':'Replace both exact trial ADC branches and move the trial via clear of the F-side supply feed and the rotated R1022 pad.'}]
p['vias']=[{'net':'/01 {slash} Core/WHEEL_ADC','position_mm':[22.5,15.9],'diameter_mm':.5,'drill_mm':.3}]
p['routes']=[{'net':'/06 {slash} CAM_Buck/UPS_5V','layer':'F.Cu','width_mm':.3,'points_mm':[[22.5,14.7],[23.25,14.7],[23.525,14.975],[23.525,15.98]]},{'net':'/01 {slash} Core/WHEEL_ADC','layer':'B.Cu','width_mm':.2,'points_mm':[[22.5,15.9],[22.7,16.1],[22.7,17.025],[23.4,17.025]]}]
out.write_text(json.dumps(p,indent=2)+'\n')

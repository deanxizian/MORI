"""Rotate R1022 in the vacated C303 region and shift the ADC via northeast.
The prior actual via split CAM power and narrowed MOTION_3V3. This proposal
uses a different branch position and preserves all original ground copper for
native refill to determine whether its connectivity is restored.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R143K-plan.json';assert not out.exists()
c=Copper(str(b/'R143J/MORI_Interface_C3.kicad_pcb'))
g=json.loads((b/'R143G/edit_manifest.json').read_text())
p={'revision':'R143K','board_sha256':c.sha,'purpose':__doc__,'translations':[{'reference':'R1022','from_mm':[23.5,16.2],'delta_mm':[-.2,0],'rotation_deg':270}],'delete_copper':[],'deleted_copper_expected':{},'routes':[],'vias':[]}
for row in g:
 if row['kind']=='track':
  t=c.by_id[row['uuid']];u=uid(t);p['delete_copper'].append(u)
  p['deleted_copper_expected'][u]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
v=c.by_id[next(row['uuid'] for row in g if row['kind']=='via')]
assert via_contact_layers(c.board,v,p['delete_copper'])==[]
p['remove_obsolete_vias']=[{'uuid':uid(v),'source_expected':via_snapshot(c.board,v),'remaining_contact_layers':[],'reason':'Both attached trial ADC branches are explicitly replaced; remove this trial-only via that cut two power corridors.'}]
p['vias']=[{'net':'/01 {slash} Core/WHEEL_ADC','position_mm':[22.45,15.85],'diameter_mm':.5,'drill_mm':.3}]
p['routes']=[{'net':'Net-(U1001-D2_{slash}_WHEEL_ADC)','layer':'B.Cu','width_mm':.2,'points_mm':[[30.4,14],[30.15,14.25],[26.65,14.25],[25.8,15.1],[23.3,15.1]]},{'net':'/01 {slash} Core/WHEEL_ADC','layer':'In3.Cu','width_mm':.2,'points_mm':[[35.95,23.25],[35.95,21.4],[34.85,20.3],[33.65,20.3],[28.15,14.8],[23.5,14.8],[22.45,15.85]]},{'net':'/01 {slash} Core/WHEEL_ADC','layer':'B.Cu','width_mm':.2,'points_mm':[[22.45,15.85],[22.7,16.1],[22.7,17.025],[23.3,17.025]]}]
out.write_text(json.dumps(p,indent=2)+'\n')

"""Validate the inherited actual 0.48mm 3V3 corridor before UV search on H."""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');c=Copper(b/'R165J/MORI_Interface_C3.kicad_pcb')
p=json.loads((b/'R165-power-spine.json').read_text());sp=LineString(p['points_mm']).buffer(p['preserved_width_mm']/2)
g=c.copper[('MOTION_3V3','In3.Cu')]
assert sp.difference(g).area<1e-6
p['inherited_from_sha256']=p['source_sha256'];p['source_sha256']=c.sha
with (b/'R165J-power-spine.json').open('x') as f:json.dump(p,f,indent=2);f.write('\n')
fs={f.GetReference():f for f in c.footprints};f=fs['R1031'];pad=next(p for p in f.Pads() if p.GetNumber()=='2')
land=c.shapes[uid(pad),'F.Cu'];via_points=[(45.65,30),(47,30)]
components=[g for g in parts(c.copper[('GND','F.Cu')]) if g.intersects(land)]
print('R1031',f.GetValue(),c.pad_name(pad),pad.GetNetname())
print('F_ground_components_at_pad',len(components))
print('same_F_copper_at_old_vias',[(pt,any(g.intersects(Point(pt).buffer(.2)) for g in components)) for pt in via_points])
a=json.loads((b/'R165J-audit.json').read_text())
print('audit',{'power_failures':sum(x['status']!='PASS' for x in a['power_width']),'ground_groups':[len(x) for x in a['GND_groups']],'old_ref_losses':len(a['retained_trace_reference_loss']),'new_ref_losses':sum(x.get('reference_uncovered_mm2_outside_existing_lands_and_own_transfers',0)>1e-6 for x in a['new_copper_review']),'lost_nets':[x['net'] for x in a['lost_pad_connections']]})

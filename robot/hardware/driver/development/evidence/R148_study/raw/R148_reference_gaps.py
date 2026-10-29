"""Locate actual filled-reference deficits of R148C; read-only, no relaxation."""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');c=Copper(b/'R148C/MORI_Interface_C3.kicad_pcb');reg=json.loads((b/'R148C-audit.json').read_text());rows=[]
for r in reg['new_copper_review']:
 if r['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']<=1e-6:continue
 t=c.by_id[r['uuid']];ly=r['layer'];ref=REFERENCE[ly];stroke=c.shapes[uid(t),ly];own=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==r['net']]);transfers=unary_union([reference_transfer_shape(c,c.by_id[v['uuid']],ref).buffer(v['clearance_mm']+v['polygon_tolerance_mm']) for v in r['own_transfer_voids']]);missing=stroke.difference(own).difference(c.copper['GND',ref]).difference(transfers)
 row={'uuid':uid(t),'net':r['net'],'layer':ly,'start':xy(t.GetStart()),'end':xy(t.GetEnd()),'missing_area_mm2':missing.area,'missing_wkt':missing.wkt,'closest_vias':sorted([{'uuid':uid(v),'net':v.GetNetname(),'pos':xy(v.GetPosition()),'distance_mm':Point(xy(v.GetPosition())).distance(missing)} for v in c.vias],key=lambda z:z['distance_mm'])[:3]};rows.append(row)
(b/'R148C-reference-gaps.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))

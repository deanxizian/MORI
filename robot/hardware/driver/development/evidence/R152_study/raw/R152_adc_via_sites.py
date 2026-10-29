"""Screen ADC layer-transfer sites for replacing the candidate-only F.Cu detour. Same-net pad clearance and native via guards retained. Ground-plane cuts and routing still require native audit."""
import sys,json
from pathlib import Path
import numpy as np
from shapely import contains_xy,intersects_xy
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');c=Copper(b/'R152F/MORI_Interface_C3.kicad_pcb');net='/01 {slash} Core/BAT_ADC'
ob=[s.buffer(.457) for (i,ly),s in c.shapes.items() if isinstance(c.by_id[i],pcb.PAD) or c.by_id[i].GetNetname()!=net]
ob += [k['shape'].buffer(.257) for k in c.keepouts if k['vias']]
ob += [Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6+.307) for v in c.vias]
ob += [Point(xy(p.GetPosition())).buffer(max(xy(p.GetDrillSize()))/2+.557) for p in c.pads if max(xy(p.GetDrillSize()))>0]
blocked=unary_union(ob)
protected=[]
for t in c.segments:
 ly=c.board.GetLayerName(t.GetLayer())
 if t.GetNetname() not in ['GND',net] and ly in REFERENCE:protected.append(c.shapes[uid(t),ly].intersection(c.copper['GND',REFERENCE[ly]]))
ref_guard=unary_union(protected).buffer(.657)
xx,yy=np.meshgrid(np.arange(43.8,46.301,.025),np.arange(28.2,33.501,.025));physical=~intersects_xy(blocked,xx,yy);valid=physical&~intersects_xy(ref_guard,xx,yy)
rows=[]
for x,y in zip(xx[valid],yy[valid]):
 pt=Point(float(x),float(y));rows.append({'position_mm':[round(float(x),4),round(float(y),4)],'ground_reference_overlap_mm2':{ly:pt.buffer(.25).intersection(c.copper['GND',ly]).area for ly in ['In1.Cu','In4.Cu']}})
result={'scope':__doc__,'source_sha256':c.sha,'grid_mm':.025,'physical_sites':int(physical.sum()),'reference_screened_sites':len(rows),'sites':rows,'limits':'Candidate-only ADC is intentionally not protected because its F.Cu segment is being replaced; all foreign retained reference geometry remains protected. R13, power continuity, exact centres and local return must be checked on native candidate.'}
(b/'R152-ADC-via-sites.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'physical_sites':int(physical.sum()),'reference_screened_sites':len(rows),'bounds':[(min(r['position_mm'][0] for r in rows),min(r['position_mm'][1] for r in rows)),(max(r['position_mm'][0] for r in rows),max(r['position_mm'][1] for r in rows))] if rows else [],'first':rows[:5],'last':rows[-5:]}))

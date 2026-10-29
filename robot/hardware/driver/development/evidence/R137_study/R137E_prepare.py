"""Prepare and geometrically screen a coupled ADC/CAM-return trial, without adopting it."""
import json,sys,hashlib
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner
base=Path('robot/.state/c3-completion/trials');src=base/'R137C/MORI_Interface_C3.kicad_pcb'
p=Planner(str(src),.05,['B.Cu','In3.Cu','F.Cu'],.2);c=p.c
net='Net-(U1001-D3_{slash}_current_ADC)'
plan=json.loads((base/'R137D-plan.json').read_text());plan.update(revision='R137E',board_sha256=c.sha,scope='Unadopted mixed-face ADC candidate. Adjust top ADC transfer, simplify deliberate bends, and add one GND stitch to enable a separately verified CAM power bridge. Does not yet repair all power or removed FAULT/ADC links.')
plan['routes'][0]['points_mm']=[[30,6.2],[28.85,5.05],[28.85,4.5],[29.75,3.6],[35.75,3.6],[36.5,4.35],[36.5,5.4],[35.95,5.95]]
plan['routes'][1]['points_mm']=[[35.95,5.95],[35.95,6.6],[35.2,7.35],[30.05,7.35],[29.05,6.35],[26.35,6.35],[16.4,16.3],[16.4,22.95],[20.3,26.85]]
plan['routes'][2]['points_mm']=[[20.3,26.85],[21.6,28.15],[22.05,28.15]]
plan['vias'][0]['position_mm']=[35.95,5.95]
plan['vias'].append({'net':'GND','position_mm':[15.65,16.1],'diameter_mm':.5,'drill_mm':.3})
_,_,obs,allowed=p.geometry(net);rows=[]
for r in plan['routes']:
 i=p.layers.index(r['layer']);ln=LineString(r['points_mm']);rows.append({'kind':'track','layer':r['layer'],'obstacle_intersection':not ln.intersection(obs[i]).is_empty,'outside_reference_length':ln.difference(allowed[i]).length})
for v in plan['vias']:
 pt=Point(v['position_mm']);hits=[]
 for (u,ly),s in c.shapes.items():
  o=c.by_id[u]
  clearance=.457 if isinstance(o,pcb.PAD) or o.GetNetname()!=v['net'] else 0
  if clearance and s.distance(pt)<clearance:hits.append({'kind':'pad' if isinstance(o,pcb.PAD) else 'copper','layer':ly,'id':c.pad_name(o),'net':o.GetNetname(),'distance':s.distance(pt)})
 for k in c.keepouts:
  if k['vias'] and k['shape'].distance(pt)<.257:hits.append({'kind':'keepout','name':k['name'],'distance':k['shape'].distance(pt)})
 if v['net']=='GND':
  for r in plan['routes']:
   if LineString(r['points_mm']).distance(pt)<.555:hits.append({'kind':'new_signal','layer':r['layer'],'distance':LineString(r['points_mm']).distance(pt)})
 rows.append({'kind':'via','net':v['net'],'position_mm':v['position_mm'],'hits':hits})
(base/'R137E-plan.json').write_text(json.dumps(plan,indent=2)+'\n');(base/'R137E-preflight.json').write_text(json.dumps({'source_sha256':c.sha,'rows':rows},indent=2)+'\n')
print(json.dumps(rows),flush=True)

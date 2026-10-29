"""Separate native obstacles from full-stroke reference screening, read-only.

This produces diagnostic paths only. It does NOT waive reference review, alter
native rules, save a PCB, or allow adoption. New vias retain the conservative
screen protecting reference beneath every retained trace.
"""
import json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from plan_layered_route import Planner,mask
from copper_geometry import *
from shapely.geometry import box
out=Path('robot/.state/c3-completion/trials/R136-reference-diagnostic');out.mkdir(exist_ok=False)
p=Planner('robot/.state/c3-completion/trials/R136A/MORI_Interface_C3.kicad_pcb',.05,['B.Cu','In3.Cu','F.Cu'],.2)
rows=[]
for net in ['Net-(U1001-D3_{slash}_current_ADC)','/01 {slash} Core/ACT_CURRENT_ADC']:
 free,vf,blocked,strict_allowed=p.geometry(net)
 region=box(.61,.61,69.39,34.39)
 allowed=[region]*len(p.layers)
 free=np.array([~mask(ob,p.xx,p.yy)&mask(region,p.xx,p.yy,True) for ob in blocked])
 gs=p.routing_groups(net)
 assert len(gs)==2
 result=p.solve(gs[0],gs[1],(free,vf,blocked,allowed),500000)
 gaps=[]
 if result['status']=='PROPOSAL':
  for route in result['routes']:
   ly=route['layer'];ref=REFERENCE[ly];stroke=LineString(route['points_mm']).buffer(route['width_mm']/2)
   missing=stroke.difference(p.ground[ref]);gaps.append({'layer':ly,'reference':ref,'raw_uncovered_area_mm2':missing.area,'raw_gap_bounds_mm':missing.bounds if not missing.is_empty else None})
 rows.append({'net':net,'source_sha256':p.c.sha,'scope':'DIAGNOSTIC_ONLY; native copper/keepout obstacles and conservative new-via guard retained; existing full-stroke GND coverage temporarily omitted from search, not waived for design or verification.','result':result,'raw_reference_gaps_not_waived':gaps})
 (out/'searches.json').write_text(json.dumps(rows,indent=2)+'\n')
 print(json.dumps(rows[-1],indent=2),flush=True)

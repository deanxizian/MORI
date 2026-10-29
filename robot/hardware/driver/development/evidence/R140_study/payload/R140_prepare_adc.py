"""Validate centre-snapped ADC common route before native refill.

The original proposal accounted for foreign power fill as a cost only. This
candidate remains an unaccepted experiment; actual power/reference regressions
are mandatory. No power or reference rule is weakened.
"""
import ast,copy,json,sys
from pathlib import Path
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner
b=Path('robot/.state/c3-completion/trials');net='/01 {slash} Core/ACT_CURRENT_ADC'
p=Planner(str(b/'R139K/MORI_Interface_C3.kicad_pcb'),.05,['B.Cu','In3.Cu','F.Cu'],.2);c=p.c
node=next(x for x in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(x,ast.FunctionDef) and x.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab_helper','exec'))
free,vf,blocked,allowed=p.geometry(net)
for i,ly in enumerate(p.layers):
 if ly in ['F.Cu','B.Cu']:
  bodies=unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly])
  own=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
  blocked[i]=unary_union([blocked[i],bodies.buffer(.102).difference(own.buffer(-.001))])
r=copy.deepcopy(json.loads((b/'R139D-power-aware-adc/searches.json').read_text())[1]['result'])
r['routes'][0]['points_mm'][:2]=[[25.5,9.75],[25.5,10.45]]
r['routes'][-1]['points_mm'][-2:]=[[16.4,23.05],[20.2,26.85]]
checks=[]
for route in r['routes']:
 i=p.layers.index(route['layer']);line=LineString(route['points_mm'])
 checks.append({'layer':route['layer'],'points_mm':route['points_mm'],'obstacle_hit':line.intersects(blocked[i]),'reference_covered':allowed[i].covers(line),'length_mm':line.length})
via_checks=[]
for v in r['vias']:
 x,y=v['position_mm'];ix=round((x-p.xs[0])/p.grid);iy=round((y-p.ys[0])/p.grid)
 via_checks.append({'position_mm':[x,y],'eligible_proxy_site':bool(vf[iy,ix])})
f=b/'R140-adc-centre-screen.json';assert not f.exists();f.write_text(json.dumps({'source_sha256':c.sha,'routes':checks,'vias':via_checks,'scope':__doc__},indent=2)+'\n')
if all(not x['obstacle_hit'] and x['reference_covered'] for x in checks) and all(x['eligible_proxy_site'] for x in via_checks):
 plan={'revision':'R140P','board_sha256':c.sha,'scope':__doc__,'routes':[{'net':net,**x} for x in r['routes']],'vias':[{'net':net,**x} for x in r['vias']]}
 f=b/'R140P-plan.json';assert not f.exists();f.write_text(json.dumps(plan,indent=2)+'\n')
print(json.dumps({'routes':checks,'vias':via_checks}),flush=True)

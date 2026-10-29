from pathlib import Path
import sys,json
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from plan_layered_route import Planner
from copper_geometry import *
p=Path('robot/.state/c3-completion/trials');j=json.loads((p/'R134K-plan.json').read_text());s=json.loads((p/'R134J-search/plan-1.json').read_text());j['revision']='R134L';j['scope']='Independent complete U401-2Y route candidate from R131G with exact grouped rework. Requires native DRC, all regression and visual review. Not adopted.'
s['routes'][0]['points_mm']=[[63.65,7.5],[63.425,7.5],[61.225,9.7],[61.225,11.1],[61.75,11.625],[62.225,11.625]]
s['routes'][-1]['points_mm']=[[60.6,26],[59.325,26],[57.625,24.3],[57.075,24.3],[56.075,23.3],[55.35,23.3],[55.005,23.645],[55.005,24.05]]
planner=Planner(str(p/'R134K/MORI_Interface_C3.kicad_pcb'),.025,['B.Cu','In3.Cu','F.Cu','In2.Cu'],.2);geom=planner.geometry('Net-(U401-2Y)');errors=[]
for ri,r in enumerate(s['routes']):
 li=planner.layers.index(r['layer'])
 for k,(a,b) in enumerate(zip(r['points_mm'],r['points_mm'][1:])):
  line=LineString([a,b]);hit=geom[2][li].intersects(line);inside=geom[3][li].covers(line)
  if hit or not inside:errors.append({'route':ri,'segment':k,'a':a,'b':b,'blocked':hit,'allowed':inside})
(p/'R134L-proposal-screen.json').write_text(json.dumps({'errors':errors,'source_candidate':'R134K','limits':'Read-only geometry screening; not native DRC or post-refill validation'},indent=2)+'\n');print('geometry errors',errors,flush=True)
assert not errors
j['routes']+=s['routes'];j['vias']+=s['vias'];j['route_search_source_sha256']=s['board_sha256'];j['route_search']=s['search'];j['route_adjustments']='Exact existing-via centre endpoints and deliberate 45-degree corners; remove raster micro-jogs without reducing clearance/reference screening.'
(p/'R134L-plan.json').write_text(json.dumps(j,indent=2)+'\n')

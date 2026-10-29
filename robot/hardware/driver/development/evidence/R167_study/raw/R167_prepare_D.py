"""Restore the 90-degree U1702 comparison with a separate local FAULT port.

Every old Q1701/U1702 connection is explicitly reconstructed. The VDD lead is
0.25 mm for the unchanged 0.20 mm power continuity screen. The right-hand INA
lead and left-hand VDD lead are considered together. Full manufacturer bypass
loop review remains open; this preparation cannot be adopted by placement alone.
"""
import ast,json,sys
from pathlib import Path
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner
b=Path('robot/.state/c3-completion/trials');out=b/'R167D-plan.json';assert not out.exists()
p=Planner(b/'R167B/MORI_Interface_C3.kicad_pcb',.05,['B.Cu','F.Cu'],.2);c=p.c
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
act='/17 {slash} Actuator_Overcurrent/ACT_UV_N';port=[56.1,14.9]
routes=[
 dict(net='/HEAD_UV_ENABLE',layer='B.Cu',points_mm=[[57.9847,11.875],[56.8625,11.875],[56.05,12.6875],[56.05,13.0625]]),
 dict(net=act,layer='F.Cu',points_mm=[[56.8,16.3875],[56.8,16.75],[57.65,17.6],[58.1,17.7]]),
 dict(net=act,layer='B.Cu',points_mm=[[57.95,13.0625],[58.35,13.0625],[58.575,13.2875],[58.575,15.75],[58.1,16.225],[58.1,17.7]]),
 dict(net=act,layer='B.Cu',points_mm=[[58.575,14.775],[58.925,14.775]]),
 dict(net='Net-(U1702-INA+)',layer='F.Cu',points_mm=[[59.35,12.575],[59.35,15.7375],[58.7,16.3875]]),
 dict(net='MOTION_3V3',layer='F.Cu',width_mm=.25,points_mm=[[57.75,14.1125],[57.75,13.5],[57.35,13.1],[56.5,13.1],[55.3,14.3],[55.3,14.85],[55.2,15.05]]),
 dict(net='/FAULT_N',layer='B.Cu',points_mm=[[57,14.9375],port]),
]
checks=[]
for rt in routes:
 w=rt.setdefault('width_mm',.2);p.width=w;net=rt['net'];ly=rt['layer'];li=p.layers.index(ly)
 _,_,obs,al=p.geometry(net)
 bodies=unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly])
 lands=unary_union([s for (u,ll),s in c.shapes.items() if ll==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
 blocked=obs[li].union(bodies.buffer(w/2+.002).difference(lands.buffer(-.001)))
 allowed=al[li]
 if net!='/FAULT_N':
  blocked=blocked.union(Point(port).buffer(.25+.205+w/2))
  allowed=allowed.difference(Point(port).buffer(.25+p.internal_clearance+.005+w/2+.002)).union(lands.buffer(-w/2-.002))
 for a,z in zip(rt['points_mm'],rt['points_mm'][1:]):
  line=LineString([a,z]);checks.append(dict(net=net,layer=ly,start=a,end=z,width_mm=w,obstacle_hit=bool(line.intersects(blocked)),reference_allowed=bool(allowed.covers(line))))
for i,rt in enumerate(routes):
 for rz in routes[i+1:]:
  if rt['net']==rz['net'] or rt['layer']!=rz['layer']:continue
  distance=LineString(rt['points_mm']).distance(LineString(rz['points_mm']))
  checks.append(dict(kind='new_route_pair',nets=[rt['net'],rz['net']],layer=rt['layer'],distance_mm=distance,obstacle_hit=distance<.205+(rt['width_mm']+rz['width_mm'])/2,reference_allowed=True))
preflight=b/'R167D-route-preflight.json';assert not preflight.exists();preflight.write_text(json.dumps(dict(scope=__doc__,geometry_source_sha256=c.sha,checks=checks),indent=2)+'\n')
failed=[x for x in checks if x['obstacle_hit'] or not x['reference_allowed']];print('failed',json.dumps(failed,indent=2));assert not failed
plan=json.loads((b/'R167B-plan.json').read_text());plan.update(revision='R167D',scope=__doc__,routes=routes,vias=[dict(net='/FAULT_N',position_mm=port,diameter_mm=.5,drill_mm=.3)],adoption_prohibited=True)
out.write_text(json.dumps(plan,indent=2)+'\n');print(out)

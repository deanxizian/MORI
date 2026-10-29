"""Restore all old Q1701/U1702 connections around a jointly screened FAULT port.

Use the R167A placement, preserve every old via, and reuse the orphaned original
ACT_UV_N transfer. New FAULT port (55.85,15.45) is the only tested A port with
a local referenced VDD restoration proposal. FAULT main trunk is still open.
"""
import ast,json,sys
from pathlib import Path
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner
b=Path('robot/.state/c3-completion/trials');out=b/'R167C-plan.json';assert not out.exists()
p=Planner(b/'R167A/MORI_Interface_C3.kicad_pcb',.05,['B.Cu','F.Cu'],.2);c=p.c
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
act='/17 {slash} Actuator_Overcurrent/ACT_UV_N';port=[55.85,15.45]
routes=[
 dict(net='/HEAD_UV_ENABLE',layer='B.Cu',points_mm=[[57.9847,11.875],[56.8625,11.875],[56.05,12.6875],[56.05,13.0625]]),
 dict(net=act,layer='F.Cu',points_mm=[[59.3875,16.2],[59.3875,16.4125],[58.1,17.7]]),
 dict(net=act,layer='B.Cu',points_mm=[[57.95,13.0625],[58.35,13.0625],[58.575,13.2875],[58.575,15.75],[58.1,16.225],[58.1,17.7]]),
 dict(net=act,layer='B.Cu',points_mm=[[58.575,14.425],[58.925,14.775]]),
 dict(net='Net-(U1702-INA+)',layer='F.Cu',points_mm=[[59.3875,12.575],[59.3875,14.3]]),
 dict(net='MOTION_3V3',layer='F.Cu',points_mm=[[57.1125,15.25],[56.5,15],[56.15,14.65],[55.6,14.65],[55.2,15.05]]),
 dict(net='/FAULT_N',layer='B.Cu',points_mm=[[57,14.9375],[57,15.45],port]),
]
checks=[]
for rt in routes:
 rt['width_mm']=.2;net=rt['net'];ly=rt['layer'];li=p.layers.index(ly)
 _,_,obs,al=p.geometry(net)
 bodies=unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly])
 lands=unary_union([s for (u,ll),s in c.shapes.items() if ll==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
 blocked=obs[li].union(bodies.buffer(.102).difference(lands.buffer(-.001)))
 allowed=al[li]
 if net!='/FAULT_N':
  blocked=blocked.union(Point(port).buffer(.555))
  allowed=allowed.difference(Point(port).buffer(.25+p.internal_clearance+.005+.102)).union(lands.buffer(-.102))
 for a,z in zip(rt['points_mm'],rt['points_mm'][1:]):
  line=LineString([a,z]);checks.append(dict(net=net,layer=ly,start=a,end=z,obstacle_hit=bool(line.intersects(blocked)),reference_allowed=bool(allowed.covers(line))))
for i,rt in enumerate(routes):
 for rz in routes[i+1:]:
  if rt['net']==rz['net'] or rt['layer']!=rz['layer']:continue
  distance=LineString(rt['points_mm']).distance(LineString(rz['points_mm']))
  checks.append(dict(kind='new_route_pair',nets=[rt['net'],rz['net']],layer=rt['layer'],distance_mm=distance,obstacle_hit=distance<.405,reference_allowed=True))
preflight=b/'R167C-route-preflight.json';assert not preflight.exists();preflight.write_text(json.dumps(dict(scope=__doc__,geometry_source_sha256=c.sha,checks=checks),indent=2)+'\n')
failed=[x for x in checks if x['obstacle_hit'] or not x['reference_allowed']]
print('failed',json.dumps(failed,indent=2));assert not failed
plan=json.loads((b/'R167A-plan.json').read_text());plan.update(revision='R167C',scope=__doc__,routes=routes,vias=[dict(net='/FAULT_N',position_mm=port,diameter_mm=.5,drill_mm=.3)],adoption_prohibited=True)
out.write_text(json.dumps(plan,indent=2)+'\n');print(out)

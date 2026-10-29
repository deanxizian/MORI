"""Read-only proposed R168C bends against R168B native geometry.

This bounded preflight does not replace native refill, DRC or electrical audit.
All same-net transfer exclusions are copied from B's actual audited islands.
"""
import ast,json,sys,itertools
from pathlib import Path
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R168-local-preflight.json';assert not out.exists()
c=Copper(str(b/'R168B/MORI_Interface_C3.kicad_pcb'))
audit=json.loads((b/'R168B-audit.json').read_text())
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
bodies={f.GetReference():fab(f) for f in c.footprints if f.GetLayer()==pcb.B_Cu}
act='/17 {slash} Actuator_Overcurrent/ACT_UV_N'
rows=[]
for x,bend in itertools.product([58.75,58.775,58.8],[59.9,59.925,59.95,59.975,60]):
 routes=[dict(net=act,width=.2,points=[[58.075,13.0625],[x-.3,13.0625],[x,13.3625],[x,15.4]]),
         dict(net=act,width=.2,points=[[x,14.775],[60.275,14.775]]),
         dict(net=act,width=.2,points=[[55.825,15.4],[55.825,15.6],[56.225,16],[57.7,16],[58.3,15.4],[x,15.4]]),
         dict(net='MOTION_3V3',width=.25,points=[[59.625,13.85],[bend,13.85],[bend+.325,13.525],[60.725,13.525]])]
 hits=[]
 for i,r in enumerate(routes):
  net=r['net'];stroke=LineString(r['points']).buffer(r['width']/2,resolution=64)
  lands=unary_union([s for (u,l),s in c.shapes.items() if l=='B.Cu' and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net]);outside=stroke.difference(lands)
  for ref,g in bodies.items():
   ar=outside.intersection(g).area
   if ar>1e-6:hits.append(dict(route=i,kind='same_face_body',reference=ref,area_mm2=ar))
  for k in c.keepouts:
   if k['tracks'] and 'B.Cu' in k['layers'] and stroke.intersection(k['shape']).area>1e-8:hits.append(dict(route=i,kind='native_guard',name=k['name']))
  for (u,l),g in c.shapes.items():
   if l!='B.Cu' or c.by_id[u].GetNetname()==net:continue
   if stroke.distance(g)<.199999:hits.append(dict(route=i,kind='foreign_clearance',uuid=u,net=c.by_id[u].GetNetname(),clearance_mm=stroke.distance(g)))
  transfer_rows=next(q['own_transfer_voids'] for q in audit['new_copper_review'] if q['net']==net and q['layer']=='B.Cu')
  voids=unary_union([reference_transfer_shape(c,c.by_id[q['uuid']],'In4.Cu').buffer(q['clearance_mm']+q['polygon_tolerance_mm']) for q in transfer_rows])
  missing=outside.difference(c.copper['GND','In4.Cu']).difference(voids)
  if missing.area>1e-6:hits.append(dict(route=i,kind='reference_gap',area_mm2=missing.area,bounds=list(missing.bounds)))
 for i,r in enumerate(routes):
  for j,s in enumerate(routes[i+1:],i+1):
   if r['net']==s['net']:continue
   d=LineString(r['points']).buffer(r['width']/2).distance(LineString(s['points']).buffer(s['width']/2))
   if d<.199999:hits.append(dict(route=i,kind='proposed_mutual_clearance',other_route=j,clearance_mm=d))
 rows.append(dict(x=x,cap_bend=bend,routes=routes,hits=hits))
out.write_text(json.dumps(dict(scope=__doc__,board_sha256=c.sha,rows=rows,adopted=False),indent=2)+'\n')
for r in rows:print(json.dumps(dict(x=r['x'],cap_bend=r['cap_bend'],hits=r['hits'])))

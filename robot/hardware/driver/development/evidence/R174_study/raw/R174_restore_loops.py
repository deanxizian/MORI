"""Sequential local loop restoration on a refilled full placement candidate.

All native clearances, original references and own-face Fab bodies constrain
the proposals. Existing same-net through vias can be used at their true lands;
no duplicate vias are inserted. Ground return uses existing vias only. Later
different-net paths avoid prior proposals and their reference anti-pads. These
are bounded proposals that still require a complete native build and audits.
"""
import ast,json,sys,time
from pathlib import Path
import numpy as np
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials');rev=sys.argv[1];out=b/(rev+'-restore-loops');out.mkdir(exist_ok=False)
p=Planner(str(b/rev/'MORI_Interface_C3.kicad_pcb'),.025,['B.Cu','F.Cu','In3.Cu','In2.Cu'],.2);c=p.c
p.xs=np.arange(40,55.001,p.grid);p.ys=np.arange(5,21.001,p.grid);p.xx,p.yy=np.meshgrid(p.xs,p.ys)
anchors=[a for a in c.anchors('GND') if all((uid(a),ly) in c.shapes and c.shapes[uid(a),ly].intersects(p.ground[ly]) for ly in p.ground)]
p.ground_near=mask(unary_union([Point(xy(a.GetPosition())).buffer(1.98) for a in anchors]),p.xx,p.yy,True)
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
bodies={ly:unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly]) for ly in ['B.Cu','F.Cu']}
pads={c.pad_name(q):q for q in c.pads}
tasks=[('ina_bypass_gnd','C1701.2','U1701.8'),('rlimit_direct_gnd','R1701.1','U1701.8'),('ina_limit','R1701.2','U1701.3'),('ina_bypass_vs','C1701.1','U1701.9'),('ina_input_minus','R1707.2','U1701.2'),('ina_input_plus','R1706.2','U1701.1'),('supervisor_ct','R1310.1','U1302.4'),('supervisor_vdd','C1304.1','U1302.5'),('supervisor_gnd','C1304.2','U1302.2'),('supervisor_sense','U1302.5','U1302.6')]
rows=[];newroutes=[];newvias=[];geometries={}
for name,an,bn in tasks:
 aa,bb=pads[an],pads[bn];net=aa.GetNetname();assert net==bb.GetNetname();start=time.monotonic()
 a=dict(pads=[an],layers={ly:c.shapes[uid(aa),ly] for ly in p.layers if (uid(aa),ly) in c.shapes})
 z=dict(pads=[bn],layers={ly:c.shapes[uid(bb),ly] for ly in p.layers if (uid(bb),ly) in c.shapes})
 if net not in geometries:geometries[net]=p.geometry(net)
 original_free,original_vf,original_blocked,original_allowed=geometries[net]
 blocked=list(original_blocked);allowed=list(original_allowed)
 for k,ly in enumerate(p.layers):
  extra=[LineString(r['points_mm']).buffer(r['width_mm']/2+.205+p.width/2) for r in newroutes if r['layer']==ly and r['net']!=net]
  extra += [Point(v['position_mm']).buffer(.25+.205+p.width/2) for v in newvias if v['net']!=net]
  if ly in bodies:
   lands=unary_union([s for (u,layer),s in c.shapes.items() if layer==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
   extra.append(bodies[ly].buffer(.102).difference(lands.buffer(-.001)))
  blocked[k]=unary_union([blocked[k]]+extra)
  holes=unary_union([Point(v['position_mm']).buffer(.652+p.width/2) for v in newvias if v['net'] not in ['GND',net]])
  allowed[k]=allowed[k].difference(holes)
 free=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(blocked,allowed)])
 via_block=[Point(v['position_mm']).buffer(.607) for v in newvias]
 via_block += [LineString(r['points_mm']).buffer(.657+r['width_mm']/2) for r in newroutes if r['net']!='GND']
 vf=original_vf & ~mask(unary_union(via_block),p.xx,p.yy)
 if net=='GND':vf=np.zeros_like(vf)
 existing=[v for v in c.vias if v.GetNetname()==net]
 existing_mask=mask(unary_union([Point(xy(v.GetPosition())).buffer(p.grid*.8) for v in existing]),p.xx,p.yy)
 vf |= existing_mask
 # First prefer direct same-face paths with no layer changes. Bounded fallback
 # can use F/B/In3 and the source In2 allow-list; no acceptance rules change.
 result=None;attempts=[]
 if set(a['layers']) & set(z['layers']):
  f=free.copy()
  for i,ly in enumerate(p.layers):
   if ly not in set(a['layers']) & set(z['layers']):f[i]=False
  result=p.solve(a,z,(f,np.zeros_like(vf),blocked,allowed),600000)
  attempts.append({k:v for k,v in result.items() if k not in ['routes','vias','activate_pth_layers']})
 if result is None or result['status']!='PROPOSAL':
  result=p.solve(a,z,(free,vf,blocked,allowed),1200000)
  attempts.append({k:v for k,v in result.items() if k not in ['routes','vias','activate_pth_layers']})
 reused=[]
 if result['status']=='PROPOSAL':
  actual=[]
  for v in result['vias']:
   hit=[old for old in existing if math.dist(v['position_mm'],xy(old.GetPosition()))<=p.grid*.8+1e-6]
   if hit:reused.append(dict(proposed_grid_mm=v['position_mm'],uuid=uid(hit[0]),native_position_mm=list(xy(hit[0].GetPosition()))))
   elif v['position_mm'] not in [q['position_mm'] for q in actual]:actual.append(v)
  result['vias']=actual
  assert not actual or net!='GND'
  newroutes.extend(dict(r,net=net) for r in result['routes']);newvias.extend(dict(v,net=net) for v in actual)
 row=dict(name=name,net=net,pads=[an,bn],result=result,attempts=attempts,reused_native_vias=reused,elapsed_seconds=time.monotonic()-start);rows.append(row)
 (out/'searches.json').write_text(json.dumps(dict(scope=__doc__,source_sha256=c.sha,grid_mm=p.grid,bounds_mm=[40,5,55,21],results=rows,routes=newroutes,vias=newvias,adopted=False),indent=2)+'\n')
 print(json.dumps(dict(name=name,result={k:v for k,v in result.items() if k not in ['routes','activate_pth_layers']},reused_native_vias=reused,elapsed_seconds=row['elapsed_seconds'])),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha

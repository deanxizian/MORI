"""Optimistic access screen for joint U301 poses, not accepted routing.

Use the refilled R180A preparation with the displaced U301 omitted from the
in-memory obstacle inventory only. Original 18 terminal/feed tracks have
already been explicitly released in R180A. All other copper, holes, body
guards, power reservations and reference masks remain. Proposed pads are
tested against reachable raster regions before restoring the new footprint
obstacles, supply and ground. This is a candidate filter, not a route proof;
absence of a raster connection is not proof that no physical design exists.
"""
import ast,hashlib,json,sys,time
from pathlib import Path
import numpy as np
from scipy import ndimage
from shapely import from_wkb
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
import plan_layered_route as routing

b=Path('robot/.state/c3-completion/trials')
out=b/'R180-pose-access';out.mkdir(exist_ok=False)
source=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
native=Copper(b/'R180A/MORI_Interface_C3.kicad_pcb')
omitted=next(f for f in native.footprints if f.GetReference()=='U301')
own={uid(p) for p in omitted.Pads()}
native.footprints=[f for f in native.footprints if f.GetReference()!='U301']
native.pads=[p for p in native.pads if uid(p) not in own]
native.items=native.pads+native.tracks
native.by_id={uid(o):o for o in native.items}
native.zones=[z for z in native.zones if not (z.GetIsRuleArea() and z.GetZoneName().startswith('BODY_U301_'))]
routing.Copper=lambda _:native
p=routing.Planner(native.path,.05,['B.Cu','F.Cu','In2.Cu','In3.Cu'],.2)
c=p.c
data=json.loads((b/'R180-supply-reservations/result.json').read_text())
assert data['source_sha256']==source.sha
assert len(data['roundtrip_checks'])==50 and all(q['status']=='PASS' for q in data['roundtrip_checks'])
reservations=[]
for row in data['files']:
 payload=(b/'R180-supply-reservations'/row['path']).read_bytes()
 assert hashlib.sha256(payload).hexdigest()==row['sha256']
 reservations.append((row['net'],row['layer'],from_wkb(payload)))
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
ground_strokes=[c.shapes[uid(t),c.board.GetLayerName(t.GetLayer())].intersection(p.ground[REFERENCE[c.board.GetLayerName(t.GetLayer())]]) for t in c.segments if t.GetNetname()=='GND' and c.board.GetLayerName(t.GetLayer()) in REFERENCE]
p.via_common=p.via_common.union(unary_union(ground_strokes).buffer(.657))
reaches={};diagnostics=[]
jobs=[('1','/01 {slash} Core/ARM_CLK','R302.1'),('3','/01 {slash} Core/ARMED','D1601.2'),('5','/03 {slash} Motor_Buses/DISARMED','U401.2'),('6','/CLR_N','R301.1'),('2','MOTION_3V3','R301.2')]
for pin,net,target in jobs:
 t0=time.monotonic();free,vf,blocked,allowed=p.geometry(net)
 reserved={ly:unary_union([g for n,l,g in reservations if l==ly and n!=net]) for ly in LAYERS}
 blocked=list(blocked)
 for i,ly in enumerate(p.layers):
  if ly in ['F.Cu','B.Cu']:
   bodies=unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly])
   lands=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
   blocked[i]=blocked[i].union(bodies.buffer(.102).difference(lands.buffer(-.001)))
  blocked[i]=blocked[i].union(reserved[ly].buffer((p.internal_clearance if ly.startswith('In') else .2)+.102))
 via_guard=unary_union([g.buffer((p.internal_clearance if ly.startswith('In') else .2)+.252) for ly,g in reserved.items()])
 vf &= ~routing.mask(via_guard,p.xx,p.yy)
 free=np.array([~routing.mask(ob,p.xx,p.yy)&routing.mask(al,p.xx,p.yy,True) for ob,al in zip(blocked,allowed)])
 labels=[];count=0
 for f in free:
  lab,n=ndimage.label(f,np.ones((3,3)));lab[lab>0]+=count;labels.append(lab);count+=n
 parent=list(range(count+1))
 def root(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 for i in range(len(p.layers)):
  for j in range(i+1,len(p.layers)):
   mm=vf&free[i]&free[j]
   if REFERENCE[p.layers[i]]!=REFERENCE[p.layers[j]]:mm &= p.ground_near
   for x,y in np.unique(np.column_stack([labels[i][mm],labels[j][mm]]),axis=0):parent[root(int(x))]=root(int(y))
 lookup=np.array([root(i) for i in range(count+1)])
 g=next(g for g in p.routing_groups(net) if target in g['pads']);roots=set()
 for i,ly in enumerate(p.layers):
  if ly in g['layers']:
   mm=routing.mask(g['layers'][ly].buffer(-.001),p.xx,p.yy,True)&free[i]
   roots.update(int(x) for x in np.unique(lookup[labels[i][mm]]) if x)
 reaches[pin]=np.isin(lookup[labels[0]],list(roots))&free[0]
 np.savez_compressed(out/(pin+'-reach.npz'),reachable=reaches[pin],xs=p.xs,ys=p.ys)
 diagnostics.append(dict(pin=pin,net=net,target=target,reachable_B_cells=int(reaches[pin].sum()),via_sites=int(vf.sum()),elapsed_seconds=time.monotonic()-t0))
 print(json.dumps(diagnostics[-1]),flush=True)
poses=json.loads((b/'R180-U301-pose-screen-wide.json').read_text())['candidates']
f=next(f for f in source.footprints if f.GetReference()=='U301');rows=[]
for pose in poses:
 part=pcb.FOOTPRINT(f);part.SetOrientationDegrees(pose['rotation_deg'])
 origin=xy(f.GetPosition());pos=pose['position_mm'];part.Move(pcb.VECTOR2I(round((pos[0]-origin[0])*1e6),round((pos[1]-origin[1])*1e6)))
 probes={}
 for pad in part.Pads():
  pin=pad.GetNumber();key='2' if pin in ['2','7','8'] else pin
  if key not in reaches:continue
  g=shape(pad,c.ids['B.Cu']).buffer(-.001)
  x0,y0,x1,y1=g.bounds
  xi=np.where((p.xs>=x0)&(p.xs<=x1))[0];yi=np.where((p.ys>=y0)&(p.ys<=y1))[0]
  xx,yy=np.meshgrid(p.xs[xi],p.ys[yi]);mm=routing.mask(g,xx,yy,True)
  probes[pin]=int((mm&reaches[key][np.ix_(yi,xi)]).sum())
 rows.append(dict(**pose,reachable_pin_cells=probes,signal_access_count=sum(probes[n]>0 for n in ['1','3','5','6']),supply_access_count=sum(probes[n]>0 for n in ['2','7','8'])))
rows.sort(key=lambda r:(-r['signal_access_count'],-r['supply_access_count'],r['displacement_mm']))
result=dict(scope=__doc__,source_sha256=source.sha,preparation_sha256=c.sha,omitted_for_diagnostic_only='U301 pad/body obstacles; source fills retained; no saved native mutation',diagnostics=diagnostics,poses=rows,adopted=False)
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(poses=len(rows),all_four=sum(r['signal_access_count']==4 for r in rows),top=rows[:12])),flush=True)
assert hashlib.sha256(Path(source.path).read_bytes()).hexdigest()==source.sha
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha

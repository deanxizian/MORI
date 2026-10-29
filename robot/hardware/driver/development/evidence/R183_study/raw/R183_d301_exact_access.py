"""Read-only exact D301 pose/access comparison on native R183A fills.

D301 is omitted only in the in-memory planning inventory, then every proposed
pad and native body/via guard is restored per pose. NRST and CLR are screened
independently, not simultaneously routed. All source power/reference criteria
remain mandatory. Nothing is adopted or saved to a native board here.
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
out=b/'R183-D301-exact-access';out.mkdir(exist_ok=False)
source=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
native=Copper(b/'R183A/MORI_Interface_C3.kicad_pcb')
omitted=[f for f in native.footprints if f.GetReference() in ['D301']]
own={uid(p) for f in omitted for p in f.Pads()}
native.footprints=[f for f in native.footprints if f.GetReference() not in ['D301']]
native.pads=[p for p in native.pads if uid(p) not in own]
native.items=native.pads+native.tracks
native.by_id={uid(o):o for o in native.items}
native.zones=[z for z in native.zones if not (z.GetIsRuleArea() and z.GetZoneName().startswith(('BODY_D301_',)))]
routing.Copper=lambda _:native
p=routing.Planner(native.path,.05,['B.Cu','F.Cu','In2.Cu','In3.Cu'],.2)
c=p.c
data=json.loads((b/'R182-supply-reservations/result.json').read_text())
assert data['source_sha256']==source.sha
assert len(data['roundtrip_checks'])==50 and all(q['status']=='PASS' for q in data['roundtrip_checks'])
reservations=[]
for row in data['files']:
 payload=(b/'R182-supply-reservations'/row['path']).read_bytes()
 assert hashlib.sha256(payload).hexdigest()==row['sha256']
 reservations.append((row['net'],row['layer'],from_wkb(payload)))
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
ground_strokes=[c.shapes[uid(t),c.board.GetLayerName(t.GetLayer())].intersection(p.ground[REFERENCE[c.board.GetLayerName(t.GetLayer())]]) for t in c.segments if t.GetNetname()=='GND' and c.board.GetLayerName(t.GetLayer()) in REFERENCE]
p.via_common=p.via_common.union(unary_union(ground_strokes).buffer(.657))
reaches={};diagnostics=[];jobgeometries={}
jobs=[('1','/01 {slash} Core/NRST','J105.7'),('2','/CLR_N','U1001.4')]
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
 jobgeometries[pin]=(free,vf,blocked,allowed,g)
 print(json.dumps(diagnostics[-1]),flush=True)

# Restore every proposed pad, same-face track guard and exact fixed-via-cutout
# shape before the access test. Signal nets are still independent: this is an
# exact obstacle raster screen, not proof that simultaneous routes can coexist.
from shapely.affinity import rotate,translate
poses=json.loads((b/'R183-D301-pose-screen.json').read_text())['candidates']
f=next(f for f in source.footprints if f.GetReference()=='D301')
origin=xy(f.GetPosition());a0=f.GetOrientationDegrees()
owned=[k for k in source.keepouts if k['name'].startswith('BODY_D301_')]
tg=unary_union([k['shape'] for k in owned if k['tracks']])
vg=unary_union([k['shape'] for k in owned if k['vias']]);fixedcut=tg.difference(vg)
samples=[];records=[]
for pose in poses:
 part=pcb.FOOTPRINT(f);part.SetOrientationDegrees(pose['rotation_deg']);pos=pose['position_mm']
 dx,dy=pos[0]-origin[0],pos[1]-origin[1]
 part.Move(pcb.VECTOR2I(round(dx*1e6),round(dy*1e6)))
 pads={pp.GetNumber():(pp.GetNetname(),shape(pp,c.ids['B.Cu'])) for pp in part.Pads()}
 guard=translate(rotate(tg,-(pose['rotation_deg']-a0),origin=origin),xoff=dx,yoff=dy)
 body=fab(part)
 vguard=unary_union([s.buffer(.457) for n,s in pads.values()]+[guard.difference(fixedcut).buffer(.257)])
 roi=unary_union([body,guard]+[s for n,s in pads.values()]).buffer(.7)
 x0,y0,x1,y1=roi.bounds;xi=np.where((p.xs>=x0)&(p.xs<=x1))[0];yi=np.where((p.ys>=y0)&(p.ys<=y1))[0]
 xx,yy=np.meshgrid(p.xs[xi],p.ys[yi])
 samples.append((part,pads,guard,body,vguard,xi,yi,xx,yy))
 records.append(dict(**pose,access={}))

for pin,net,target in jobs:
 t0=time.monotonic();free,vf,blocked,allowed,target_group=jobgeometries[pin]
 otherlabs=[];offset=50000
 for ff in free[1:]:
  lab,n=ndimage.label(ff,np.ones((3,3)));lab[lab>0]+=offset;otherlabs.append(lab);offset+=n
 vy,vx=np.where(vf);vxx,vyy=p.xs[vx],p.ys[vy]
 targets=[]
 for i,ly in enumerate(p.layers):
  target_mask=routing.mask(target_group['layers'][ly].buffer(-.001),p.xx,p.yy,True)&free[i] if ly in target_group['layers'] else np.zeros(p.xx.shape,bool)
  targets.append(np.where(target_mask))
 for idx,(part,pads,guard,body,vguard,xi,yi,xx,yy) in enumerate(samples):
  lands=unary_union([s for n,s in pads.values() if n==net])
  overlay=unary_union([s.buffer(.305) for n,s in pads.values() if n!=net]+[guard.buffer(.105),body.buffer(.102).difference(lands.buffer(-.001))])
  allowed_local=unary_union([allowed[0],lands.buffer(-.102)])
  bb=blocked[0].union(overlay)
  ff=free[0].copy()
  ff[np.ix_(yi,xi)]=~routing.mask(bb,xx,yy)&routing.mask(allowed_local,xx,yy,True)
  lab,n=ndimage.label(ff,np.ones((3,3)));assert n<50000
  labs=[lab]+otherlabs
  parent=np.arange(offset+1,dtype=np.int32)
  def root(i):
   while parent[i]!=i:parent[i]=parent[parent[i]];i=int(parent[i])
   return i
  valid=~routing.mask(vguard,vxx,vyy)
  # SMD pads and body guards affect B only; via exclusions apply to all layers.
  for i in range(len(p.layers)):
   for j in range(i+1,len(p.layers)):
    mm=valid&(labs[i][vy,vx]>0)&(labs[j][vy,vx]>0)
    if REFERENCE[p.layers[i]]!=REFERENCE[p.layers[j]]:mm &= p.ground_near[vy,vx]
    for aa,bb_ in np.unique(np.column_stack([labs[i][vy[mm],vx[mm]],labs[j][vy[mm],vx[mm]]]),axis=0):parent[root(int(aa))]=root(int(bb_))
  target_roots=set()
  for i,(ty,tx) in enumerate(targets):target_roots.update(root(int(k)) for k in np.unique(labs[i][ty,tx]) if k)
  probe_pins=[pin]
  for actual in probe_pins:
   pad=pads[actual][1].buffer(-.001)
   mm=routing.mask(pad,xx,yy,True)&ff[np.ix_(yi,xi)]
   labels=np.unique(lab[np.ix_(yi,xi)][mm]);accessible=any(root(int(k)) in target_roots for k in labels if k)
   records[idx]['access'][actual]=dict(accessible=accessible,start_cells=int(mm.sum()),start_regions=len(labels))
  if idx%150==0:print(json.dumps(dict(pin=pin,poses=idx,seconds=time.monotonic()-t0)),flush=True)
 print(json.dumps(dict(pin=pin,poses=len(records),seconds=time.monotonic()-t0)),flush=True)

for row in records:
 row['signal_access_count']=sum(row['access'][n]['accessible'] for n in ['1','2'])
records.sort(key=lambda r:(-r['signal_access_count'],r['target_gaps_mm']['1'],r['displacement_mm']))
result=dict(scope=__doc__,source_sha256=source.sha,preparation_sha256=c.sha,diagnostics=diagnostics,poses=records,adopted=False)
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(poses=len(records),all_two=sum(r['signal_access_count']==2 for r in records),top=records[:12])),flush=True)
assert hashlib.sha256(Path(source.path).read_bytes()).hexdigest()==source.sha
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha

"""Locate precise movable copper dependencies for the isolated R1304 RAW terminal.

Read-only; native pad/keepout conflicts are not waived. The output proposes
dependencies to replan, not legal holes or completed routing.
"""
import sys,json,math
from pathlib import Path
from scipy import ndimage
from shapely.prepared import prep
b=Path('robot/.state/c3-completion/trials')
s=(b/'R189_route.py').read_text().split('start=time.monotonic();result=')[0]
exec(compile(s,'source_geometry','exec'))
assert c.sha=='b6da4de8fc7341e01971efb11f1720f6cdf68364958675948ef76ef03830722a'
lab,n=ndimage.label(free[0],np.ones((3,3)))
pad=next(o for o in c.pads if c.pad_name(o)=='R1304.2')
lands=c.shapes[uid(pad),'B.Cu'];start=mask(lands.buffer(-.001),p.xx,p.yy,True)&free[0]
labels=set(int(x) for x in np.unique(lab[start]) if x)
reachable=np.isin(lab,list(labels))&free[0]
fixed=unary_union([g.buffer(.457) for (u,l),g in c.shapes.items() if isinstance(c.by_id[u],pcb.PAD)]+[k['shape'].buffer(.257) for k in c.keepouts if k['vias']])
fixed=prep(fixed)
physical={}
for (u,ly),g in c.shapes.items():
 if not isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()!=net:
  physical.setdefault(u,[]).append(g.buffer(.457))
physical={u:prep(unary_union(gs)) for u,gs in physical.items()}
references={uid(t):prep(c.shapes[uid(t),c.board.GetLayerName(t.GetLayer())].intersection(p.ground[REFERENCE[c.board.GetLayerName(t.GetLayer())]]).buffer(.657))
 for t in c.segments if c.board.GetLayerName(t.GetLayer()) in REFERENCE}
power=[(q['net'],q['layer'],prep(from_wkb((rdir/q['path']).read_bytes()).buffer((p.internal_clearance if q['layer'].startswith('In') else .2)+.252))) for q in data['files'] if q['net']!=net]
rows=[]
near=ndimage.distance_transform_edt(~reachable)*p.grid<=1.5
fixed_routes=prep(unary_union([g.buffer(.305) for (u,l),g in c.shapes.items() if l=='B.Cu' and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()!=net]+[k['shape'].buffer(.105) for k in c.keepouts if k['tracks'] and 'B.Cu' in k['layers']]+[fab(f).buffer(.102).difference(lands.buffer(-.001)) for f in c.footprints if f.GetLayer()==pcb.B_Cu]))
def paths(a,z):
 dx,dy=z[0]-a[0],z[1]-a[1];m=min(abs(dx),abs(dy));sx=1 if dx>=0 else -1;sy=1 if dy>=0 else -1
 for mid in [(a[0]+sx*m,a[1]+sy*m),(z[0]-sx*m,z[1]-sy*m)]:
  pts=[a]
  if math.dist(a,mid)>1e-8 and math.dist(mid,z)>1e-8:pts.append(mid)
  pts.append(z);yield pts
for iy,ix in zip(*np.where(near)):
 if ix%2 or iy%2:continue
 pos=(float(p.xs[ix]),float(p.ys[iy]));pt=Point(pos)
 if fixed.intersects(pt):continue
 routes=[]
 for path in paths(xy(pad.GetPosition()),pos):
  line=LineString(path)
  if fixed_routes.intersects(line):continue
  deps=[u for (u,l),g in c.shapes.items() if l=='B.Cu' and not isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()!=net and line.intersects(g.buffer(.305))]
  routes.append((len(deps),line.length,path,deps))
 if not routes:continue
 _,_,path,route_deps=min(routes)
 phys=[u for u,g in physical.items() if g.intersects(pt)]
 phys=sorted(set(phys)|set(route_deps))
 refs=[u for u,g in references.items() if g.intersects(pt)]
 pw=[dict(net=n,layer=l) for n,l,g in power if g.intersects(pt)]
 changed=set(phys)|set(refs)
 rows.append(dict(position_mm=[round(x,6) for x in pos],B_escape_mm=path,physical=phys,reference=refs,power_reservations=pw,
  dependency_count=len(changed),distance_to_pad_mm=math.dist(pos,xy(pad.GetPosition())),
  items=[dict(uuid=u,net=c.by_id[u].GetNetname(),kind=c.by_id[u].GetClass(),
   layer=c.board.GetLayerName(c.by_id[u].GetLayer()),position_mm=list(xy(c.by_id[u].GetPosition()))) for u in sorted(changed)]))
rows.sort(key=lambda r:(len(r['power_reservations']),r['dependency_count'],r['distance_to_pad_mm']))
chosen=[]
for r in rows:
 if any(math.dist(r['position_mm'],x['position_mm'])<.2 for x in chosen):continue
 chosen.append(r)
 if len(chosen)==12:break
(out/'prospective_dependencies.json').write_text(json.dumps(dict(scope=__doc__,source_sha256=c.sha,reachable_B_cells=int(reachable.sum()),
 native_pad_and_guard_clear_sites=len(rows),extension_beyond_existing_region_mm=1.5,ranked=rows,representative=chosen,adopted=False),indent=2)+'\n')
print(json.dumps(dict(count=len(rows),representative=chosen),indent=2))
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha

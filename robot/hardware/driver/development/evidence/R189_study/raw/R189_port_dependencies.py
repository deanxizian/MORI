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
for iy,ix in zip(*np.where(reachable)):
 if ix%2 or iy%2:continue
 pos=(float(p.xs[ix]),float(p.ys[iy]));pt=Point(pos)
 if fixed.intersects(pt):continue
 phys=[u for u,g in physical.items() if g.intersects(pt)]
 refs=[u for u,g in references.items() if g.intersects(pt)]
 pw=[dict(net=n,layer=l) for n,l,g in power if g.intersects(pt)]
 changed=set(phys)|set(refs)
 rows.append(dict(position_mm=[round(x,6) for x in pos],physical=phys,reference=refs,power_reservations=pw,
  dependency_count=len(changed),distance_to_pad_mm=math.dist(pos,xy(pad.GetPosition())),
  items=[dict(uuid=u,net=c.by_id[u].GetNetname(),kind=c.by_id[u].GetClass(),
   layer=c.board.GetLayerName(c.by_id[u].GetLayer()),position_mm=list(xy(c.by_id[u].GetPosition()))) for u in sorted(changed)]))
rows.sort(key=lambda r:(len(r['power_reservations']),r['dependency_count'],r['distance_to_pad_mm']))
chosen=[]
for r in rows:
 if any(math.dist(r['position_mm'],x['position_mm'])<.2 for x in chosen):continue
 chosen.append(r)
 if len(chosen)==12:break
(out/'dependencies.json').write_text(json.dumps(dict(scope=__doc__,source_sha256=c.sha,reachable_B_cells=int(reachable.sum()),
 native_pad_and_guard_clear_sites=len(rows),ranked=rows,representative=chosen,adopted=False),indent=2)+'\n')
print(json.dumps(dict(count=len(rows),representative=chosen),indent=2))
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha

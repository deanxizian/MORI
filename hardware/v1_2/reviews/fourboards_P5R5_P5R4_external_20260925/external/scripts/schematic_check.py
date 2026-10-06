from analyze import *
from shapely.geometry import Point,LineString
import networkx as nx
OUT=Path('/mnt/data/latest_review_work/evidence')
def norm(s):return s.lstrip('/')
def check(nm,rev):
 b,d=get_board(nm,rev); s=parse(f'/mnt/data/MORI_{nm}_{rev}.kicad_sch');lib={x[1]:x for x in sub(one(s,'lib_symbols'),'symbol')};ps=[];pts=set();wires=[];labels=[]
 for w in sub(s,'wire'):
  pp=[tuple(p[1:]) for p in one(w,'pts')[1:]];pts.update(pp);wires.append(pp)
 for l in sub(s,'label')+sub(s,'global_label'):
  xy=tuple(one(l,'at')[1:3]);pts.add(xy);labels.append((l[1],xy,l.line))
 for j in sub(s,'junction'):pts.add(tuple(one(j,'at')[1:3]))
 for x in sub(s,'symbol'):
  name=val(x,'lib_id');props={p[1]:p[2] for p in sub(x,'property')};ref=props['Reference'];base=one(x,'at')[1:];angle=base[2] if len(base)>2 else 0
  for sym in sub(lib[name],'symbol'):
   for p in sub(sym,'pin'):
    a=one(p,'at')[1:];dx,dy=rot(a[0],-a[1],angle);xy=(round(base[0]+dx,6),round(base[1]+dy,6));num=str(val(p,'number'))
    ps.append({'ref':ref,'num':num,'name':val(p,'name'),'xy':xy,'line':x.line});pts.add(xy)
 for n in sub(s,'no_connect'):pts.add(tuple(one(n,'at')[1:3]))
 g=nx.Graph();g.add_nodes_from(pts)
 for pp in wires:
  line=LineString(pp);inline=[p for p in pts if line.distance(Point(p))<1e-5]
  for p in inline[1:]:g.add_edge(inline[0],p)
 labs=collections.defaultdict(list)
 for name,xy,ln in labels:labs[name].append(xy)
 for coords in labs.values():
  for p in coords[1:]:g.add_edge(coords[0],p)
 components=list(nx.connected_components(g));idx={p:i for i,c in enumerate(components) for p in c};nets=collections.defaultdict(set)
 for name,xy,ln in labels:nets[idx[xy]].add(name)
 nc={tuple(one(x,'at')[1:3]) for x in sub(s,'no_connect')}
 errors=[];pcbpins={(r,p['num']):p['net'] for r,f in d['footprints'].items() for p in f['pads'] if p['num']};rows=[]
 for p in ps:
  if p['ref'].startswith('#'):continue
  k=(p['ref'],p['num']);ns=nets[idx[p['xy']]];pnet=pcbpins.get(k,'MISSING');p['schematic_nets']=sorted(ns);p['pcb_net']=pnet;p['nc']=p['xy'] in nc
  if ns:ok=norm(pnet) in ns
  else:ok=p['nc'] and pnet.startswith('unconnected')
  p['ok']=ok
  if not ok:errors.append(p)
  rows.append(p)
 result={'name':nm,'physical_pin_numbers_checked':len(rows),'errors':errors,'pins':rows,'ambiguous_labels':[sorted(ns) for ns in nets.values() if len(ns)>1]}
 (OUT/f'{nm}_schematic_check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));return result
if __name__=='__main__':
 for nm,rev in [('power','P5R5'),('motion','P5R5'),('imu','P5R4'),('rear','P5R4')]:
  r=check(nm,rev);print(nm,rev,r['physical_pin_numbers_checked'],'errors',r['errors'],'ambiguous',r['ambiguous_labels'])

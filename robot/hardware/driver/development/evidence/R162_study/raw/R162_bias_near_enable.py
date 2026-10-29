"""Search bias-pair placements near the actual retained ENABLE group.

Read-only nominal geometry with exact native pads/courtyards, fixed holes,
all fixed vias/tracks and mounted-face body avoidance. Only short, explicitly
referenced B-face connections are ranked. Native refill and full circuit
regression are still required; a placement result is not adoption.
"""
import ast,json,math,sys
from pathlib import Path
from shapely.affinity import translate
from shapely.geometry import box
from shapely.ops import polygonize,nearest_points
from shapely.prepared import prep
from scipy.spatial import cKDTree
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_existing_copper import groups
b=Path('robot/.state/c3-completion/trials');out=b/'R162-bias-near-enable.json';assert not out.exists()
c=Copper(str(b/'R162D/MORI_Interface_C3.kicad_pcb'));fs={f.GetReference():f for f in c.footprints}
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
moving={'R1311','R1312'};mid='Net-(R1311-~-Pad1)';enable='/HEAD_UV_ENABLE'
fixed=[f for f in c.footprints if f.GetReference() not in moving]
for f in fixed:f.BuildCourtyardCaches()
fixed_cy=prep(unary_union([polyset(f.GetCourtyard(pcb.B_CrtYd)) for f in fixed if f.GetLayer()==pcb.B_Cu]).buffer(.005))
fixed_bodies=unary_union([fab(f) for f in fixed if f.GetLayer()==pcb.B_Cu])
fixed_pads=[p for f in fixed for p in f.Pads() if p.IsOnLayer(pcb.B_Cu)]
pth_court=prep(unary_union([shape(p,pcb.B_Cu) for p in fixed_pads if p.GetAttribute()==pcb.PAD_ATTRIB_PTH]).buffer(.005))
tracks=[t for t in c.tracks if t.GetNetname()!=mid and (uid(t),'B.Cu') in c.shapes]
holes=unary_union([Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6) for v in c.vias]+[Point(xy(p.GetPosition())).buffer(max(xy(p.GetDrillSize()))/2) for p in c.pads if max(xy(p.GetDrillSize()))>0])
track_shapes=unary_union([c.shapes[(uid(t),'B.Cu')] for t in tracks])
body_guard=prep(track_shapes.union(holes))
pad_guards={}
for net in [mid,enable,'GND']:
 foreign=[shape(p,pcb.B_Cu) for p in fixed_pads if p.GetNetname()!=net]
 foreign += [c.shapes[(uid(t),'B.Cu')] for t in tracks if t.GetNetname()!=net or isinstance(t,pcb.PCB_VIA)]
 pad_guards[net]=prep(unary_union(foreign).buffer(.202).union(holes.buffer(.302)))
route_guards={};lands={}
for net in [mid,enable]:
 lands[net]=unary_union([shape(p,pcb.B_Cu) for p in fixed_pads if p.GetNetname()==net])
 foreign=[shape(p,pcb.B_Cu) for p in fixed_pads if p.GetNetname()!=net]+[c.shapes[(uid(t),'B.Cu')] for t in tracks if t.GetNetname()!=net]
 route_guards[net]=prep(unary_union(foreign).buffer(.302).union(holes.buffer(.402)))
ref=c.copper[('GND','In4.Cu')]
target=next(g for g in groups(c,enable) if 'Q1701.1' in g['pads'])['layers']['B.Cu']
target_lines=[]
for t in c.segments:
 if t.GetNetname()==enable and c.board.GetLayerName(t.GetLayer())=='B.Cu' and c.shapes[(uid(t),'B.Cu')].intersects(target):
  target_lines.append(LineString([xy(t.GetStart()),xy(t.GetEnd())]))
target_points=[xy(p.GetPosition()) for p in fixed_pads if p.GetNetname()==enable and shape(p,pcb.B_Cu).intersects(target)]
def paths(a,z):
 for ps in [[a,z],[a,(a[0],z[1]),z],[a,(z[0],a[1]),z]]:
  ps=[p for i,p in enumerate(ps) if not i or p!=ps[i-1]]
  if len(ps)>1:yield ps
def legal_route(net,ps,own_lands,own_bodies,foreign_new):
 line=LineString(ps)
 if route_guards[net].intersects(line) or line.distance(foreign_new)<.302:return False
 copper=line.buffer(.1);outside=copper.difference(lands[net].union(own_lands))
 if outside.intersection(fixed_bodies.union(own_bodies)).area>1e-6:return False
 if outside.difference(ref).area>1e-6:return False
 return True
domains={};geometry={};enable_paths={};counts={}
grid={(ix/5,iy/5) for xr,yr in [((255,307),(47,68)),((315,345),(24,48))] for ix in range(xr[0],xr[1]+1) for iy in range(yr[0],yr[1]+1)}
for name in ['R1311','R1312']:
 rows=[];tested=0
 for angle in [0,90,180,-90]:
  f=pcb.FOOTPRINT(fs[name]);f.SetPosition(pcb.VECTOR2I(0,0));f.SetOrientationDegrees(angle);f.BuildCourtyardCaches()
  cy0=polyset(f.GetCourtyard(pcb.B_CrtYd));assert not cy0.is_empty
  body0=fab(f);pad0={p.GetNumber():(p.GetNetname(),shape(p,pcb.B_Cu),xy(p.GetPosition())) for p in f.Pads()}
  for x,y in sorted(grid):
   tested+=1;cy=translate(cy0,xoff=x,yoff=y)
   if not box(.505,.505,69.495,34.495).covers(cy) or fixed_cy.intersects(cy) or pth_court.intersects(cy):continue
   body=translate(body0,xoff=x,yoff=y)
   if body_guard.intersects(body):continue
   pads={n:(net,translate(sh,xoff=x,yoff=y),(x+pos[0],y+pos[1])) for n,(net,sh,pos) in pad0.items()}
   if any(pad_guards[net].intersects(sh) for net,sh,_ in pads.values()):continue
   ident=f'{name}:{angle}:{x}:{y}';ep=[]
   if name=='R1311':
    pos=pads['2'][2];points=target_points+[tuple(nearest_points(Point(pos),line)[1].coords[0]) for line in target_lines]
    for z in points:
     if math.dist(pos,z)>7:continue
     for ps in paths(pos,z):
      if legal_route(enable,ps,pads['2'][1],body,pads['1'][1]):ep.append((LineString(ps).length,ps))
    if not ep:continue
    enable_paths[ident]=sorted(ep,key=lambda r:r[0])[:4]
   row={'id':ident,'reference':name,'position_mm':[x,y],'rotation_deg':angle,'pads':{n:list(pos) for n,(_,_,pos) in pads.items()}}
   rows.append(row);geometry[ident]=(cy,body,pads)
 domains[name]=rows;counts[name]={'tested':tested,'eligible':len(rows)};print(json.dumps({name:counts[name]}),flush=True)
pairs=[];tested_pairs=0
if domains['R1311'] and domains['R1312']:
 tree=cKDTree([r['pads']['2'] for r in domains['R1312']])
 for a in domains['R1311']:
  cy1,bo1,pa=geometry[a['id']]
  for qi in tree.query_ball_point(pa['1'][2],4):
   z=domains['R1312'][qi];cy2,bo2,pz=geometry[z['id']]
   if cy1.intersects(cy2) or any(n!=m and s.distance(t)<.202 for n,s,_ in pa.values() for m,t,_ in pz.values()):continue
   tested_pairs+=1;foreign=pa['2'][1].union(pz['1'][1]);body=bo1.union(bo2);mid_lands=pa['1'][1].union(pz['2'][1])
   for ps in paths(pa['1'][2],pz['2'][2]):
    if not legal_route(mid,ps,mid_lands,body,foreign):continue
    for elen,eps in enable_paths[a['id']]:
     if not legal_route(enable,eps,pa['2'][1],body,mid_lands.union(pz['1'][1])) or LineString(eps).distance(LineString(ps))<.402:continue
     pairs.append({'score':LineString(ps).length+elen,'poses':[a,z],'common_node_route_B_mm':ps,'enable_route_B_mm':eps,'mid_length_mm':LineString(ps).length,'enable_length_mm':elen})
pairs.sort(key=lambda r:r['score'])
out.write_text(json.dumps({'scope':__doc__,'source_sha256':c.sha,'grid_mm':.2,'counts':counts,'tested_pairs':tested_pairs,'pair_count':len(pairs),'best_pairs':pairs[:40],'adopted':False,'native_verification_required':True},indent=2)+'\n')
print(json.dumps({'pairs':len(pairs),'best':pairs[:1]}),flush=True)

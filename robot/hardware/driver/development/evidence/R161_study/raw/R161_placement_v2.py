"""Corrected detector/Schottky pose screen, including PTH-in-courtyard.

All fixed pads and ground vias are included. Other existing copper conflicts
are reported, never accepted as routed. This is not an adoption gate.
"""
import ast,json,math,sys
from pathlib import Path
from shapely.affinity import translate
from shapely.geometry import box
from shapely.ops import polygonize
from shapely.prepared import prep
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R161-placement-v2.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='bf719a717ffba2a1468126f6a71a1cc3703980fedf647caf8af07c1a9cef62a0'
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
fs={f.GetReference():f for f in c.footprints}
moving={'U1301','D1803','C1301','C1302','C1303','R1303','R1307','R1502','R1311','R1312','R1504'}
fixed=[f for f in c.footprints if f.GetReference() not in moving]
fixed_cy=prep(unary_union([polyset(f.GetCourtyard(pcb.B_CrtYd)) for f in fixed if f.GetLayer()==pcb.B_Cu]).buffer(.01))
pth=[p for p in c.pads if p.GetAttribute()==pcb.PAD_ATTRIB_PTH]
pth_land=prep(unary_union([shape(p,pcb.B_Cu) for p in pth]).buffer(.005))
ground=[v for v in c.vias if v.GetNetname()=='GND']
ground_cu=unary_union([shape(v,pcb.B_Cu) for v in ground])
holes=unary_union([Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6) for v in ground]+
 [Point(xy(p.GetPosition())).buffer(max(xy(p.GetDrillSize()))/2) for p in c.pads if max(xy(p.GetDrillSize()))>0])
body_guard=prep(ground_cu.union(holes));hole_guard=prep(holes.buffer(.302))
fixed_pads=[p for f in fixed for p in f.Pads() if p.IsOnLayer(pcb.B_Cu)]
pad_guards={}
domains={};geometries={};stats={};witnesses=[]
for ref,xs,ys in [('D1803',range(640,676),range(185,231)),('U1301',range(580,686),range(190,318))]:
 source=fs[ref];rows=[];counts={k:0 for k in ['poses','court_fixed','pth_court','body_hole','pad_edge','pad_clearance']}
 for angle in [0,90,180,-90]:
  f=pcb.FOOTPRINT(source);f.SetPosition(pcb.VECTOR2I(0,0));f.SetOrientationDegrees(angle);f.BuildCourtyardCaches()
  cy0=polyset(f.GetCourtyard(pcb.B_CrtYd));assert not cy0.is_empty
  body0=fab(f);pads0=[]
  for p in f.Pads():
   net=p.GetNetname();pads0.append((p.GetNumber(),net,shape(p,pcb.B_Cu),xy(p.GetPosition())))
   if net not in pad_guards:
    foreign=unary_union([shape(q,pcb.B_Cu) for q in fixed_pads if q.GetNetname()!=net])
    pad_guards[net]=prep(ground_cu.union(foreign).buffer(.202))
  poses={(ix/10,iy/10) for ix in xs for iy in ys}
  if ref=='U1301':poses|={(68.225,y/100) for y in range(2500,2801,5)}
  if abs(source.GetOrientationDegrees()-angle)<1e-6:poses.add(xy(source.GetPosition()))
  for x,y in sorted(poses):
   counts['poses']+=1;cy=translate(cy0,xoff=x,yoff=y)
   if fixed_cy.intersects(cy):counts['court_fixed']+=1;continue
   if pth_land.intersects(cy):counts['pth_court']+=1;continue
   body=translate(body0,xoff=x,yoff=y)
   if body_guard.intersects(body) or not box(0,0,70,35).covers(body):counts['body_hole']+=1;continue
   ps=[(n,net,translate(sh,xoff=x,yoff=y),(x+pos[0],y+pos[1])) for n,net,sh,pos in pads0]
   if any(not box(.505,.505,69.495,34.495).covers(sh) for _,_,sh,_ in ps):counts['pad_edge']+=1;continue
   if any(pad_guards[net].intersects(sh) or hole_guard.intersects(sh) for _,net,sh,_ in ps):counts['pad_clearance']+=1;continue
   conflicts=[]
   for t in c.tracks:
    sh=c.shapes.get((uid(t),'B.Cu'))
    if sh is None:continue
    via=isinstance(t,pcb.PCB_VIA)
    body_hit=body.intersection(sh).area>1e-6
    pad_hit=any((net!=t.GetNetname() or via) and land.distance(sh)<.202 for _,net,land,_ in ps)
    if body_hit or pad_hit:conflicts.append({'uuid':uid(t),'net':t.GetNetname(),'via':via,'body':body_hit,'pad':pad_hit})
   assert not any(r['via'] and r['net']=='GND' for r in conflicts)
   ident=f'{ref}:{angle}:{x}:{y}'
   row={'id':ident,'reference':ref,'position_mm':[x,y],'rotation_deg':angle,'court_bounds_mm':list(cy.bounds),
        'pending_copper_conflicts':conflicts,'pads':{n:{'net':net,'position_mm':list(pos)} for n,net,_,pos in ps},
        'old_to_new_mm':math.dist((x,y),xy(source.GetPosition()))}
   rows.append(row);geometries[ident]=(cy,body,ps)
 rows.sort(key=lambda r:(sum(4 if v['via'] else 1 for v in r['pending_copper_conflicts']),r['old_to_new_mm']))
 domains[ref]=rows;stats[ref]={**counts,'valid_poses':len(rows)}
 print(json.dumps({'ref':ref,'statistics':stats[ref],'first':rows[:2]}),flush=True)
pairs=[]
for d in domains['D1803']:
 dc,db,dp=geometries[d['id']]
 for u in domains['U1301']:
  uc,ub,up=geometries[u['id']]
  if dc.distance(uc)<.01:continue
  if any(dn!=un and ds.distance(us)<.202 for _,dn,ds,_ in dp for _,un,us,_ in up):continue
  conflicts={r['uuid']:r for row in [d,u] for r in row['pending_copper_conflicts']}
  score=sum(4 if r['via'] else 1 for r in conflicts.values())+.2*d['old_to_new_mm']+.05*u['old_to_new_mm']
  pairs.append({'score':score,'D1803':d['id'],'U1301':u['id'],'pending_count':len(conflicts)})
pairs.sort(key=lambda r:r['score'])
# Known R161A witness: PTH courtyard collision must be rejected before routing.
df=pcb.FOOTPRINT(fs['D1803']);df.SetPosition(pcb.VECTOR2I(64400000,21300000));df.SetOrientationDegrees(90);df.BuildCourtyardCaches()
assert pth_land.intersects(polyset(df.GetCourtyard(pcb.B_CrtYd)))
out.write_text(json.dumps({'scope':__doc__,'source_sha256':c.sha,'statistics':stats,'movable_refs':sorted(moving),
 'candidate_domains':domains,'pair_count':len(pairs),'best_pairs':pairs[:100],
 'known_R161A_PTH_collision_detected':True,'native_verification_required':True,'adopted':False},indent=2)+'\n')
print(json.dumps({'pairs':len(pairs),'best_pairs':pairs[:5]}),flush=True)

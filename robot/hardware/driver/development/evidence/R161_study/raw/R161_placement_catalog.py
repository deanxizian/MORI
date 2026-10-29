"""Joint native placement and first-escape screen for the detector/clamp region.

D1803 is the B340LA Schottky clamp, not the neighboring D1802 TVS. All fixed
mechanical interfaces and source ground vias stay fixed. Old signal copper is
reported as rerouting work; this is not a native DRC or routability acceptance.
"""
import ast,json,math,sys
from pathlib import Path
from shapely.affinity import translate
from shapely.geometry import box
from shapely.ops import polygonize
from shapely.prepared import prep
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R161-placement-catalog.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='bf719a717ffba2a1468126f6a71a1cc3703980fedf647caf8af07c1a9cef62a0'
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
fps={f.GetReference():f for f in c.footprints}
movable={'U1301','D1803','C1301','C1302','C1303','R1303','R1307','R1502','R1311','R1312','R1504'}
fixed_cy=prep(unary_union([polyset(f.GetCourtyard(pcb.B_CrtYd)) for f in c.footprints if f.GetLayer()==pcb.B_Cu and f.GetReference() not in movable]))
ground=[v for v in c.vias if v.GetNetname()=='GND']
pth=[p for p in c.pads if max(xy(p.GetDrillSize()))>0]
ground_annuli=unary_union([shape(v,pcb.B_Cu) for v in ground])
holes=unary_union([Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6) for v in ground]+[Point(xy(p.GetPosition())).buffer(max(xy(p.GetDrillSize()))/2) for p in pth])
body_holes=prep(unary_union([ground_annuli,holes]));drill_guard=prep(holes.buffer(.3005))
fixed_pads=[p for p in c.pads if p.IsOnLayer(pcb.B_Cu) and p.GetParentFootprint().GetReference() not in movable]
pad_guards={};escape_guards={};domains={};stats={}
for ref,xr,yr,width,escape in [('D1803',(620,680),(175,235),.8,1.25),('U1301',(590,680),(190,300),.2,1.0)]:
 source=fps[ref];rows=[];counts={k:0 for k in ['poses','courtyard','body_hole','pad_clearance','outward_escape']}
 for angle in [0,90,180,-90]:
  f=pcb.FOOTPRINT(source);f.SetPosition(pcb.VECTOR2I(0,0));f.SetOrientationDegrees(angle)
  cy0=polyset(f.GetCourtyard(pcb.B_CrtYd));body0=fab(f)
  pads0=[]
  for p in f.Pads():
   net=p.GetNetname();pos=xy(p.GetPosition());ps=shape(p,pcb.B_Cu)
   axis=0 if abs(pos[0])>abs(pos[1]) else 1;direction=1 if pos[axis]>0 else -1
   end=list(pos);end[axis]+=direction*escape
   pads0.append((p.GetNumber(),net,ps,pos,LineString([pos,end])))
   key=(net,width)
   if key not in escape_guards:
    foreign_pads=unary_union([shape(p,pcb.B_Cu) for p in fixed_pads if p.GetNetname()!=net])
    pad_guards[key]=prep(unary_union([ground_annuli.buffer(.2005),foreign_pads.buffer(.2005)]))
    foreign_ground=ground_annuli if net!='GND' else GeometryCollection()
    foreign_holes=unary_union([Point(xy(p.GetPosition())).buffer(max(xy(p.GetDrillSize()))/2) for p in pth if p.GetNetname()!=net]+
       ([Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6) for v in ground] if net!='GND' else []))
    escape_guards[key]=prep(unary_union([foreign_pads.buffer(.205+width/2),foreign_ground.buffer(.205+width/2),foreign_holes.buffer(.305+width/2)]))
  for ix in range(xr[0],xr[1]+1,2):
   x=ix/10
   for iy in range(yr[0],yr[1]+1,2):
    y=iy/10;counts['poses']+=1;cy=translate(cy0,xoff=x,yoff=y)
    if not box(.35,.35,69.65,34.65).covers(cy) or fixed_cy.intersects(cy):counts['courtyard']+=1;continue
    body=translate(body0,xoff=x,yoff=y)
    if body_holes.intersects(body):counts['body_hole']+=1;continue
    ps=[(number,net,translate(sh,xoff=x,yoff=y),(x+pos[0],y+pos[1]),translate(line,xoff=x,yoff=y)) for number,net,sh,pos,line in pads0]
    if any(pad_guards[net,width].intersects(sh) or drill_guard.intersects(sh) for _,net,sh,_,_ in ps):counts['pad_clearance']+=1;continue
    if any(escape_guards[net,width].intersects(line) for _,net,_,_,line in ps):counts['outward_escape']+=1;continue
    conflicts=[]
    for t in c.tracks:
     sh=c.shapes.get((uid(t),'B.Cu'))
     if sh is None:continue
     is_via=isinstance(t,pcb.PCB_VIA)
     bad_body=sh.intersection(body).area>1e-6
     bad_pad=any((net!=t.GetNetname() or is_via) and land.distance(sh)<.2005 for _,net,land,_,_ in ps)
     bad_escape=any(net!=t.GetNetname() and sh.distance(line)<.205+width/2 for _,net,_,_,line in ps)
     if bad_body or bad_pad or bad_escape:conflicts.append({'uuid':uid(t),'net':t.GetNetname(),'via':is_via,'body':bad_body,'pad':bad_pad,'escape':bad_escape})
    assert not any(r['via'] and r['net']=='GND' for r in conflicts)
    rows.append({'reference':ref,'position_mm':[x,y],'rotation_deg':angle,'courtyard_bounds_mm':list(cy.bounds),
      'pads':[{'number':n,'net':net,'position_mm':list(pos)} for n,net,_,pos,_ in ps],
      'fixed_object_first_escape_screen':'PASS','pending_copper_conflicts':conflicts,
      'old_to_new_mm':math.dist((x,y),xy(source.GetPosition()))})
 rows.sort(key=lambda r:(sum(2 if v['via'] else 1 for v in r['pending_copper_conflicts']),r['old_to_new_mm']))
 domains[ref]=rows;stats[ref]={**counts,'valid_poses':len(rows)}
 print(json.dumps({'ref':ref,'stats':stats[ref],'best':rows[:2]}),flush=True)
write={'scope':__doc__,'source_sha256':c.sha,'movable_refs':sorted(movable),'grid_mm':.2,'statistics':stats,
       'candidate_domains':domains,'screen_limit':'Straight outward first escapes only; other movable parts not yet placed, copper not rerouted, power/reference/thermal checks pending.',
       'adopted':False,'physical':'NOT_TESTED'}
out.write_text(json.dumps(write,indent=2)+'\n')

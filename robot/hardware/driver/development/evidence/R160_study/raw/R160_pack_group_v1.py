"""Bounded joint passive-placement search around the relocated detector.
Preserve all source ground holes, PTH geometry and fixed same-face courtyards.
Non-ground vias/old tracks are counted as explicit pending reroute conflicts.
No PCB is saved; a packing proposal is not electrical or mechanical acceptance.
"""
import ast,json,math,sys,time
from pathlib import Path
from shapely.geometry import box
from shapely.ops import polygonize
from shapely.affinity import translate
from shapely.prepared import prep
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R160-joint-packing.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='bf719a717ffba2a1468126f6a71a1cc3703980fedf647caf8af07c1a9cef62a0'
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
fs={f.GetReference():f for f in c.footprints};refs=['C1301','C1302','C1303','R1303','R1307','R1502'];movable=set(refs+['U1301'])
u=pcb.FOOTPRINT(fs['U1301']);u.SetPosition(pcb.VECTOR2I(64250000,27500000))
up={p.GetNumber():xy(p.GetPosition()) for p in u.Pads()}
targets={'C1301':('1',up['3'],4.2),'C1302':('1',up['4'],4.2),'C1303':('1',up['5'],4.0),
         'R1303':('2',up['3'],6.0),'R1307':('2',up['4'],6.0),'R1502':('1',(64.75,26.175),6.0)}
fixed_cy={ly:unary_union([polyset(f.GetCourtyard(pcb.F_CrtYd if ly=='F.Cu' else pcb.B_CrtYd)) for f in c.footprints if f.GetReference() not in movable and c.board.GetLayerName(f.GetLayer())==ly]+([polyset(u.GetCourtyard(pcb.B_CrtYd))] if ly=='B.Cu' else [])) for ly in ['F.Cu','B.Cu']}
ground_vias=[v for v in c.vias if v.GetNetname()=='GND'];pth=[p for p in c.pads if max(xy(p.GetDrillSize()))>0]
fixed_holes=unary_union([Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6) for v in ground_vias]+[Point(xy(p.GetPosition())).buffer(max(xy(p.GetDrillSize()))/2) for p in pth])
fixed_drill_clear=prep(fixed_holes.buffer(.3005))
fixed_body_holes=prep(fixed_holes)
gvia_pad_clear={ly:unary_union([shape(v,c.ids[ly]) for v in ground_vias]).buffer(.2005) for ly in ['F.Cu','B.Cu']}
pad_protection={};domains={};geometry={};diagnostics={}
for ref in refs:
 f=fs[ref];ly=c.board.GetLayerName(f.GetLayer());pin,target,maximum=targets[ref];rows=[];rejects={k:0 for k in ['range','courtyard','ground_body','pad_physical']}
 for angle in [0,90,180,-90]:
  q=pcb.FOOTPRINT(f);q.SetPosition(pcb.VECTOR2I(0,0));q.SetOrientationDegrees(angle)
  cy0=polyset(q.GetCourtyard(pcb.F_CrtYd if ly=='F.Cu' else pcb.B_CrtYd));body0=fab(q)
  pads0=[(p.GetNumber(),p.GetNetname(),shape(p,c.ids[ly]),xy(p.GetPosition())) for p in q.Pads()]
  endpoint=next(p[3] for p in pads0 if p[0]==pin)
  for number,net,ps,offset in pads0:
   if (net,ly) not in pad_protection:
    foreign_pth=unary_union([shape(p,c.ids[ly]) for p in pth if p.IsOnLayer(c.ids[ly]) and p.GetNetname()!=net]).buffer(.2005)
    pad_protection[net,ly]=prep(gvia_pad_clear[ly].union(foreign_pth))
  for ix in range(580,691):
   x=ix/10
   for iy in range(220,336):
    y=iy/10;dist=math.dist((x+endpoint[0],y+endpoint[1]),target)
    if dist>maximum:rejects['range']+=1;continue
    cy=translate(cy0,xoff=x,yoff=y)
    if not box(.35,.35,69.65,34.65).covers(cy) or cy.intersection(fixed_cy[ly]).area>1e-6:rejects['courtyard']+=1;continue
    body=translate(body0,xoff=x,yoff=y)
    if fixed_body_holes.intersects(body):rejects['ground_body']+=1;continue
    ps=[(net,translate(sh,xoff=x,yoff=y)) for _,net,sh,_ in pads0]
    if any(pad_protection[net,ly].intersects(sh) or fixed_drill_clear.intersects(sh) for net,sh in ps):rejects['pad_physical']+=1;continue
    conflicts=[]
    for t in c.tracks:
     sh=c.shapes.get((uid(t),ly))
     if sh is None:continue
     is_via=isinstance(t,pcb.PCB_VIA)
     bad_body=body.intersection(sh).area>1e-6
     bad_pad=any((net!=t.GetNetname() or is_via) and land.distance(sh)<.2005 for net,land in ps)
     if bad_body or bad_pad:conflicts.append({'uuid':uid(t),'net':t.GetNetname(),'via':is_via,'body':bad_body,'pad_clearance':bad_pad})
    assert not any(v['via'] and v['net']=='GND' for v in conflicts)
    score=dist+.03*math.dist((x,y),xy(f.GetPosition()))+sum(3 if v['via'] else (.75 if v['net'] in ['MOTION_3V3','/WHEEL_VM','/HEAD_VM','/UPS_BAT'] else .1) for v in conflicts)
    ident=f'{ref}:{angle}:{ix}:{iy}'
    rows.append({'id':ident,'reference':ref,'position_mm':[x,y],'rotation_deg':angle,'target_pin':pin,'target_distance_mm':dist,'score':score,'pending_copper_conflicts':conflicts})
    geometry[ident]=cy
 rows.sort(key=lambda r:r['score']);domains[ref]=rows;diagnostics[ref]={'valid_poses':len(rows),'rejections':rejects}
 print(json.dumps({'reference':ref,**diagnostics[ref],'best':rows[:2]}),flush=True)
order=sorted(refs,key=lambda r:len(domains[r]));solutions=[];nodes=0;limit=200000
def search(assigned,pending):
 global nodes
 nodes+=1
 if nodes>limit or len(solutions)>=8:return
 if not pending:
  solutions.append({'score':sum(r['score'] for r in assigned),'poses':assigned.copy()});return
 ref=min(pending,key=lambda r:len(pending[r]));remaining={k:v for k,v in pending.items() if k!=ref}
 for row in pending[ref]:
  if nodes>limit or len(solutions)>=8:break
  cy=geometry[row['id']];filtered={}
  for other,values in remaining.items():
   if fs[other].GetLayer()!=fs[ref].GetLayer():filtered[other]=values
   else:filtered[other]=[v for v in values if cy.intersection(geometry[v['id']]).area<=1e-6]
   if not filtered[other]:break
  else:search(assigned+[row],filtered)
search([],domains)
solutions.sort(key=lambda s:s['score'])
result={'scope':__doc__,'source_sha256':c.sha,'fixed_U1301':{'position_mm':[64.25,27.5],'rotation_deg':90},
 'grid_mm':.1,'ranges_mm':{'x':[58,69],'y':[22,33.5]},'target_distance_limits':'Local planning bounds only, not manufacturer qualification.',
 'diagnostics':diagnostics,'candidate_domains':domains,'search_nodes':nodes,'node_limit':limit,'solutions':solutions,'adopted':False,'physical':'NOT_TESTED'}
out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'complete':True,'nodes':nodes,'solution_count':len(solutions),'best':solutions[:1]}),flush=True)

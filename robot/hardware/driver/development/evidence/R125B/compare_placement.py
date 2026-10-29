import sys,json,math
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from shapely.affinity import rotate,translate
from shapely.geometry import box
from shapely.prepared import prep
from plan_existing_copper import groups
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');ref='C1208';f=next(f for f in c.footprints if f.GetReference()==ref);origin=xy(f.GetPosition());angle=f.GetOrientationDegrees();f.BuildCourtyardCaches();court=polyset(f.GetCourtyard(pcb.B_Cu))
other_courts=[]
for q in c.footprints:
 if q.GetReference()!=ref:
  q.BuildCourtyardCaches();s=polyset(q.GetCourtyard(pcb.B_Cu))
  if not s.is_empty:other_courts.append(s)
court_ob=prep(unary_union(other_courts));edge=prep(box(.5,.5,69.5,34.5))
lands=[(p.GetNumber(),p.GetNetname(),c.shapes[uid(p),'B.Cu']) for p in f.Pads()]
blocked={net:prep(unary_union([s.buffer(.205) for (id_,ly),s in c.shapes.items() if ly=='B.Cu' and c.by_id[id_].GetNetname()!=net and not (isinstance(c.by_id[id_],pcb.PAD) and c.pad_name(c.by_id[id_]).startswith(ref+'.'))])) for _,net,_ in lands}
viaob=prep(unary_union([s.buffer(.205) for (id_,ly),s in c.shapes.items() if ly=='B.Cu' and isinstance(c.by_id[id_],pcb.PCB_VIA)]))
body=unary_union([k['shape'] for k in c.keepouts if k['name'].startswith('BODY_'+ref+'_') and k['tracks']]);bodyob=prep(unary_union([s for (id_,ly),s in c.shapes.items() if ly=='B.Cu' and not isinstance(c.by_id[id_],pcb.PAD)]))
main=groups(c,'/HEAD_VM')[0]['layers']['B.Cu'];gnd=c.copper['GND','B.Cu'];rows=[];tested=0
for targetangle in [0,90,180,270]:
 ang=-(targetangle-angle);rcourt=rotate(court,ang,origin=origin);rlands=[(pin,net,rotate(s,ang,origin=origin)) for pin,net,s in lands];rb=rotate(body,ang,origin=origin)
 for iy in range(24,117):
  y=iy*.25
  for ix in range(7,274):
   x=ix*.25;dx=x-origin[0];dy=y-origin[1];tested+=1
   p=translate(rcourt,xoff=dx,yoff=dy)
   if not edge.covers(p) or court_ob.intersects(p):continue
   shifted=[(pin,net,translate(s,xoff=dx,yoff=dy)) for pin,net,s in rlands]
   if any(blocked[net].intersects(s) or viaob.intersects(s) for pin,net,s in shifted):continue
   if bodyob.intersects(translate(rb,xoff=dx,yoff=dy)):continue
   hs=next(s for pin,net,s in shifted if pin=='1');gs=next(s for pin,net,s in shifted if pin=='2');hd=hs.distance(main);gd=gs.distance(gnd)
   if hd>3 or gd>.05:continue
   rows.append({'position_mm':[x,y],'orientation_deg':targetangle,'head_copper_gap_mm':hd,'ground_copper_gap_mm':gd,'move_mm':math.hypot(dx,dy),'distance_to_efuse_mm':math.hypot(x-10.5,y-24.25),'distance_to_head_connector_mm':math.hypot(x-61.775,y-33.4)})
rows.sort(key=lambda r:(r['head_copper_gap_mm']>1e-7,r['head_copper_gap_mm'],min(r['distance_to_efuse_mm'],r['distance_to_head_connector_mm']),r['move_mm']))
out={'source_sha256':c.sha,'scope':'Read-only 0.25-mm placement screen, all four rotations on B side; full native/routing/thermal checks still required','tested_positions':tested,'passing_positions':len(rows),'candidates':rows[:80]}
Path('robot/.state/c3-completion/trials/R125-C1208-placements.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({**out,'candidates':rows[:12]},indent=2))

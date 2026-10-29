import sys,json
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from shapely.affinity import rotate,translate
source=Path('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');c=Copper(source)
scenarios=[{'name':f'Q1401 rotation {angle} at original center','moves':{'Q1401':([0,0],angle)}} for angle in [0,90,180,270]]
scenarios += [{'name':'R126B left-shift gate group','moves':{'Q1401':([-.7,0],270),'R1406':([-.425,0],0),'R1407':([-.425,.125],0)}},{'name':'R126C rotate R1406 upward','moves':{'Q1401':([-.7,0],270),'R1406':([0,-.875],90),'R1407':([-.425,.125],0)}}]
dels={'3d28f70a-dcf4-4144-9558-decbb7f9feca','b905fcd1-cd48-4f51-86df-f423b4d3dcfb','5fcf1aa3-5657-4c2b-bfef-31c82a1f1ba9'}
rows=[]
for scene in scenarios:
 moves=scene['moves'];newpads={};courts={};minimums=[]
 for f in c.footprints:
  ref=f.GetReference();f.BuildCourtyardCaches();s=polyset(f.GetCourtyard(pcb.B_Cu))
  if ref in moves:
   delta,angle=moves[ref];ang=-(angle-f.GetOrientationDegrees());origin=xy(f.GetPosition());tr=lambda x:translate(rotate(x,ang,origin=origin),xoff=delta[0],yoff=delta[1]);courts[ref]=tr(s)
   for p in f.Pads():newpads[uid(p)]=(ref,c.pad_name(p),p.GetNetname(),tr(c.shapes[uid(p),'B.Cu']))
  else:courts[ref]=s
 issues=[]
 for ref in moves:
  nearest=[]
  for other,s in courts.items():
   if other==ref or s.is_empty:continue
   dist=courts[ref].distance(s);nearest.append([dist,other])
   if courts[ref].intersects(s):issues.append(['courtyard',ref,other])
  minimums.append({'reference':ref,'nearest_courtyards':sorted(nearest)[:3]})
 for id_,(ref,pin,net,s) in newpads.items():
  for (oid,ly),old in c.shapes.items():
   if ly!='B.Cu' or oid in newpads or oid in dels:continue
   obj=c.by_id[oid]
   if (obj.GetNetname()!=net or isinstance(obj,pcb.PCB_VIA)) and s.distance(old)<.1999996:issues.append(['pad_clearance',pin,c.pad_name(obj),obj.GetNetname(),s.distance(old)])
  for oid,(_,other,n2,s2) in newpads.items():
   if oid>id_ and net!=n2 and s.distance(s2)<.1999996:issues.append(['moved_pad_clearance',pin,other,s.distance(s2)])
 rows.append({'name':scene['name'],'moves':moves,'issues':issues,'nearest_courtyards':minimums,'screen_status':'FAIL' if issues else 'PASS'})
out={'source_sha256':c.sha,'scope':'Read-only same-face courtyard and pad clearances against native pads/tracks/vias; excludes three explicitly replaced gate/OUT segments. Does not validate ground fill, new routes, internal projections, thermal or qualification. Native candidate DRC remains authoritative.','scenarios':rows}
Path('robot/.state/c3-completion/trials/R126-placement-comparison.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps([{'name':r['name'],'screen_status':r['screen_status'],'issue_count':len(r['issues'])} for r in rows],indent=2))

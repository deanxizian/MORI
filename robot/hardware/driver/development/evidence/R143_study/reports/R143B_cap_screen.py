"""Finite C303 placement comparison for the proposed U303 relocation.
No board is saved. Native pad/courtyard spacing and mounted-face body conflicts
are screened; native refill/DRC and full power/reference checks remain required.
"""
import ast,json,sys,math
from pathlib import Path
from shapely.affinity import rotate,translate
from shapely.geometry import box
from shapely.ops import polygonize
from shapely.prepared import prep
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R143B-cap-screen.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='2a7c04b8430875a0f8f9e4bdde4b789da6b8efb5f84ee991a360f1d5b6d006dd'
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab_helper','exec'))
fs={f.GetReference():f for f in c.footprints};f=fs['C303'];u=fs['U303'];u0=xy(u.GetPosition());f0=xy(f.GetPosition())
def ut(g):return translate(rotate(g,180,origin=u0),xoff=21-u0[0],yoff=12.4-u0[1])
removed={'53522878-2ddb-52d7-93a6-a12df88268cf','624fe692-481e-582f-8e19-1c25cf9d48d3','6bdc90d4-66d7-5c79-a33d-f2102f11e4aa','ef3bb842-5e07-55cf-8829-2b9f42ca47ca','525a7ae2-c619-480c-b284-1a1b028034bc','0c67320a-3b36-41f5-9372-e866af4a1d9b','879415a2-d05e-4a60-8fc6-43453ead98fa','7b4c4e31-9dd9-4673-bf37-973c8204164e','4f4d6d69-0c12-4912-8387-df7396dbc26d'}
others=[]
for q in c.footprints:
 if q.GetLayer()!=pcb.B_Cu or q.GetReference()=='C303':continue
 g=polyset(q.GetCourtyard(pcb.B_CrtYd));others.append(ut(g) if q.GetReference()=='U303' else g)
other_courts=prep(unary_union(others).buffer(.01))
foreign={};allpads=[]
for q in c.pads:
 if c.pad_name(q).rsplit('.',1)[0]=='C303':continue
 g=c.shapes.get((uid(q),'B.Cu'))
 if g is not None:allpads.append((q.GetNetname(),ut(g) if c.pad_name(q).rsplit('.',1)[0]=='U303' else g))
tracks=[(t,c.shapes[uid(t),'B.Cu']) for t in c.segments if t.GetLayer()==pcb.B_Cu and uid(t) not in removed]
for net in ['GND','MOTION_3V3']:
 foreign[net]=prep(unary_union([g for n,g in allpads if n!=net]+[g for t,g in tracks if t.GetNetname()!=net]).buffer(.205))
via=prep(unary_union([s for (id_,ly),s in c.shapes.items() if ly=='B.Cu' and isinstance(c.by_id[id_],pcb.PCB_VIA)]).buffer(.205))
keep=prep(unary_union([k['shape'] for k in c.keepouts if 'B.Cu' in k['layers'] and k['name'].startswith('MOUNT_')]))
court=polyset(f.GetCourtyard(pcb.B_CrtYd));body=fab(f);rows=[]
for angle in [0,90,180,270]:
 for ix in range(210,251):
  for iy in range(118,168):
   x,y=ix/10,iy/10
   def tr(g):return translate(rotate(g,-(angle-f.GetOrientationDegrees()),origin=f0),xoff=x-f0[0],yoff=y-f0[1])
   ct=tr(court)
   if other_courts.intersects(ct) or keep.intersects(ct):continue
   pp=[(q,tr(c.shapes[uid(q),'B.Cu'])) for q in f.Pads()]
   if any(foreign[q.GetNetname()].intersects(g) or via.intersects(g) for q,g in pp):continue
   bodyg=tr(body)
   if any(bodyg.intersects(g) for t,g in tracks):continue
   p1=next(g for q,g in pp if q.GetNumber()=='1');p2=next(g for q,g in pp if q.GetNumber()=='2')
   dist=p1.centroid.distance(Point(21.9375,12.4))
   if dist>4 or not p2.intersects(c.copper['GND','B.Cu']):continue
   rows.append({'position_mm':[x,y],'rotation_deg':angle,'distance_mm':dist,'pads_mm':{q.GetNumber():[round(g.centroid.x,6),round(g.centroid.y,6)] for q,g in pp}})
rows.sort(key=lambda r:r['distance_mm']);chosen=[]
for r in rows:
 if all(math.dist(r['position_mm'],q['position_mm'])>.5 or r['rotation_deg']!=q['rotation_deg'] for q in chosen):chosen.append(r)
 if len(chosen)==16:break
out.write_text(json.dumps({'scope':__doc__,'source_sha256':c.sha,'u303_position_mm':[21,12.4],'u303_rotation_deg':0,'candidate_count':len(rows),'chosen':chosen},indent=2)+'\n')
print(json.dumps({'candidate_count':len(rows),'chosen':chosen[:8]},indent=2))

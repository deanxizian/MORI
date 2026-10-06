import sys,json,math,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid
load_collections();assembled();bpy.context.view_layer.update()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH'}
f=next(r for r in json.loads((HERE/'fastener_current.json').read_text()) if r['id']=='Head_Pitch_Ear_1_Screw');p=np.array(f['tool_start_mm']);name=f['id']
bench={n:s for n,s in ss.items() if n.startswith(('Pitch_Yoke','Pitch_Bearing','Pitch_Servo','Head_Pitch_')) and n!=name}
# Published envelope:108length x16max width x2.3plate;14tip-height.
# Unknown tip/retainer profile bounded deliberately by diameter6/11,
# not declared exact manufacturer CAD. Bar extends toward +Z on the bench.
bar=manifold.Manifold.cube([2.3,16,108]).translate([p[0]+11.7,-8,p[2]-8])
bit=manifold.Manifold.cylinder(10,3,3,64).rotate([0,90,0]).translate(p)
root=manifold.Manifold.cylinder(4,5.5,5.5,64).rotate([0,90,0]).translate(p+[10,0,0]);tool=bar+bit+root
rows=[]
for angle in range(-180,181,2):
 tr=Matrix.Translation(Vector(p))@Matrix.Rotation(math.radians(angle),4,'X')@Matrix.Translation(-Vector(p));m=tool.transform(np.array(tr)[:3,:]);hits=[]
 for n,s in bench.items():
  bb=np.array(m.bounding_box())
  if np.any(bb[3:]<s.lo) or np.any(s.hi<bb[:3]):continue
  v=max(0,(m^s.m).volume())
  if v>.02:hits.append({'part':n,'volume_mm3':v})
 rows.append({'angle_deg':angle,'hits':hits})
report={'tool':'ANEX6102 +0x14','source':'https://www.anextool.co.jp/wp-content/uploads/6102-0.pdf','sha256':hashlib.sha256((HERE/'sources/ANEX_6102_0.pdf').read_bytes()).hexdigest(),'published_envelope_mm':{'length':108,'width_max':16,'plate_thickness':2.3,'tip_height':14},'assumed_conservative_profile_mm':{'tip_diameter':6,'root_diameter':11},'screw':name,'assembly_prerequisite':'Pitch servo on detached yoke before yaw servo/cradle; blade points upward','rows':rows,'status':'PASS' if any(all(not rr['hits'] for rr in rows[i:i+11]) for i in range(len(rows)-10)) else 'FAIL','physical_tool_fit':'NOT_TESTED','note':'Finite60deg swing of a conservative envelope; requires re-indexing. Exact tip recess engagement, hand pressure and tool purchase not qualified.'}
(HERE/'offset_tool_checks.json').write_text(json.dumps(report,indent=2));print('OFFSET_TOOL',report['status'],[r['angle_deg'] for r in rows if not r['hits']],flush=True)

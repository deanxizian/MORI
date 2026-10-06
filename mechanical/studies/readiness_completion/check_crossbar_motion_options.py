import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from common import *
from validate import Solid,rigidtr
from optics_mount import display_transform
bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections()
for n in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[n].hide_viewport=False
assembled();ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.get('group')!='dock'}
g=json.load(open(ROOT/'reports/readiness_geometry.json'));cfg=P['readiness_completion']['lcd']
def cube(lo,hi):return manifold.Manifold.cube((np.array(hi)-lo).tolist()).translate(lo)
def cyl(p,axis,r,h):
 tr=Matrix.Translation(Vector(p))@Vector(axis).to_track_quat('Z','Y').to_matrix().to_4x4()
 return manifold.Manifold.cylinder(h,r,r,64).transform(np.array(tr)[:3,:])
pitch=[n for n,a in ss.items() if a.group=='pitch' and n!='Display_Frame'];fixed=[n for n,a in ss.items() if a.group!='pitch']
rows=[]
for rear in [27.5,28.5,29.5,30.5,31.5,32.5,33.5]:
 front=rear+3
 original=ss['Display_Frame'].m
 # Study only: replace the full lower crossbar with a straight rectangular
 # one, retaining every pre-existing part above its top and all side joints.
 candidate=original-cube([-32.001,27.49,207.99],[32.001,45,219.999])
 candidate+=cube([-32,rear,208],[32,front,220])
 # Preserve source mounting blocks (above z211.03) where they meet LCD posts.
 base=json.load(open(PROJECT/P['readiness_completion']['baseline_geometry']))['Display_Frame']
 baseline=manifold.Manifold(manifold.Mesh64(np.array(base['vertices_mm']),np.array(base['triangles'],dtype=np.uint64)))
 for x in [-14.8492424,14.8492424]:candidate+=baseline^cube([x-3.5,27.5,211.033],[x+3.5,44,218.035])
 for row in g['LCD']:
  axis=np.array(row['axis']);p=np.array(row['post_face_mm']);f=np.array(row['head_bearing_mm'])
  candidate-=cyl(p-axis*45,axis,cfg['clearance_radius_mm'],60)
  candidate-=cyl(f-axis*20,axis,cfg['spotface_radius_mm'],20)
 collisions=[]
 for angle in range(-20,26,5):
  moved=candidate.transform(np.array(rigidtr(0,angle))[:3,:])
  for n in fixed:
   v=max(0,(moved^ss[n].m).volume())
   if v>.01:collisions.append({'pitch':angle,'part':n,'mm3':v,'box':list((moved^ss[n].m).bounding_box())})
 for n in pitch:
  v=max(0,(candidate^ss[n].m).volume())
  if v>.01:collisions.append({'pitch':'static','part':n,'mm3':v})
 rows.append({'rear_y':rear,'front_y':front,'positive_components':sum(m.volume()>.001 for m in candidate.decompose()),'hits':collisions})
print(rows);save_json(Path(__file__).parent/'crossbar_options.json',rows)

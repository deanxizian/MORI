import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from common import *
from validate import Solid
bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections()
for n in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[n].hide_viewport=False
assembled();ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.get('group')!='dock'}
g=json.load(open(ROOT/'reports/readiness_geometry.json'));cfg=P['readiness_completion']['lcd']
def cyl(p,axis,r,h):
 tr=Matrix.Translation(Vector(p))@Vector(axis).to_track_quat('Z','Y').to_matrix().to_4x4()
 return manifold.Manifold.cylinder(h,r,r,64).transform(np.array(tr)[:3,:])
rows=[]
for extension in [2,3,3.5,4]:
 slab=manifold.Manifold.cube([64,3,extension+.05]).translate([-32,27.5,212-extension]);candidate=ss['Display_Frame'].m+slab
 for row in g['LCD']:
  axis=np.array(row['axis']);p=np.array(row['post_face_mm']);f=np.array(row['head_bearing_mm'])
  candidate-=cyl(p-axis*45,axis,cfg['clearance_radius_mm'],60)
  candidate-=cyl(f-axis*20,axis,cfg['spotface_radius_mm'],20)
 changed=candidate-ss['Display_Frame'].m;bad=[]
 for n,a in ss.items():
  if n=='Display_Frame':continue
  v=max(0,(changed^a.m).volume())
  if v>.01:bad.append({'part':n,'volume_mm3':v})
 rows.append({'extension_mm':extension,'added_volume_mm3':max(0,changed.volume()),'hits':bad,'min_counterbore_bottom_wall_mm':211.71-cfg['spotface_radius_mm']-(212-extension)})
print(rows);save_json(Path(__file__).parent/'lower_rail_candidate.json',rows)

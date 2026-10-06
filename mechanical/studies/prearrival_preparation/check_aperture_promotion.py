import sys,json,math
from pathlib import Path
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H.parents[1]/'scripts'))
from common import *
from validate import Solid,intersect_volume
from optics_mount import camera_transform,camera_pupil
from validate_prearrival_completion import validate_prearrival_completion
load_collections()
for name in ['DATUMS','DOCK','KEEP_OUT','COUPONS']:COLS[name].hide_viewport=False
assembled();bpy.context.view_layer.update()
base=json.loads((H/'baseline_geometry.json').read_text())['Head_Front'];old=manifold.Manifold(manifold.Mesh64(np.array(base['vertices_mm']),np.array(base['triangles'],dtype=np.uint64)))
now=Solid(bpy.data.objects[PREFIX+'Head_Front']).m;witness=Solid(bpy.data.objects[PREFIX+'Integrated_Face_Region']).m
q=P['prearrival_completion']['camera_aperture'];rot=np.array(camera_transform().to_3x3())@np.array([[1,0,0],[0,0,1],[0,-1,0]]);p=np.array(camera_pupil());kh=math.sqrt(2)*math.tan(math.radians(28.5));kv=math.sqrt(2)*math.tan(math.radians(22))
pts=[[math.cos(a)*(.3+kh*w),math.sin(a)*(.3+kv*w),w] for w in [0,35] for a in np.linspace(0,2*math.pi,128,endpoint=False)]
cut=manifold.Manifold.hull_points(pts).transform(np.c_[rot,p]);result={'camera_pupil':p.tolist(),'cut_witness':max(0,(cut^witness).volume()),'actual_removal_in_witness':max(0,((old-now)^witness).volume()),'witness_bounds':witness.bounding_box(),'witness_outside_old':max(0,(witness-old).volume())}
solids={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.get('group')!='dock'}
def check(*args):print(args[0],args[1],args[3] if args[0]=='prearrival_camera_rays' else '',flush=True)
validate_prearrival_completion(solids,Solid,intersect_volume,check)
(H/'aperture_promotion_diagnostic.json').write_text(json.dumps(result,indent=2));print(result,flush=True)

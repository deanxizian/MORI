import sys,json
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[2];sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from common import *
from validate import Solid
from optics_mount import camera_transform,camera_pupil
out={};old=None
for kind,path in [('candidate',H/'camera_aperture_candidate.blend'),('current',PROJECT/'mechanical/mori_v1_2.blend')]:
 bpy.ops.wm.open_mainfile(filepath=str(path));load_collections();assembled();bpy.context.view_layer.update()
 rows={}
 for name in ['Head_Front','Integrated_Face_Region','Camera_Lens','Display_PCB','Parking_Cradle']:
  o=bpy.data.objects[PREFIX+name];a=Solid(o);rows[name]={'bounds':[a.lo.tolist(),a.hi.tolist()],'matrix':[list(r) for r in o.matrix_world],'volume':a.m.volume(),'role':o.get('role')}
  if name=='Head_Front':
   if old is not None:rows[name].update(added_vs_candidate=max(0,(a.m-old).volume()),removed_vs_candidate=max(0,(old-a.m).volume()))
   else:old=a.m
 rot=np.array(camera_transform().to_3x3())@np.array([[1,0,0],[0,0,1],[0,-1,0]]);tr=np.c_[rot,np.array(camera_pupil())];q=P['prearrival_completion']['camera_aperture'];kh=math.sqrt(2)*math.tan(math.radians(28.5));kv=math.sqrt(2)*math.tan(math.radians(22))
 pts=[[math.cos(a)*(.3+kh*w),math.sin(a)*(.3+kv*w),w] for w in [0,35] for a in np.linspace(0,2*math.pi,128,endpoint=False)]
 cut=manifold.Manifold.hull_points(pts).transform(tr);rows['cut_bezel']=max(0,(cut^Solid(bpy.data.objects[PREFIX+'Integrated_Face_Region']).m).volume());out[kind]=rows
(H/'promotion_inspection.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))

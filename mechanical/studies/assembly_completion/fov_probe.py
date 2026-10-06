import sys,json,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from common import *
from validate import Solid
from optics_mount import camera_transform
bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections()
for n in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[n].hide_viewport=False
assembled();shell=Solid(bpy.data.objects[PREFIX+'Head_Front']);window=Solid(bpy.data.objects[PREFIX+'Camera_Window']);rot=camera_transform().to_3x3();p=Vector(P['camera']['pupil_from_head_mm'])+Vector((0,0,D['head_z']));rows=[]
for d in np.arange(0,4.01,.25):
 origin=p-rot@Vector((0,float(d),0));hits=[];miss=[]
 for ix in range(11):
  for iz in range(9):
   h=(ix/10*2-1)*math.radians(57/2);v=(iz/8*2-1)*math.radians(44/2);direction=rot@Vector((math.tan(h),1,math.tan(v))).normalized()
   if shell.bvh().ray_cast(origin,direction,150)[0] is not None:hits.append([ix,iz])
   if window.bvh().ray_cast(origin,direction,12)[0] is None:miss.append([ix,iz])
 rows.append({'recess_mm':float(d),'occluded':len(hits),'window_misses':len(miss)})
save_json(Path(__file__).parent/'fov_recess_sweep.json',rows);print(json.dumps(rows))

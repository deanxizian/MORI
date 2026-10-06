import sys,json
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'scripts'))
from common import *
from validate import Solid
from render import camera
load_collections();assembled()
out=Path(__file__).parent
for name in ['Yaw_Servo','Pitch_Servo','Yaw_Output','Pitch_Output','Yaw_Horn','Pitch_Horn']:
    o=bpy.data.objects[PREFIX+name];a=Solid(o)
    print(name,'bounds',list(zip(a.lo,a.hi)), 'components',[(round(m.volume(),3),m.bounding_box()) for m in a.m.decompose()])
bpy.ops.wm.stl_import(filepath=str(root/'sources/scs0009_detail/pollen_scs0009_reference.stl'))
o=bpy.context.object
print('POLLEN','dimensions',list(o.dimensions),'bounds',bounds(o))
sc=bpy.context.scene
for q in sc.objects:
    if q.type=='MESH':q.hide_render=q!=o
sc.render.engine='CYCLES';sc.cycles.samples=16;sc.cycles.use_denoising=True
sc.render.resolution_x=1100;sc.render.resolution_y=900;sc.render.resolution_percentage=100
o.data.materials.clear();o.data.materials.append(MATS.get('metal') or material('reference_servo',(.32,.36,.37)))
b=bound=None
bb=bounds(o);center=Vector([sum(v)/2 for v in bb]);size=max(o.dimensions)
camera('vendor_reference',center+Vector((size*2,size*3,size*2)),center,size*1.6)
sc.render.filepath=str(out/'pollen_reference.png');bpy.ops.render.render(write_still=True)
save_json(out/'pollen_reference_inspection.json',{'bounds_xyz':bb,'dimensions':list(o.dimensions),'status':'THIRD_PARTY_NOT_VENDOR_CAD'})

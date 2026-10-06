import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from common import *
from validate import Solid,intersect_volume
from optics_mount import camera_transform
bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections();assembled()
for c in ['DOCK','COUPONS','DATUMS','KEEP_OUT']:COLS[c].hide_viewport=False
bpy.context.view_layer.update();ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.get('group')!='dock'}
axis=camera_transform().to_3x3()@Vector((0,1,0));rows=[]
for dist in [0,.5,1,1.5,2,2.5,3,3.5,4]:
 tr=Matrix.Translation(-axis*dist);row={'recess_mm':dist,'overlaps':[]}
 for name in ['Camera_PCB','Camera_Lens']:
  a=Solid(ss[name].o,ss[name],tr)
  for other in ['Head_Front','Display_Frame','Display_PCB','Pitch_Cradle']:
   v=intersect_volume(a,ss[other]);row['overlaps'].append({'part':name,'obstacle':other,'mm3':round(v,3)})
 rows.append(row)
save_json(Path(__file__).parent/'camera_recess_probe.json',rows);print(json.dumps(rows))

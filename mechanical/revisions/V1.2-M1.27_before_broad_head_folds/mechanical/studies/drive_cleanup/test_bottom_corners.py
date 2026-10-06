import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from common import *
from validate import Solid
from layout_cleanup import mm_mesh
bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections();assembled()
s=P['drive_print_cleanup'];w=P['wheel_interface'];hx,hy=[v/2 for v in s['central_outer_xy_mm']];c=s['cap_corner_chamfer_mm'];base=w['clamp_plate_bottom_z_mm']-w['cap_head_recess_depth_mm']
cap=Solid(bpy.data.objects[PREFIX+'Motor_Retainer']);body=Solid(bpy.data.objects[PREFIX+'Body_Lower']);corners=[];cuts=[]
for sx in [-1,1]:
 for sy in [-1,1]:
  pts=[(sx*hx,sy*hy),(sx*(hx-c),sy*hy),(sx*hx,sy*(hy-c))]
  if sx*sy<0:pts.reverse()
  corners.append(manifold.CrossSection([pts]).extrude(s['case_cap_split_z_mm']-base).translate([0,0,base]))
  cuts.append(manifold.Manifold.hull_points([(sx*hx,sy*hy,base),(sx*(hx-c),sy*hy,base),(sx*hx,sy*(hy-c),base),(sx*hx,sy*hy,base+c)]))
new=cap.m+manifold.Manifold.batch_boolean(corners,manifold.OpType.Add)-manifold.Manifold.batch_boolean(cuts,manifold.OpType.Add)
report={'overlap_mm3':(new^body.m).volume(),'minimum_gap_mm':new.min_gap(body.m,10),'added_volume_mm3':new.volume()-cap.m.volume()}
save_json(ROOT/'reports/drive_bottom_corner_trial.json',report);print('BOTTOM_CORNERS',report)

"""Read-only counterfactual: square just the remaining shell-clearance corners."""
import sys,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'scripts'))
from common import *
from validate import Solid

bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections();assembled()
cap=Solid(bpy.data.objects[PREFIX+'Motor_Retainer']);shell=Solid(bpy.data.objects[PREFIX+'Body_Lower'])
s=P['drive_print_cleanup'];w=P['wheel_interface'];hx,hy=[x/2 for x in s['central_outer_xy_mm']]
c=s['cap_corner_chamfer_mm'];z0=w['clamp_plate_bottom_z_mm']-w['cap_head_recess_depth_mm']
corner_parts=[]
for sx in [-1,1]:
    for sy in [-1,1]:
        corner_parts.append(manifold.Manifold.hull_points([(sx*hx,sy*hy,z0),(sx*(hx-c),sy*hy,z0),(sx*hx,sy*(hy-c),z0),(sx*hx,sy*hy,z0+c)]))
corners=manifold.Manifold.batch_boolean(corner_parts,manifold.OpType.Add)
edge_parts=[]
hi=w['bearing_housing_abs_x_limits_mm'][1];c=s['bearing_outer_lower_chamfer_mm'];z=s['bearing_bar_bottom_outer_z_mm'];depth=s['bearing_bar_depth_mm']
for sign in [-1,1]:
    profile=[(hi-c,z),(hi,z),(hi,z+c)]
    if sign<0:profile=[(-x,zz) for x,zz in reversed(profile)]
    edge_parts.append(manifold.CrossSection([profile]).extrude(depth).rotate([90,0,0]).translate([0,depth/2,0]))
edges=manifold.Manifold.batch_boolean(edge_parts,manifold.OpType.Add)
current=(cap.m^shell.m).volume()
plate=((cap.m+corners)^shell.m).volume()
saddle=((cap.m+edges)^shell.m).volume()
both=((cap.m+edges+corners)^shell.m).volume()
r={'revision':P['revision'],'source_blend_sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),
   'method':'Read final assembly; add back only plate corner triangles or outer saddle bottom-edge triangles; exact nominal Manifold solid intersections with Body_Lower. Do not save modified geometry.',
   'current_overlap_mm3':current,'current_minimum_cap_shell_gap_mm':cap.m.min_gap(shell.m,10),
   'plate_corners_square_overlap_mm3':plate,'outer_saddle_edges_square_overlap_mm3':saddle,'both_square_overlap_mm3':both,
   'plate_corner_chamfer_mm':s['cap_corner_chamfer_mm'],'saddle_lower_edge_chamfer_mm':s['bearing_outer_lower_chamfer_mm'],
   'limits':'Nominal mesh result. Tolerance, flexure, manufacturing and print strength NOT_TESTED.',
   'status':'PASS' if current<.01 and plate>.01 and saddle>.01 and both>.01 else 'FAIL'}
save_json(root/'reports/drive_retained_interfaces.json',r);print('DRIVE_RETAINED_INTERFACES',r)
if r['status']!='PASS':raise RuntimeError('Counterfactual does not support retained cuts')

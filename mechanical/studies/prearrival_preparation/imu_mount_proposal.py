"""Keep native sensor pose; evaluate an unrouted extra-edge mechanical PCB proposal."""
import sys,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[2]/'mechanical/scripts'))
from common import *
from validate import Solid
ROOT=PROJECT
load_collections();assembled();bpy.context.view_layer.update()
# Native IMU original20x16 extends fromy=-48 to-32. Extend fullrear edge5mm;
# no existing part/trace/hole is moved. Proposednew origin adds5 to old native y.
extension=manifold.Manifold.cube([20,5,1.6]).translate([-35,-53,106.8])
boss=manifold.Manifold.cylinder(3.0,3.3,3.3,80).translate([-25,-50.5,108.4])
rows=[]
for o in parts():
 if o.get('role')!='part' or o.get('group') in ['dock','coupon']:continue
 s=Solid(o)
 for name,m,exclude in [('PCB_extension',extension,{'Body_IMU'}),('third_boss',boss,{'Load_Frame','Body_IMU'})]:
  if s.name in exclude:continue
  bb=np.array(m.bounding_box())
  if np.any(bb[3:]<s.lo) or np.any(s.hi<bb[:3]):continue
  v=max(0,(m^s.m).volume())
  if v>.02:rows.append({'allocation':name,'part':s.name,'mm3':round(v,4)})
report={'status':'PASS' if not rows else 'FAIL','proposal_only':True,'native_board_changed':False,'received':'MORI_imu_P5R4','old_outline_mm':[20,16],'proposed_outline_mm':[20,21],'new_board_origin_world_mm':[-35,-53,108.355],'existing_footprint_translation_in_new_PCB_coordinates_mm':[0,5],'proposed_holes_xy_mm':[[2.5,17.5],[17.5,17.5],[10,2.5]],'proposed_finished_hole_diameter_mm':2.4,'third_boss_axis_world_mm':[-25,-50.5,108.4],'proposed_copper_component_keepout_diameter_mm':6.6,'sensor_body_transform_change':'NONE if footprints and original holes are translated together as specified; body components-down orientation retained','extra_metal_parts':['one M2 screw','one selected M2 insert'],'extra_print_parts':0,'collisions':rows,'source_recommendation':'https://invensense.tdk.com/wp-content/uploads/2024/04/AN-000393-TDK-InvenSense-IMU-PCB-Design-and-MEMS-Assembly-Guidelines-v1.5.pdf','limits':'PCB geometry proposal only, not routed or electrically reviewed. One-piece boss addition to Load_Frame must follow a published native-board handoff and fastener selection. Three coplanar anchors minimize stress; no extra foam/isolation inferred.'}
(HERE/'imu_mount_proposal.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('IMU_MOUNT_PROPOSAL_COMPLETE',report['status'],rows,flush=True)

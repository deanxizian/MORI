"""Locate first sampled stop engagement after relocating tabs above the bearing.

This is rigid geometric evidence; it does not qualify impact strength or real angles.
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from validate import Solid

bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections();assembled()
a=Solid(bpy.data.objects[PREFIX+'Pitch_Yoke']);b=Solid(bpy.data.objects[PREFIX+'Yaw_Base'])
expected_z=D['yaw_bearing_z']+P['part_consolidation']['final_yaw_stop_z_from_bearing_mm']
rows=[]
for sign in [-1,1]:
    free=0;hit=None
    for angle in range(0,91):
        overlap=a.m.rotate([0,0,sign*angle])^b.m
        if overlap.volume()>.01:
            m=overlap.to_mesh64();v=np.asarray(m.vert_properties)[:,:3]
            hit={'first_sampled_overlap_deg':sign*angle,'previous_free_sample_deg':sign*free,'overlap_mm3':overlap.volume(),'overlap_bounds_xyz_mm':list(zip(v.min(0).tolist(),v.max(0).tolist()))};break
        free=angle
    ok=bool(hit and 60<abs(hit['first_sampled_overlap_deg'])<=85 and abs(sum(hit['overlap_bounds_xyz_mm'][2])/2-expected_z)<.6)
    rows.append({'direction':sign,'status':'PASS' if ok else 'FAIL','engagement':hit})
result={'revision':P['revision'],'status':'PASS' if all(r['status']=='PASS' for r in rows) else 'FAIL','step_deg':1,'tested_each_direction_deg':[0,90],'intersection_threshold_mm3':.01,'stop_center_z_mm':expected_z,'cases':rows,'method':'Actual one-piece yaw U/journal vs fixed bearing bridge triangle-solid intersection; identifies overlap at the relocated tab height. Previous free sample / first positive-volume sample bound the onset only to this grid and volume threshold.','limits':['Not an exact continuous contact angle','No head-shell or cable permission to travel past normal +/-60deg','No tolerance, flex, impact or printed stop strength qualification']}
save_json(ROOT/'reports/integrated_stop_check.json',result)
print(json.dumps(result,ensure_ascii=False))
if result['status']!='PASS':raise RuntimeError('Integrated stop geometry needs correction')

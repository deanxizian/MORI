"""Candidate actual-solid checks, independent of historical scope gates."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from validate import Solid,intersect_volume
from monocoque_structure import source_build

load_collections()
for n in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[n].hide_viewport=False
assembled();source_build().materials()
if '--native' in sys.argv:
    from native_electronics import apply_native_electronics
    apply_native_electronics();assembled()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.get('role')=='part' and o.get('group') not in ['dock','coupon']}
names={'Pitch_Cradle','Battery_Tray','Battery_Strap','Battery_Pad_Top','Display_Frame','Head_Front','Camera_PCB','Camera_Lens'}|{n for n in ss if n.startswith('CAM_Mount_')}
if '--native' in sys.argv:names|={'Body_IMU','MCU_Carrier','Power_Module','Rear_Interface_PCB','Power_Switch','USB_Receptacle','Load_Frame','Body_Upper'}
hits=[]
for n in sorted(names):
    for k,b in ss.items():
        if n==k or (k in names and k<n):continue
        v=intersect_volume(ss[n],b)
        if v>.01:hits.append({'a':n,'b':k,'volume_mm3':round(v,4),'intersection_bounds_xyz_mm':list((ss[n].m^b.m).bounding_box())})
r={'revision':P['revision'],'source_blend':bpy.data.filepath,'scope':sorted(names),'all_intersections':hits,'threshold_mm3':.01,'note':'Includes declared intended interfaces for human review; does not waive collisions.'}
save_json(ROOT/'reports/completion_candidate_fit.json',r)
print(json.dumps(r,ensure_ascii=False,indent=2),flush=True)
if '--save' in sys.argv:
    write_bom();bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'studies/assembly_completion/candidate.blend'))

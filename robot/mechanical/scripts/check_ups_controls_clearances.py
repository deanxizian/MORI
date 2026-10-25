"""Saved-candidate gaps, connector allocations and sampled head motion."""
from pathlib import Path
import sys,hashlib,json
PROJECT=Path(__file__).resolve().parents[2]
OUT=PROJECT/'mechanical/studies/off_shelf_modules_20261013/ups_controls_M1_57'
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from common import *
from validate import Solid,rigidtr
from validate_off_shelf_modules import raw_solid
record=dict(new_reference_ids=list(P['ups_rear_controls']['reference_ids']))
bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections();assembled();bpy.context.view_layer.update()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ('dock','coupon')}
required_absent=['Rear_Interface_PCB','USB_Receptacle','Power_Switch','Power_Module','Body_IMU','Wheel_Buck','Head_Buck']
assert not (set(required_absent)&set(ss))
assert {'MCU_Carrier','MCU_Motion','UPS_Module','IMU_BMI323','Head_Buck_6V'}<=set(ss)
extras=set(record['new_reference_ids']);sources={n:ss[n].m for n in extras};targets={n:s.m for n,s in ss.items() if n not in extras and n!='Body_Rear'}
plug_path=OUT.parent/'controller_center/connector_review/plug_reservation_meshes.json'
targets|={'Plug/'+n:raw_solid(r) for n,r in json.loads(plug_path.read_text()).items()}
rows=[]
for n,m in sources.items():
    near=[]
    for name,other in targets.items():
        gap=m.min_gap(other,10.)
        if gap<10:near.append(dict(target=name,gap_mm=gap))
    rows.append(dict(part=n,status='PASS' if all(r['gap_mm']>=.3 for r in near) else 'FAIL',nearest=sorted(near,key=lambda r:r['gap_mm'])))
motion=[];count=0
for yaw in range(-60,61,10):
 for pitch in range(-20,26,5):
    count+=1
    for name,s in ss.items():
        if s.group not in ('yaw','pitch'):continue
        tr=np.array(rigidtr(yaw,pitch if s.group=='pitch' else 0),dtype=float)
        moved=s.m.transform(tr[:3,:])
        for n,m in sources.items():
            gap=m.min_gap(moved,.3)
            if gap<.3:motion.append(dict(yaw_deg=yaw,pitch_deg=pitch,part=n,target=name,gap_mm=gap))

result=dict(status='PASS' if not motion and all(r['status']=='PASS' for r in rows) else 'FAIL',
    revision=P['revision'],source_blend_sha256=hashlib.sha256((ROOT/'mori.blend').read_bytes()).hexdigest(),required_free_gap_mm=.3,search_cap_mm=10,static=rows,head_motion=dict(combinations=count,hits=motion,continuous_motion='NOT_TESTED'),
    custom_PCB_count=1,custom_PCB_ids=['MCU_Carrier'],purchased_modules=['MCU_Motion','CAM_Mainboard','Display_PCB','UPS_Module','IMU_BMI323','Head_Buck_6V'],retired_ids_absent=required_absent,
    intentional_contacts_excluded=['Body_Rear mounting annulus','Switch and its retaining nut'],plug_capacity_source_sha256=hashlib.sha256(plug_path.read_bytes()).hexdigest(),
    physical_fit='NOT_TESTED',flexible_leads='BLOCKED',electrical_function='BLOCKED - owner requirements received; native new board and physical qualification pending',formal_adoption=True,manufacturing_release=False,
    script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
save_json(ROOT/'reports/ups_controls_clearances.json',result)
if result['status']!='PASS':raise RuntimeError('Current UPS control clearance failure')
print('UPS_CONTROLS_GAPS',result['status'],rows,'head_positions',count,'hits',len(motion),flush=True)

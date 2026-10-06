"""Saved-solid head sections and endpoint motion; no cable/structural edits."""
from pathlib import Path
import sys,json,hashlib,math,itertools,time
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from common import *
from validate import Solid,rigidtr
from interface_completion import axial
load_collections()
for collection in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[collection].hide_viewport=False
assembled();bpy.context.view_layer.update()
source=Path(bpy.data.filepath);source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
datums=json.loads((HERE/'head_hardware_groups.json').read_text())
assert source_hash==datums['source_blend_sha256']
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.get('group') not in ['dock','coupon']}
ports={(p['object'],p['reference']):p for p in datums['ports']}

def aabb_closest(a,b):
    a,b=np.asarray(a),np.asarray(b);p=[];q=[]
    for i in range(3):
        if a[1,i]<b[0,i]:p.append(a[1,i]);q.append(b[0,i])
        elif b[1,i]<a[0,i]:p.append(a[0,i]);q.append(b[1,i])
        else:
            value=max(a[0,i],b[0,i],min(0.,a[1,i],b[1,i]))
            p.append(value);q.append(value)
    p,q=np.array(p),np.array(q)
    return p,q,float(np.linalg.norm(q-p))

camera_port=ports['CAM_Mainboard','CAMERA_FPC_24']
camera=ss['Camera_PCB']
a,b,lower=aabb_closest(camera_port['bounds_mm'],[camera.lo,camera.hi])
line=axial(.025,lower,(a+b)/2,(b-a)/lower,segments=24)
line_hits=[]
for n,s in ss.items():
    if n=='Camera_PCB':continue
    if np.any(np.maximum(a,b)+.03<s.lo) or np.any(np.minimum(a,b)-.03>s.hi):continue
    vol=max(0.,(line^s.m).volume())
    if vol>1e-6:line_hits.append(dict(object=n,probe_intersection_mm3=vol))

poses=[(y,p) for y in range(-60,61,10) for p in range(-20,26,5)]
motion=[]
for key in ['UART_4P','USB_C','SPEAKER_2P','DISPLAY_FPC_18','CAMERA_FPC_24']:
    row=ports['CAM_Mainboard',key];c=np.mean(row['bounds_mm'],axis=0)
    xyz=[]
    for yaw,pitch in poses:
        tr=np.array(rigidtr(yaw,pitch));xyz.append(tr[:3,:3]@c+tr[:3,3])
    xyz=np.array(xyz)
    motion.append(dict(reference=key,point_basis='Estimated housing AABB center, NOT a wire termination datum',
        zero_center_mm=c.tolist(),sampled_bounds_mm=[xyz.min(0).tolist(),xyz.max(0).tolist()],
        largest_sampled_displacement_from_zero_mm=float(np.linalg.norm(xyz-c,axis=1).max())))
distance_errors=[]
for yaw,pitch in poses:
    tr=np.array(rigidtr(yaw,pitch));aa=tr[:3,:3]@a+tr[:3,3];bb=tr[:3,:3]@b+tr[:3,3]
    distance_errors.append(abs(np.linalg.norm(bb-aa)-lower))

# Meridional cuts are exact sections of the validation solids, with existing
# declared connector proxies. Display-only sections do not replace the model.
tr=np.array([[0,1,0,0],[0,0,1,0],[1,0,0,0]],float)
names=['Head_Front','Head_Rear','Head_Lower_Guard','Pitch_Cradle','Pitch_Yoke',
       'Display_Frame','CAM_Mainboard','Camera_PCB','Camera_Lens','Display_PCB',
       'Yaw_Servo','Pitch_Servo','Yaw_Base','Yaw_Bearing','Yaw_Reaction_Link']
sections=[]
for x in [0.,-18.]:
    layers={}
    for n in names:
        if n not in ss:continue
        s=ss[n];polys=s.m.transform(tr).slice(x).to_polygons()
        if len(polys):layers[n]=dict(group=s.group,polygons_mm=[p.tolist() for p in polys])
    sections.append(dict(x_mm=x,axes=['Y_forward','Z_up'],layers=layers))

out=dict(revision=P['revision'],source_blend_sha256=source_hash,
    source_endpoint_report_sha256=hashlib.sha256((HERE/'head_hardware_groups.json').read_bytes()).hexdigest(),
    endpoint_motion_status='PASS',endpoint_motion_scope='Rigid-group classification and 130 endpoint-position samples only; no routed cable qualification',
    poses=len(poses),endpoints=motion,
    camera_reach=dict(status='BLOCKED',minimum_AABB_separation_mm=lower,minimum_pair_mm=[a.tolist(),b.tolist()],
        available_complete_factory_flex_length_mm=None,
        historical_visible_flex_length_mm=P['waveshare_detail']['camera']['flat_fpc_visible_length_mm'],
        visible_flex_is_complete_length=False,
        same_pitch_group=True,maximum_sampled_pair_distance_error_mm=max(distance_errors),
        straight_line_obstacles=line_hits,probe_radius_mm=.025,
        explanation='AABB distance is a lower bound for these nominal reconstructed objects, not an actual routed length. The thin segment only diagnoses whether the lower-bound shortcut passes through objects. It is not a candidate cable or a cable-clearance check.'),
    LCD_external_FFC_identification=dict(reference='Connector_108',evidence='Vendor CAD left vertical connector, matched to official interface photo; electrical L1, 18 pins. Connector_107 is the panel-internal FPC, not the host connector.',
        image='sources/lcd_connector_photo.webp',status='PASS',mating_exit_and_contacts='BLOCKED'),
    sections=sections,main_geometry_changed=False,
    limits=['CAM and camera geometry is partly photo-estimated; no MEASURED dimensions.',
        'The reconstructed camera-connector latch does not establish the actual cable exit direction.',
        'FFC widths, thicknesses, permitted bends, insertion depths and strain relief remain unspecified.',
        '130 endpoint positions do not certify any continuous cable shape, slack, clearance or fatigue life.'])
(HERE/'head_path_review.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==source_hash
print('HEAD_PATH_REVIEW',json.dumps({k:v for k,v in out.items() if k in ['poses','camera_reach','main_geometry_changed']},ensure_ascii=False),flush=True)

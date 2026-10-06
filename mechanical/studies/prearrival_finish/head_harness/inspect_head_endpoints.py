"""Read saved head hardware groups and documented/estimated port datums only."""
from pathlib import Path
import sys,json,hashlib
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from common import *
from validate import Solid,rigidtr
load_collections()
# Hidden validation collections must be evaluated before reading world-space
# geometry; otherwise Blender can retain stale proxy transforms from creation.
for collection in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[collection].hide_viewport=False
assembled();bpy.context.view_layer.update()
source=Path(bpy.data.filepath);source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
names=['Yaw_Servo','Pitch_Servo','CAM_Mainboard','Display_PCB','Camera_PCB','Speaker','Yaw_Base','Pitch_Yoke','Pitch_Cradle','Yaw_Output','Pitch_Output','Body_Upper']
rows=[]
for name in names:
    o=bpy.data.objects.get(PREFIX+name)
    if o is None:
        rows.append(dict(name=name,exists=False));continue
    s=Solid(o)
    rows.append(dict(name=name,exists=True,group=o.get('group'),data_status=o.get('data_status'),
        bounds_mm=[s.lo.tolist(),s.hi.tolist()],matrix_world=[list(v) for v in o.matrix_world],
        custom_properties={k:str(o[k]) for k in o.keys() if any(t in k for t in ['source','evidence','datum','model'])}))
ports=[]
cam_refs={'CAMERA_FPC_24','DISPLAY_FPC_18','USB_C','UART_4P','SPEAKER_2P'}
for name in ['CAM_Mainboard','Display_PCB']:
    o=bpy.data.objects[PREFIX+name];records=json.loads(o['component_reference_index'])
    for row in records:
        if (name=='CAM_Mainboard' and row['reference'] not in cam_refs) or (name=='Display_PCB' and row['reference'] not in ['Connector_107','Connector_108','CAD_solid_109','CAD_solid_110']):continue
        start,end=row['vertices'];vs=np.array([tuple(o.matrix_world@o.data.vertices[i].co) for i in range(start,end)])
        ports.append(dict(object=name,reference=row['reference'],group=o.get('group'),
            bounds_mm=[vs.min(0).tolist(),vs.max(0).tolist()],source_evidence=row['evidence'],
            limitations=row.get('limitations'),source_vertex_count=len(vs)))
out=dict(source_blend_sha256=source_hash,revision=P['revision'],parts=rows,ports=ports,
    motion_axes_mm=dict(head_pitch_origin=[0,0,D['head_z']],yaw_axis='+Z',yaw_bearing_z=D['yaw_bearing_z']),
    note='Port coordinates still require vendor datum mapping; bounds are not wire exit datums.',main_modified=False)
(HERE/'head_hardware_groups.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==source_hash
for r in rows:print(r['name'],r.get('group'),r.get('bounds_mm'),flush=True)

"""Actual before/after support renders with identical visibility and camera.

The immutable M1.4 model and current delivered model use identical cameras.
Opening the baseline is read-only; no historical render is called current.
"""
import sys,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import common as c
import build as b
from render import camera

out=c.ROOT/'renders/structure';out.mkdir(parents=True,exist_ok=True)
names={'Pitch_Cradle','Camera_Mount','CAM_Mainboard_Mount','Display_Frame',
       'Pitch_Yoke','Pitch_Servo_Mount','Yaw_Carrier','Load_Frame','Battery_Tray',
       'Motor_Mount_L','Motor_Mount_R','Yaw_Turntable','Yaw_Servo_Mount',
       'MCU_Mount_Motion','IMU_Mount','Power_Module_Mount','USB_Charge_Mount','Head_Lower_Guard','Motor_Retainer','Yaw_Stop_-76','Yaw_Stop_76','Drive_Bridge','Body_Cheek_L','Body_Cheek_R','Yaw_Base'}
views={'whole':((340,510,320),(0,0,145),295),
       'deck':((230,390,205),(0,0,134),150)}
records=[]
audit_path=c.ROOT/'reports/structure_changes.json';current_audit=audit_path.read_bytes()
for version in ['before','after']:
    if version=='before':
        baseline=c.PROJECT/c.P['structure']['comparison_baseline']['blend']
        c.bpy.ops.wm.open_mainfile(filepath=str(baseline))
        c.bpy.context.window.scene=c.bpy.data.scenes['MORI_V1_Assembly'];c.load_collections();sc=c.bpy.context.scene
        provenance='Archived M1.4 actual model SHA256 '+hashlib.sha256(baseline.read_bytes()).hexdigest()
    else:
        c.P['structure']['architecture']='simple_modules'
        c.bpy.ops.wm.open_mainfile(filepath=str(c.ROOT/'mori_v1_2.blend'))
        c.bpy.context.window.scene=c.bpy.data.scenes['MORI_V1_Assembly'];c.load_collections()
        sc=c.bpy.context.scene
        provenance='Current delivered .blend SHA256 '+hashlib.sha256((c.ROOT/'mori_v1_2.blend').read_bytes()).hexdigest()
    c.assembled();sc.render.engine='CYCLES';sc.cycles.samples=24;sc.cycles.use_denoising=True
    sc.render.resolution_x=1000;sc.render.resolution_y=1000;sc.render.resolution_percentage=100
    for collection in ['DATUMS','KEEP_OUT','COUPONS','ANNOTATIONS','DOCK']:c.COLS[collection].hide_render=True
    c.bpy.data.objects[c.PREFIX+'Studio_Ground'].hide_render=True
    for view,args in views.items():
        visible=[]
        for o in sc.objects:
            if o.get('role') not in ['part','routing','display_content']:continue
            n=o.name.removeprefix(c.PREFIX)
            show=n in names or n.startswith('Battery_Hanger_')
            if view=='deck':show=n in {'Load_Frame','Body_Cheek_L','Body_Cheek_R','Yaw_Base','Yaw_Servo','Yaw_Output','Yaw_Horn','Yaw_Bearing','Battery'}
            o.hide_render=not show
            if show:visible.append(n)
        camera('structure_'+version+'_'+view,*args)
        path=out/f'{version}_{view}.png';sc.render.filepath=str(path)
        c.bpy.ops.render.render(write_still=True)
        records.append({'version':version,'view':view,'file':str(path.relative_to(c.ROOT)),
                        'visible_parts':sorted(visible),'provenance':provenance,
                        'camera':args,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
audit_path.write_bytes(current_audit)
c.save_json(c.ROOT/'reports/structure_render_comparison.json',{'records':records,
    'meaning':'Actual Blender geometry; camera/scale identical. Exterior and electronics hidden to expose supports. Geometry change is not measured strength proof.'})
print('STRUCTURE_COMPARISON_COMPLETE',flush=True)

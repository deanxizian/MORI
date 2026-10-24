"""Current saved-main views; no independent candidate geometry or model writes."""
import sys,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *

source=ROOT/'mori_v1_2.blend';digest=hashlib.sha256(source.read_bytes()).hexdigest()
out=ROOT/'renders'/('ups_controls_M1_58' if P.get('ups_rear_controls',{}).get('enabled') else 'dc_trial_M1_57' if P.get('dc_inlet_trial',{}).get('enabled') else 'off_shelf_M1_56');out.mkdir(parents=True,exist_ok=True)
scene=bpy.data.scenes['MORI_V1_Assembly'];bpy.context.window.scene=scene;load_collections();assembled()
native={o.name.removeprefix(PREFIX):o for o in parts() if o.get('group') not in ('dock','coupon')}
for c in COLS.values():c.hide_viewport=False
for o in scene.objects:o.hide_render=True
for k in ['PRINTABLE','PURCHASED_REFERENCE','PLACEHOLDER']:COLS[k].hide_render=False
data=bpy.data.cameras.new('M1_56_REVIEW_CAMERA');cam=bpy.data.objects.new('M1_56_REVIEW_CAMERA',data)
scene.collection.objects.link(cam);scene.camera=cam;data.type='ORTHO';data.clip_start=.1;data.clip_end=5000
scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=1440;scene.render.resolution_y=1080;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.display.render_aa='16'
sh=scene.display.shading;sh.light='STUDIO';sh.color_type='MATERIAL';sh.show_shadows=True;sh.show_cavity=True;sh.cavity_type='BOTH'
sh.background_type='VIEWPORT';sh.background_color=(.88,.90,.92)
q=P['off_shelf_modules'];rows=[]
upper=set(q['controller_group_ids'])|{'Load_Frame','IMU_BMI323','Head_Buck_6V'}|{n for n in native if n.startswith(('BMI323_','Buck6V_'))}
ups={'UPS_Module','Load_Frame'}|{n for n in native if n.startswith('UPS_Direct_')}
views=[
 ('assembled',(380,510,335),(0,0,145),420,set(native)),
 ('internal',(340,510,325),(0,0,143),400,set(native)-set(body_shell_names())-{'Head_Front','Head_Rear'}),
 ('top_modules',(100,60,480),(0,-6,116),132,upper),
 ('ups_direct',(195,275,35),(0,-8,96),185,{n for n,o in native.items() if bounds(o)[2][0]<147}-set(body_shell_names())),
 ('ups_joint',(90,120,44),(23,31,105),61,ups),
 ('load_frame',(180,240,10),(0,-5,108),163,{'Load_Frame'}),
]
if P.get('dc_inlet_trial',{}).get('enabled'):
    views += [
        ('dc_seat',(95,-250,190),(0,-73.8,129.8),60,{'Body_Rear'}),
        ('dc_inside',(55,60,174),(0,-73.8,129.8),80,{'Body_Rear'}|set(P['dc_inlet_trial']['reference_ids'])),
    ]
if P.get('ups_rear_controls',{}).get('enabled'):
    ids={'Body_Rear'}|set(P['dc_inlet_trial']['reference_ids'])|set(P['ups_rear_controls']['reference_ids'])
    views=[v for v in views if not v[0].startswith('dc_')]
    views += [('controls_rear',(42,-250,155),(0,-75,120),77,ids),('controls_inside',(52,65,157),(0,-74,120),91,ids),('controls_shell',(35,-250,153),(0,-75,120),77,{'Body_Rear'})]
for name,loc,target,scale,visible in views:
    for n,o in native.items():o.hide_render=n not in visible;o.hide_set(False)
    for o in scene.objects:
        if o.get('role')=='display_content':o.hide_render=name in ['top_modules','ups_direct','ups_joint','load_frame']
    cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();data.ortho_scale=scale
    scene.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
    image_path=Path(scene.render.filepath)
    rows.append(dict(file=str(image_path.relative_to(ROOT)),sha256=hashlib.sha256(image_path.read_bytes()).hexdigest(),bytes=image_path.stat().st_size,visible_ids=sorted(visible),camera_mm=loc,target_mm=target))
assert hashlib.sha256(source.read_bytes()).hexdigest()==digest
save_json(ROOT/'reports/off_shelf_render_manifest.json',dict(revision=P['revision'],source_blend_sha256=digest,
    geometry='All visible part meshes and poses from the saved main model, no candidate substitutions',views=rows))
print('OFF_SHELF_CURRENT_VIEWS_COMPLETE',len(rows),flush=True)

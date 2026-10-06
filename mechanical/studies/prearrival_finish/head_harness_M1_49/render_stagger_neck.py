"""Preview the verified local neck segment, with open ends explicitly retained."""
from pathlib import Path
import json,sys
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
OUT=HERE/'remaining_routes/stagger_neck_spk26_phase2'
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import bpy,COLS
from render import camera
ctx=Context();report=json.loads((OUT/'neck_screen.json').read_text())
assert report['status']=='PASS'
for f,h in {**report['sources'],**report['inputs']}.items():assert sha(PROJECT/f)==h,f
data=np.load(OUT/'neck_candidates.npz');assert sha(OUT/'neck_candidates.npz')==report['curve_sha256']
tag='MORI_STAGGER_NECK_STUDY_149__';new=[]
for o in list(bpy.data.objects):
    if o.name.startswith(tag):bpy.data.objects.remove(o,do_unlink=True)
for i in range(11):
    p=data[f'z147.0_dip0.6_wire{i}_y0'];radius=report['OD_mm'][i]/2
    cu=bpy.data.curves.new(tag+str(i),'CURVE');cu.dimensions='3D';cu.bevel_depth=radius;cu.bevel_resolution=3;cu.use_fill_caps=True
    sp=cu.splines.new('POLY');sp.points.add(len(p)-1)
    for v,q in zip(sp.points,p):v.co=(*q,1)
    o=bpy.data.objects.new(tag+str(i),cu);bpy.context.scene.collection.objects.link(o)
    o.color=(1.,.45,.06,1) if i<7 else (1.,.73,.18,1)
    o['category']='PLACEHOLDER';o['data_status']='ASSUMED';o['robot_part']=False
    o['scope']='Unselected wire reference; neck segment only, open ends, no complete harness or anchor approval'
    new.append(o)
for c in COLS.values():c.hide_viewport=False;c.hide_render=False
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.color_type='OBJECT'
scene.display.shading.light='STUDIO';scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
scene.display.shading.show_shadows=True;scene.display.shading.show_specular_highlight=False
scene.display.shading.background_type='WORLD';scene.world.color=(.81,.85,.87);scene.view_settings.view_transform='Standard'
scene.render.film_transparent=False;scene.render.resolution_x=1200;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';images=[]
for name,keep,eye,target,scale in [
    ('neck_entry',{'Yaw_Base','Yaw_Anti_Lift_Keeper','Yaw_Bearing','Power_Module','MCU_Carrier'},(150,-180,155),(0,0,159),88),
    ('neck_exposed',{'Yaw_Bearing','Power_Module','MCU_Carrier'},(120,-180,226),(0,0,170),94)]:
    for o in scene.objects:
        if o.type in ['MESH','CURVE','FONT']:o.hide_render=True
    for n,s in ctx.ss.items():
        s.o.hide_render=n not in keep
        if s.o.get('category')=='PRINTABLE':s.o.color=(.54,.62,.64,1)
    for o in new:o.hide_render=False;o.hide_set(False)
    cam=camera(tag+name,eye,target,scale);cam.data.clip_start=.1
    scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
    images.append(dict(file=name+'.png',sha256=sha(OUT/(name+'.png')),visible_native_parts=sorted(keep)))
ctx.assert_unchanged();dest=OUT/'MORI_M1_49_staggered_neck_study.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(dest));ctx.assert_unchanged()
manifest=dict(status='PASS',scope='Local preview generation only; open ends are not final wire terminals',
    sources=ctx.sources,inputs={str(p.relative_to(PROJECT)):sha(p) for p in [OUT/'neck_screen.json',OUT/'neck_candidates.npz']},
    images=images,blend_sha256=sha(dest),main_changed=False,full_harness='BLOCKED',script_sha256=sha(Path(__file__)))
(OUT/'render_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

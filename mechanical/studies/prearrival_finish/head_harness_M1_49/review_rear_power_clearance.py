"""Publish the accepted local eleven-path candidate without changing main."""
from pathlib import Path
import itertools,json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes/rear_power_bump';OUT=BASE/'review';OUT.mkdir(exist_ok=True)
PREV=HERE/'remaining_routes/rear_separated_neck/review'
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from common import bpy,COLS
from render import camera
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text());report=read(BASE/'neck_screen.json');previous=read(PREV/'review.json')
for r in [report,previous]:
    for f,h in {**r['sources'],**r['inputs']}.items():assert sha(ROOT/f)==h,f
assert report['status']=='PASS' and previous['ten_local_paths']=='PASS'
assert sha(BASE/'curves.npz')==report['curve_sha256'] and sha(PREV/'curves.npz')==previous['curve_sha256']
now=np.load(BASE/'curves.npz');old=np.load(PREV/'curves.npz');case=next(r for r in report['results'] if r['status']=='PASS')
for s,y in itertools.product(range(11),range(-60,61,10)):
    a=now[f'wire{s}_y{y}'];b=old[f'wire{s}_y{y}']
    if s!=5:assert np.array_equal(a,b)
    else:assert np.array_equal(a[a[:,2]<=177.],b[b[:,2]<=177.])
tree=ctx.targets['Pitch_Yoke']['tree'];points=now['wire5_y0'];d,i=min((float(tree.find_nearest(v)[3]),i) for i,v in enumerate(points.tolist()))
tag='MORI_REAR_NECK_LOCAL__';new=[]
for s in range(11):
    p=now[f'wire{s}_y0'];cu=bpy.data.curves.new(tag+str(s),'CURVE');cu.dimensions='3D';cu.bevel_depth=report['OD_mm'][s]/2;cu.bevel_resolution=3;cu.use_fill_caps=True
    sp=cu.splines.new('POLY');sp.points.add(len(p)-1)
    for v,point in zip(sp.points,p):v.co=(*point,1)
    o=bpy.data.objects.new(tag+'slot'+str(s),cu);bpy.context.scene.collection.objects.link(o)
    o.color=(.10,.73,.28,1) if s==5 else (.05,.67,.74,1) if s>=7 else (1.,.55,.07,1)
    o['robot_part']=False;o['category']='PLACEHOLDER';o['data_status']='ASSUMED';o['scope']='Local neck candidate only, incomplete endpoints and variable path length';new.append(o)
for c in COLS.values():c.hide_viewport=False;c.hide_render=False
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.color_type='OBJECT';scene.display.shading.light='STUDIO'
scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH';scene.display.shading.show_shadows=True;scene.display.shading.show_specular_highlight=False
scene.display.shading.background_type='WORLD';scene.world.color=(.86,.88,.90);scene.view_settings.view_transform='Standard';scene.render.film_transparent=False
scene.render.resolution_x=1200;scene.render.resolution_y=1000;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';images=[]
for name,eye,target,scale in [('rear_neck_overview',(80,-135,237),(-5,-5,177),82),('rear_neck_clearance',(-78,-120,248),(-8,-9,195),39)]:
    for o in scene.objects:
        if o.type in ['MESH','CURVE','FONT']:o.hide_render=True
    for n in ['Pitch_Yoke','Yaw_Bearing','Yaw_Servo','Pitch_Servo','CAM_Mainboard']:
        ctx.ss[n].o.hide_render=False
        if n=='Pitch_Yoke':ctx.ss[n].o.color=(.57,.62,.64,1)
    for o in new:o.hide_render=False;o.hide_set(False)
    cam=camera(tag+name,eye,target,scale);cam.data.clip_start=.1;scene.render.filepath=str(OUT/(name+'.png'))
    bpy.ops.render.render(write_still=True);images.append(dict(file=name+'.png',sha256=sha(OUT/(name+'.png'))))
ctx.assert_unchanged();blend=OUT/'MORI_M1_49_rear_neck_local.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend));ctx.assert_unchanged()
inputs=[BASE/'neck_screen.json',BASE/'curves.npz',PREV/'review.json',PREV/'curves.npz']
r=dict(status='PASS',sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},images=images,blend_sha256=sha(blend),
       scope='Delivery of local eleven-path geometry only; green path identifies the changed power conductor, not full harness qualification.',
       unchanged_other_path_arrays=130,unchanged_slot5_through_z_mm=177.,new_native_checks=case['native_checks'],new_pairs=len(case['pairs']),retained_other_pairs=585,
       pair_gap_lower_bound_mm=min(x['gap_lower_bound_mm'] for x in case['pairs']),
       zero_pose_power_yoke_minimum_sampled_gap_mm=d-report['OD_mm'][5]/2,minimum_distance_point_mm=points[i].tolist(),
       main_changed=False,C6_main_applied=False,full_harness='BLOCKED',constant_length='BLOCKED',wired_assembly='NOT_TESTED',
       script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(r,indent=2)+'\n');print('REAR_NECK_LOCAL_DELIVERY',r['status'],r['zero_pose_power_yoke_minimum_sampled_gap_mm'],flush=True)

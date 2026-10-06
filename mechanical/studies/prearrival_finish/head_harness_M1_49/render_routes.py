"""Independent current-source route preview. Never saves over the main blend."""
from pathlib import Path
import sys,json
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import *
from render import camera
ctx=Context()
r=json.loads((HERE/'body_layered_four_screen.json').read_text())
motion=json.loads((HERE/'current_source_verification.json').read_text())
assert r['status']==motion['status']=='PASS'
for p,h in motion['sources'].items():assert sha(PROJECT/p)==h,p
for p,h in motion['inputs'].items():assert sha(HERE/p)==h,p
signals=np.load(HERE/'body_layered_four_candidates.npz');assert sha(HERE/'body_layered_four_candidates.npz')==r['curve_sha256']
neck=np.load(HERE/'spaced_entry_candidates.npz');profile=json.loads((HERE/'spaced_entry_screen.json').read_text())
assert sha(HERE/'spaced_entry_candidates.npz')==profile['curve_file_sha256']
by_slot={row['slot']:row for row in r['selected']}
tag='MORI_ROUTE_149__';wire_objs=[]
for o in list(bpy.data.objects):
    if o.name.startswith(tag):bpy.data.objects.remove(o,do_unlink=True)
colors=[(.12,.68,.88,1),(.42,.27,.8,1),(.08,.62,.38,1),(.9,.2,.47,1)]
for i,allocation in enumerate(P['neck_harness_capacity']['wire_allocations']):
    row=by_slot.get(i)
    points=signals[f'pin{row["pin"]}_y0'] if row else neck[f'case0_wire{i}_y0']
    label=f'Motion_J5_pin{row["pin"]}_to_neck_only' if row else f'Capacity_wire{i}_local_only'
    cu=bpy.data.curves.new(tag+label,'CURVE');cu.dimensions='3D';cu.bevel_depth=allocation['OD_mm']/2
    cu.bevel_resolution=3;cu.use_fill_caps=True
    sp=cu.splines.new('POLY');sp.points.add(len(points)-1)
    for target,p in zip(sp.points,points):target.co=(*p,1)
    o=bpy.data.objects.new(tag+label,cu);bpy.context.scene.collection.objects.link(o)
    o.color=colors[row['pin']-1] if row else (.93,.44,.09,1)
    o['category']='PLACEHOLDER';o['data_status']='ASSUMED';o['role']='partial_route_candidate'
    o['robot_part']=False;o['full_harness']='BLOCKED';o['not_cut_length']=True
    o['scope']='Partial route; selected only for independent geometric study, not added to main model'
    wire_objs.append(o)
for c in COLS.values():c.hide_viewport=False;c.hide_render=False
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH'
scene.display.shading.color_type='OBJECT';scene.display.shading.light='STUDIO'
scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
scene.display.shading.show_shadows=True;scene.display.shading.show_specular_highlight=False
scene.display.shading.background_type='WORLD';scene.world.color=(.81,.85,.87)
scene.view_settings.view_transform='Standard';scene.render.film_transparent=False
scene.render.resolution_x=1280;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
records=[]
def view(name,keep,eye,target,scale):
    for o in scene.objects:
        if o.type in ['MESH','CURVE','FONT']:o.hide_render=True
    for n,s in ctx.ss.items():
        visible=n in keep;s.o.hide_render=not visible
        if s.o.get('category')=='PRINTABLE':s.o.color=(.54,.62,.64,1)
    for o in wire_objs:o.hide_render=False;o.hide_set(False)
    cam=camera('Route149_'+name,eye,target,scale);cam.data.clip_start=.1
    scene.render.filepath=str(HERE/(name+'.png'));bpy.ops.render.render(write_still=True)
    records.append(dict(file=name+'.png',sha256=sha(HERE/(name+'.png')),visible_native_parts=sorted(keep),scope='Zero-pose partial routes; omitted solids still included in recorded checks'))
boards={'Power_Module','MCU_Carrier','MCU_Motion','Load_Frame','Yaw_Bearing'}
view('body_to_neck',boards|{'Yaw_Base','Yaw_Anti_Lift_Keeper','Pitch_Yoke'},(190,-270,225),(0,-8,151),156)
view('paths_exposed',boards,(190,-270,225),(0,-8,151),156)
bpy.context.view_layer.update()
ctx.assert_unchanged()
out=HERE/'MORI_M1_49_partial_harness_review.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(out))
ctx.assert_unchanged()
(HERE/'render_manifest.json').write_text(json.dumps(dict(status='PASS',source_blend_sha256=ctx.source_hash,source_report_sha256=sha(HERE/'current_source_verification.json'),images=records,blend_sha256=sha(out),script_sha256=sha(Path(__file__)),main_changed=False,full_harness='BLOCKED'),ensure_ascii=False,indent=2)+'\n')
print('PARTIAL_HARNESS_RENDERED',len(records),flush=True)

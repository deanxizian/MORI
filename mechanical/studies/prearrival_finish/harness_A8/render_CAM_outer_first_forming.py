"""Render the saved finite 3->2->1->0 forming sequence as an independent study."""
from pathlib import Path
OR_SCRIPT=Path(__file__).resolve();OR_ROOT=OR_SCRIPT.parent
OR_HELPER=OR_ROOT/'plan_CAM_direct_angle_forming.py';__file__=str(OR_HELPER)
exec(compile(OR_HELPER.read_text().split('\nda_grid=',1)[0],str(OR_HELPER),'exec'),globals())
__file__=str(OR_SCRIPT)
from common import material,parts
from render import camera
from validate_head_cleanup import geometry_record
OR_OUT=L2_OUT/'outer_first_forming';or_path=json.loads((OR_OUT/'screen.json').read_text())
assert or_path['status']=='PASS'
or_source={o.name:geometry_record(o) for o in parts()};or_moving=[];or_images=[]
for o in bpy.context.scene.objects:
    if o.type in ['MESH','CURVE','FONT']:o.hide_render=True
or_colors=[(.05,.58,.67),(.9,.24,.08),(.3,.64,.12),(.65,.28,.8)]


def or_mesh(name,m,color):
    a=m.to_mesh64();d=bpy.data.meshes.new('A8_ORDER_'+name)
    d.from_pydata(a.vert_properties[:,:3].tolist(),[],a.tri_verts.tolist());d.update()
    o=bpy.data.objects.new('A8_ORDER_'+name,d);bpy.context.scene.collection.objects.link(o)
    d.materials.append(material('A8_ORDER_MAT_'+name,color,roughness=.45))
    o['study_owner']='CAM_OUTER_FIRST';o['part_class']='PLACEHOLDER';o['data_status']='ASSUMED'
    return o


def or_wire(name,p,color):
    d=bpy.data.curves.new('A8_ORDER_'+name,'CURVE');d.dimensions='3D';d.bevel_depth=OD/2.;d.bevel_resolution=3;d.use_fill_caps=True
    sp=d.splines.new('POLY');sp.points.add(len(p)-1)
    for q,v in zip(sp.points,p):q.co=(*v,1.)
    o=bpy.data.objects.new('A8_ORDER_'+name,d);bpy.context.scene.collection.objects.link(o)
    d.materials.append(material('A8_ORDER_MAT_'+name,color,roughness=.4))
    o['study_owner']='CAM_OUTER_FIRST';o['part_class']='PLACEHOLDER';o['data_status']='ASSUMED'
    return o


show={'Pitch_Yoke','Pitch_Cradle','Pitch_Servo','Yaw_Servo','Yaw_Reaction_Link','Yaw_Base',
      'Yaw_Axial_Keeper','Yaw_Bearing','Pitch_Bearing_L','Pitch_Bearing_R','CAM_Tie_Head','CAM_Tie_Band'}
for name,group,m,*_ in fm_targets:
    if name in show:or_mesh(name,m,(.53,.56,.58) if 'Servo' in name else (.17,.26,.29))
for slot in range(4):or_wire(f'upstream_{slot}',pw_fans[slot][0],or_colors[slot])


def or_pose(stage,f):
    global st_angle_max,fc_amplitude
    for o in or_moving:bpy.data.objects.remove(o,do_unlink=True)
    or_moving.clear();s=or_path['stages'][stage];active=s['active_slot']
    n=next(n for n in s['path'] if abs(n['fraction']-f)<1e-8)
    phases=[]
    for slot in range(4):
        phase=f if slot==active else (1. if or_path['wire_order'].index(slot)<stage else 0.)
        st_angle_max=n['side_angle_deg'] if slot==active else 0.;fc_amplitude=n['amplitude_mm'] if slot==active else 9.
        p,u,e=fc_curve(phase);p=p+[xx[slot]-xx[0],0.,0.]
        or_moving.append(or_wire(f'free_{slot}',p,or_colors[slot]))
        _,tr=ft_frame(phase,p[-1]);or_moving.append(or_mesh(f'nominal_terminal_{slot}',ft_box.transform(tr),(.87,.62,.24)))
        phases.append(phase)
    return n,phases


scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
scene.render.resolution_x=1100;scene.render.resolution_y=1050;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.threads_mode='FIXED';scene.render.threads=4
for label,stage,f,eye,target,scale in [
    ('start',0,0.,(-150,180,371),(-8,0,269),165),
    ('last_wire_sideways',3,.775,(-110,112,304),(-8,0,236),101),
    ('all_four_positioned',3,1.,(-103,113,292),(-8,0,233),101)]:
    n,phases=or_pose(stage,f);camera('A8_ORDER_CAMERA',eye,target,scale)
    scene.render.filepath=str(OR_OUT/(label+'.png'));bpy.ops.render.render(write_still=True)
    or_images.append({'file':label+'.png','sha256':sha(OR_OUT/(label+'.png')),'stage':stage,'active_slot':or_path['wire_order'][stage],
        'fraction':f,'amplitude_mm':n['amplitude_mm'],'side_angle_deg':n['side_angle_deg'],'all_free_wire_phases':phases,
        'all_four_wires_and_contacts_present':True,'shown_structure_subset':sorted(show),'inspection_exclusions_changed':False})
assert all(geometry_record(o)==or_source[o.name] for o in parts() if o.name in or_source)
scene['independent_study']='Finite nominal four-wire forming order; continuous motion, terminal insertion and complete harness remain unqualified.'
scene['wire_order']='3,2,1,0 (geometric slots, not electrical pin numbers)'
scene.render.use_file_extension=True;bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OR_OUT/'review.blend'))
(OR_OUT/'render_manifest.json').write_text(json.dumps({'status':'PASS','script_sha256':sha(OR_SCRIPT),'helper_sha256':sha(OR_HELPER),
    'source_main_sha256':source_hash,'source_path_sha256':sha(OR_OUT/'screen.json'),'images':or_images,
    'physical_source_objects_preserved':len(or_source),'review_sha256':sha(OR_OUT/'review.blend'),
    'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False},ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('OUTER_FIRST_RENDER_DONE',len(or_images),flush=True)

"""Render actual forming-stage solids and the catalogue contact envelopes."""
from pathlib import Path
VT_SCRIPT=Path(__file__).resolve();VT_ROOT=VT_SCRIPT.parent
VT_HELPER=VT_ROOT/'check_CAM_forming_terminals.py';__file__=str(VT_HELPER)
exec(compile(VT_HELPER.read_text().split('\nfor fraction in np.linspace',1)[0],str(VT_HELPER),'exec'),globals())
__file__=str(VT_SCRIPT)
from common import material,parts
from render import camera
from validate_head_cleanup import geometry_record
VT_OUT=FM_OUT/'terminals';vt_source={o.name:geometry_record(o) for o in parts()}
for o in bpy.context.scene.objects:
    if o.type in ['MESH','CURVE','FONT']:o.hide_render=True
vt_show={'Pitch_Yoke','Pitch_Cradle','Pitch_Servo','Yaw_Servo','Yaw_Reaction_Link','Yaw_Base',
 'Yaw_Axial_Keeper','Yaw_Bearing','Pitch_Bearing_L','Pitch_Bearing_R','CAM_Tie_Head','CAM_Tie_Band'}
vt_objects=[];vt_hashes={};vt_moving=[]


def vt_mesh(name,m,color):
    mesh=m.to_mesh64();d=bpy.data.meshes.new('A8_CONTACT_FORMING_'+name)
    d.from_pydata(mesh.vert_properties[:,:3].tolist(),[],mesh.tri_verts.tolist());d.update()
    o=bpy.data.objects.new('A8_CONTACT_FORMING_'+name,d);bpy.context.scene.collection.objects.link(o)
    d.materials.append(material('A8_CONTACT_MAT_'+name,color,roughness=.45))
    o['study_owner']='CAM_FORMING_CONTACT_REVIEW';o['part_class']='PLACEHOLDER';o['data_status']='ASSUMED'
    return o


for name,group,m,*_ in fm_targets:
    if name not in vt_show:continue
    color=(.54,.57,.59) if 'Servo' in name else (.15,.25,.28)
    if name=='Yaw_Reaction_Link':color=(.84,.44,.12)
    if name.startswith('CAM_Tie_'):color=(.88,.69,.22)
    o=vt_mesh(name,m,color);vt_objects.append(o)
    a=m.to_mesh64();vt_hashes[name]=hashlib.sha256(a.vert_properties[:,:3].tobytes()+a.tri_verts.tobytes()).hexdigest()


def vt_pose(fraction,amplitude,housing=False):
    for o in vt_moving:bpy.data.objects.remove(o,do_unlink=True)
    vt_moving.clear();base,parameter,error,extra=fr_curve(fraction,amplitude)
    colors=[(.06,.57,.66),(.9,.23,.07),(.28,.62,.1),(.63,.25,.77)]
    for slot in range(4):
        points=base+[xx[slot]-xx[0],0.,0.];d=bpy.data.curves.new(f'A8_CONTACT_WIRE{slot}','CURVE')
        d.dimensions='3D';d.bevel_depth=OD/2.;d.bevel_resolution=3;d.use_fill_caps=True
        sp=d.splines.new('POLY');sp.points.add(len(points)-1)
        for q,p in zip(sp.points,points):q.co=(*p,1.)
        o=bpy.data.objects.new(f'A8_CONTACT_WIRE{slot}',d);bpy.context.scene.collection.objects.link(o)
        d.materials.append(material(f'A8_CONTACT_WIRE_MAT{slot}',colors[slot],roughness=.4));vt_moving.append(o)
        o['study_owner']='CAM_FORMING_CONTACT_REVIEW';o['part_class']='PLACEHOLDER';o['data_status']='ASSUMED'
        if not housing:
            rot,tr=ft_frame(fraction,points[-1]);vt_moving.append(vt_mesh('SSH_BOX_'+str(slot),ft_box.transform(tr),(.85,.58,.19)))
    if housing:
        rot,_=ft_frame(fraction,base[-1]);tr=np.column_stack([rot,base[-1]-rot@ft_final])
        vt_moving.append(vt_mesh('SH_HOUSING',bl_plug.transform(tr),(.9,.67,.27)))
    return base


scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
scene.render.resolution_x=1100;scene.render.resolution_y=950;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';vt_images=[]
for label,fraction,amp,housing,eye,target,scale in [
    ('loose_terminals',.975,9.,False,(-82,62,263),(-10,-17,213),47),
    ('housing_collision',.825,12.,True,(-92,52,258),(-7,8,213),63),
    ('forming_overview',.825,9.,False,(-130,100,330),(-7,0,218),116)]:
    base=vt_pose(fraction,amp,housing)
    isolated=None
    if label=='loose_terminals':
        isolated={'Pitch_Cradle'};target=base[-1]+[1.5,0.,0.];eye=target+[30.,40.,-20.];scale=31.
    elif label=='housing_collision':
        isolated={'Pitch_Servo'};target=base[-1]+[1.5,0.,0.];eye=target+[-30.,20.,-25.];scale=28.
    for o in vt_objects:
        name=o.name.removeprefix('A8_CONTACT_FORMING_');o.hide_render=isolated is not None and name not in isolated
    camera('A8_CONTACT_REVIEW_CAMERA',eye,target,scale)
    scene.render.filepath=str(VT_OUT/(label+'.png'));bpy.ops.render.render(write_still=True)
    vt_images.append({'file':label+'.png','sha256':sha(VT_OUT/(label+'.png')),'fraction':fraction,'amplitude_mm':amp,'housing_present':housing,
        'isolated_view':isolated is not None,'displayed_structure_subset':sorted(isolated) if isolated else sorted(vt_show),
        'inspection_exclusions_changed':False})
vt_pose(1.,9.,False);camera('A8_CONTACT_REVIEW_CAMERA',(-130,100,330),(-7,0,218),116)
for o in vt_objects:o.hide_render=False
assert all(geometry_record(o)==vt_source[o.name] for o in parts() if o.name in vt_source)
scene['independent_study']='Nominal catalogue contact boxes, not detailed crimp CAD. M1.47 unchanged; full harness remains incomplete.'
bpy.ops.wm.save_as_mainfile(filepath=str(VT_OUT/'review.blend'))
(VT_OUT/'render_manifest.json').write_text(json.dumps({'status':'PASS','script_sha256':sha(VT_SCRIPT),'helper_sha256':sha(VT_HELPER),
 'source_main_sha256':source_hash,'source_terminal_screen_sha256':sha(VT_OUT/'screen.json'),
 'source_housed_screen_sha256':sha(FM_OUT/'housed/screen.json'),'source_solids_sha256':vt_hashes,
 'physical_source_objects_preserved':len(vt_source),'images':vt_images,'review_sha256':sha(VT_OUT/'review.blend'),
 'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False},ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('FORMING_CONTACT_RENDER_DONE',len(vt_images),flush=True)

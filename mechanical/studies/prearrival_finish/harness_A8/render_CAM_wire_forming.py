"""Render the tested failed/screened forming paths using their actual solids."""
from pathlib import Path
FV_SCRIPT=Path(__file__).resolve();FV_ROOT=FV_SCRIPT.parent
FV_HELPER=FV_ROOT/'screen_CAM_wire_forming_raised.py';__file__=str(FV_HELPER)
exec(compile(FV_HELPER.read_text().split('\nfor amplitude in [',1)[0],str(FV_HELPER),'exec'),globals())
__file__=str(FV_SCRIPT)
from common import material,parts,PREFIX
from render import camera
from validate_head_cleanup import geometry_record
fv_base={o.name:geometry_record(o) for o in parts()}
fv_report=json.loads((FR_OUT/'screen.json').read_text());assert fv_report['status']=='PASS'
fv_plain=np.load(FM_OUT/'curves.npz');fv_raised=np.load(FR_OUT/'curves.npz')
for o in bpy.context.scene.objects:
    if o.type in ['MESH','CURVE','FONT']:o.hide_render=True
fv_show={'Pitch_Yoke','Pitch_Cradle','Pitch_Servo','Yaw_Servo','Yaw_Reaction_Link','Yaw_Base',
         'Yaw_Axial_Keeper','Yaw_Bearing','Pitch_Bearing_L','Pitch_Bearing_R','CAM_Tie_Head','CAM_Tie_Band'}
fv_created=[];fv_solid_hashes={}
for name,group,m,*_ in fm_targets:
    if name not in fv_show:continue
    a=m.to_mesh64();d=bpy.data.meshes.new('A8_FORMING_'+name)
    d.from_pydata(a.vert_properties[:,:3].tolist(),[],a.tri_verts.tolist());d.update()
    o=bpy.data.objects.new('A8_FORMING_'+name,d);bpy.context.scene.collection.objects.link(o)
    color=(.54,.57,.59) if 'Servo' in name else (.15,.25,.28)
    if name=='Yaw_Reaction_Link':color=(.84,.44,.12)
    if name.startswith('CAM_Tie_'):color=(.88,.69,.22)
    d.materials.append(material('A8_FORMING_MAT_'+name,color,roughness=.5))
    o['study_owner']='CAM_WIRE_FORMING';o['part_class']='PLACEHOLDER';o['data_status']='ASSUMED'
    fv_created.append(o)
    fv_solid_hashes[name]=hashlib.sha256(a.vert_properties[:,:3].tobytes()+a.tri_verts.tobytes()).hexdigest()
fv_colors=[(.06,.57,.66),(.9,.23,.07),(.28,.62,.1),(.63,.25,.77)]
fv_wires=[]
def fv_pose(curves,fraction):
    for o in fv_wires:bpy.data.objects.remove(o,do_unlink=True)
    fv_wires.clear()
    for slot in range(4):
        key=f'f{fraction:.3f}_slot{slot}'
        # Failed screens stopped after the first collision. Other wires are
        # the same known X offsets, regenerated only for that comparison.
        if key in curves:points=curves[key]
        else:points=curves[f'f{fraction:.3f}_slot0']+[xx[slot]-xx[0],0,0]
        d=bpy.data.curves.new(f'A8_FORMING_WIRE{slot}','CURVE');d.dimensions='3D'
        d.bevel_depth=OD/2.;d.bevel_resolution=3;d.use_fill_caps=True
        sp=d.splines.new('POLY');sp.points.add(len(points)-1)
        for q,p in zip(sp.points,points):q.co=(*p,1)
        o=bpy.data.objects.new(f'A8_FORMING_WIRE{slot}',d);bpy.context.scene.collection.objects.link(o)
        d.materials.append(material(f'A8_FORMING_WIRE_MAT{slot}',fv_colors[slot],roughness=.5))
        o['study_owner']='CAM_WIRE_FORMING';o['part_class']='PLACEHOLDER';o['data_status']='ASSUMED'
        fv_wires.append(o)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True
scene.render.resolution_x=1100;scene.render.resolution_y=950;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';fv_images=[]
for label,curves,fraction,scale,target in [
    ('direct_bend_conflict',fv_plain,.825,116,(-7,0,218)),
    ('raised_bend_candidate',fv_raised,.825,116,(-7,0,218)),
    ('upright_start',fv_raised,0.,215,(-7,0,262))]:
    fv_pose(curves,fraction);camera('A8_FORMING_CAMERA',(-130,100,330),target,scale)
    scene.render.filepath=str(FM_OUT/(label+'.png'));bpy.ops.render.render(write_still=True)
    fv_images.append({'file':label+'.png','sha256':sha(FM_OUT/(label+'.png')),'fraction':fraction,
                      'wire_source_sha256':sha(FM_OUT/'curves.npz') if curves is fv_plain else sha(FR_OUT/'curves.npz')})
fv_pose(fv_raised,1.)
camera('A8_FORMING_CAMERA',(-130,100,330),(-7,0,218),116)
bpy.context.view_layer.update()
assert all(geometry_record(o)==fv_base[o.name] for o in parts() if o.name in fv_base)
scene['independent_study']='CAM wire forming: raised-apex41-pose candidate only; final parts unchanged. No terminal shape, continuous forming or full assembly qualification.'
bpy.ops.wm.save_as_mainfile(filepath=str(FM_OUT/'review.blend'))
(FM_OUT/'render_manifest.json').write_text(json.dumps({'status':'PASS','script_sha256':sha(FV_SCRIPT),
 'helper_sha256':sha(FV_HELPER),'source_main_sha256':source_hash,'source_raised_screen_sha256':sha(FR_OUT/'screen.json'),
 'source_solids_sha256':fv_solid_hashes,'physical_source_objects_preserved':len(fv_base),
 'source_parts_visible':sorted(fv_solid_hashes),'images':fv_images,'review_sha256':sha(FM_OUT/'review.blend'),
 'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False},ensure_ascii=False,indent=2)+'\n')
print('CAM_FORMING_RENDER_DONE',len(fv_images),flush=True)

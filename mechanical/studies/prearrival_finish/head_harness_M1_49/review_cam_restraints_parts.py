"""Visualize the independent sliding guide and return clamp without native edits."""
from pathlib import Path
import json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=HERE/'remaining_routes';REST=BASE/'cam_restraints';OUT=REST/'review_parts'
OUT.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from common import bpy,COLS
from validate import rigidtr
from render import camera
ctx=Context();started=time.time();J=BASE/'cam_side_fans/c6_join';C=REST/'return_clamp_v3';G=REST/'sliding_guide_v4'
reports=[J/'join_review.json',C/'review.json',G/'review.json',REST/'return_material_stations.json']
for path in reports:
    r=json.loads(path.read_text());assert r['status']=='PASS'
    for f,h in {**r['sources'],**r['inputs']}.items():assert sha(ROOT/f)==h,f
curves=np.load(J/'candidate_curves.npz');tag='MORI_CAM_RESTRAINT_CANDIDATE__';scene=bpy.context.scene;clones={};groups={};wires=[]
replacement={'Pitch_Cradle':C/'Pitch_Cradle_candidate.npz','Pitch_Yoke':G/'Pitch_Yoke_candidate.npz','Yaw_Base':BASE/'c6_left_slot_entry/Yaw_Base_candidate.npz'}
def meshobj(name,v,f,color,group):
    me=bpy.data.meshes.new(tag+name);me.from_pydata(v.tolist(),[],f.tolist());me.update();o=bpy.data.objects.new(tag+name,me);scene.collection.objects.link(o)
    o.color=color;o['robot_part']=False;o['category']='PRINTABLE' if name in replacement else 'PURCHASED_REFERENCE';o['data_status']='ASSUMED';o['scope']='Independent candidate review; not manufacturing release';clones[name]=o;groups[name]=group
for n,s in ctx.ss.items():
    if n in ['Head_Front','Head_Rear','Body_Upper','Body_Lower'] or s.group not in ['yaw','pitch','body']:continue
    if n in replacement:
        a=np.load(replacement[n]);v=a['vertices_mm'];f=a['triangles']
    else:v=s.v;f=s.f
    color=(.36,.59,.67,1.) if n in ['Pitch_Cradle','Pitch_Yoke'] else (.68,.56,.32,1.) if n=='Yaw_Base' else s.o.color
    meshobj(n,v,f,color,s.group)
for name in ['band','head']:
    a=np.load(C/(name+'.npz'));meshobj('Tie_'+name,a['vertices_mm'],a['triangles'],(.12,.14,.16,1.),'pitch')
def wire(name,p,r,color):
    cu=bpy.data.curves.new(tag+name,'CURVE');cu.dimensions='3D';cu.bevel_depth=r;cu.bevel_resolution=3;cu.use_fill_caps=True
    sp=cu.splines.new('POLY');sp.points.add(len(p)-1)
    for a,b in zip(sp.points,p):a.co=(*b,1.)
    o=bpy.data.objects.new(tag+name,cu);scene.collection.objects.link(o);o.color=color;o['robot_part']=False;o['category']='PLACEHOLDER';o['data_status']='ASSUMED';wires.append(o)
for col in COLS.values():col.hide_viewport=False;col.hide_render=False
scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.color_type='OBJECT';scene.display.shading.light='STUDIO';scene.display.shading.show_cavity=False
scene.display.shading.cavity_type='BOTH';scene.display.shading.show_shadows=True;scene.display.shading.show_specular_highlight=False;scene.display.shading.background_type='WORLD'
scene.world.color=(.86,.88,.90);scene.view_settings.view_transform='Standard';scene.render.film_transparent=False
scene.render.resolution_x=1400;scene.render.resolution_y=1200;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
palette=[(.04,.71,.79,1),(.12,.75,.3,1),(.85,.27,.66,1),(.95,.57,.08,1)];images=[]
views=[('head_overview',0,0,(-190,90,326),(-10,-3,225),112),
       ('sliding_guide',0,0,(-12,4,314),(-28,-10,226),35),
       ('return_clamp',0,0,(-10,8,294),(-28,-21,216),38),
       ('head_pitch_25',0,25,(-138,-178,293),(-13,-3,218),110)]
for name,yaw,pitch,eye,target,scale in views:
    for o in wires:bpy.data.objects.remove(o,do_unlink=True)
    wires=[]
    for n,o in clones.items():o.matrix_world=rigidtr(yaw,pitch) if groups[n]=='pitch' else rigidtr(yaw,0) if groups[n]=='yaw' else rigidtr(0,0)
    for pin in range(1,5):wire('CAM_'+str(pin),curves[f'CAM_{pin}_y{yaw}_p{pitch}'],.3302,palette[pin-1])
    for n in ['P_J9_1','P_J9_2','P_J9_3','P_J18_1','P_J18_2']:wire(n,curves[f'{n}_y{yaw}'],.5842,(.78,.57,.17,1))
    for slot in [3,6]:wire('SPK_'+str(slot),curves[f'SPK_reservation_{slot}_y{yaw}'],.4445,(.5,.5,.5,1))
    for o in scene.objects:
        if o.type in ['MESH','CURVE','FONT']:o.hide_render=True
    for o in list(clones.values())+wires:o.hide_render=False;o.hide_set(False)
    if name in ['sliding_guide','return_clamp']:
        shown=['Pitch_Yoke'] if name=='sliding_guide' else ['Pitch_Cradle','Tie_band','Tie_head','CAM_Mainboard']
        for n,o in clones.items():o.hide_render=n not in shown
    cam=camera(tag+name,eye,target,scale);cam.data.clip_start=.1;scene.render.filepath=str(OUT/(name+'.png'))
    bpy.ops.render.render(write_still=True);images.append(dict(file=name+'.png',sha256=sha(OUT/(name+'.png')),yaw_deg=yaw,pitch_deg=pitch))
ctx.assert_unchanged();blend=OUT/'MORI_M1_49_CAM_restraint_candidate.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend));ctx.assert_unchanged()
inputs=[*reports,J/'candidate_curves.npz',*replacement.values(),C/'band.npz',C/'head.npz']
r=dict(status='PASS',scope='Visual evidence only; two closeups show only the relevant carrying print and wires (plus the CAM board for the clamp), while full native geometry remains in the collision checks',sources=ctx.sources,
       inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},images=images,blend_sha256=sha(blend),original_geometry_after_save='PASS',main_changed=False,
       approved=False,C6_main_applied=False,full_harness='BLOCKED',script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(r,indent=2)+'\n');print('RESTRAINT_REVIEW',r['status'],flush=True)

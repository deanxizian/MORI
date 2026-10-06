"""Editable visual review of the checked detached preassembly and transfer."""
from pathlib import Path
import json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=HERE/'remaining_routes';REST=BASE/'cam_restraints'
B=REST/'bench_preassembly_v2';T=REST/'bench_transfer';G=REST/'sliding_guide_v4';PH=REST/'PH_terminal_gate';OUT=REST/'bench_review'
OUT.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import bpy,COLS
from render import camera
from mathutils import Matrix
ctx=Context();started=time.time();reports=[B/'review.json',T/'review.json',PH/'review.json'];inputs=list(reports)
for p in reports:
    r=json.loads(p.read_text());assert r['status']=='PASS'
    for f,h in {**r['sources'],**r['inputs']}.items():assert sha(ROOT/f)==h,f
br=json.loads(reports[0].read_text());module=set(br['module'])|{'connector_band','connector_head'};deferred=set(br['not_yet_installed'])
tag='MORI_CAM_BENCH_STUDY__';scene=bpy.context.scene;clones={};wires=[]
def mesh(name,v,f,color):
    me=bpy.data.meshes.new(tag+name);me.from_pydata(v.tolist(),[],f.tolist());me.update()
    o=bpy.data.objects.new(tag+name,me);scene.collection.objects.link(o);o.color=color
    o['robot_part']=False;o['category']='PLACEHOLDER';o['data_status']='ASSUMED';o['scope']='Independent staged assembly study, not main geometry or manufacturing release'
    clones[name]=o;return o
def cached(name,path,shift=(0,0,0),color=(.31,.59,.65,1)):
    inputs.append(path);a=np.load(path);return mesh(name,a['vertices_mm']+shift,a['triangles'],color)
for n,s in ctx.ss.items():
    if n in deferred or n in ['Body_Upper','Body_Lower'] or s.group not in ['yaw','pitch','body']:continue
    if n=='Pitch_Cradle':cached(n,B/'Pitch_Cradle.npz',(-180,0,0))
    elif n=='Pitch_Yoke':cached(n,G/'Pitch_Yoke_candidate.npz')
    else:mesh(n,s.v,s.f,s.o.color)
for n in ['connector_band','connector_head']:cached(n,B/(n+'.npz'),(-180,0,0),(.09,.11,.13,1))
tool=cached('cutter_workspace',B/'connector_0_cutter_sweep.npz',(-180,0,0),(.93,.40,.05,1))
mod=tool.modifiers.new('Show_work_envelope_edges','WIREFRAME');mod.thickness=.25;mod.use_replace=True
contact=cached('PH_family_outline_sweep',PH/'PH_contact_sweep.npz',color=(.97,.58,.13,1))
basecurves={n:p-[180,0,0] for n,p in np.load(B/'bench_curves.npz').items()};inputs.append(B/'bench_curves.npz')
palette=[(.03,.64,.75,1),(.08,.68,.23,1),(.82,.23,.63,1),(.95,.56,.07,1)]
def wire(name,p,r,color):
    cu=bpy.data.curves.new(tag+name,'CURVE');cu.dimensions='3D';cu.bevel_depth=r;cu.bevel_resolution=3;cu.use_fill_caps=True
    sp=cu.splines.new('POLY');sp.points.add(len(p)-1)
    for a,b in zip(sp.points,p):a.co=(*b,1)
    o=bpy.data.objects.new(tag+name,cu);scene.collection.objects.link(o);o.color=color;o['robot_part']=False;o['category']='PLACEHOLDER';o['data_status']='ASSUMED';wires.append(o)
for col in COLS.values():col.hide_render=False;col.hide_viewport=False
scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.color_type='OBJECT';scene.display.shading.light='STUDIO'
scene.display.shading.show_cavity=False;scene.display.shading.show_shadows=True;scene.display.shading.show_specular_highlight=False;scene.display.shading.background_type='WORLD'
scene.world.color=(.87,.89,.91);scene.view_settings.view_transform='Standard';scene.render.film_transparent=False
scene.render.resolution_x=1400;scene.render.resolution_y=1150;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
views=[
 ('bench_cutting',[180,0,0],(115,73,277),(153,-20,229),83),
 ('above_yoke',[0,0,35],(-156,114,355),(-10,-6,244),152),
 ('seated_loose_leads',[0,0,0],(-133,107,307),(-10,-7,227),116),
 ('PH_gate',[0,0,0],(-3,13,274),(-28,-11,225),24),
]
images=[]
for name,shift,eye,target,scale in views:
    for o in wires:bpy.data.objects.remove(o,do_unlink=True)
    wires=[]
    for n,o in clones.items():o.matrix_world=Matrix.Translation(shift) if n in module or n=='cutter_workspace' else Matrix.Identity(4)
    if name=='PH_gate':
        ph=json.loads((PH/'review.json').read_text())
        for i,row in enumerate(ph['parked_wire_checks']):wire('temporary_'+str(i),np.array([[*row['xy_mm'],223],[*row['xy_mm'],228]]),.3302,palette[i])
    else:
        for i,(n,p) in enumerate(basecurves.items()):wire(n,p+shift,.3302,palette[i])
    for o in scene.objects:
        if o.type in ['MESH','CURVE','FONT']:o.hide_render=True
    for o in wires:o.hide_render=False;o.hide_set(False)
    for n,o in clones.items():
        visible=(n in ['Pitch_Yoke','PH_family_outline_sweep']) if name=='PH_gate' else n!='PH_family_outline_sweep' and (n!='cutter_workspace' or name=='bench_cutting')
        o.hide_render=not visible;o.hide_set(not visible)
    cam=camera(tag+name,eye,target,scale);cam.data.clip_start=.1;scene.render.filepath=str(OUT/(name+'.png'))
    bpy.ops.render.render(write_still=True)
    images.append(dict(file=name+'.png',sha256=sha(OUT/(name+'.png')),module_translation_mm=shift,
                       view_scope='Local guide detail only' if name=='PH_gate' else 'Body shells hidden for view only; they remain in the transfer collision fixtures. Free upper lead ends extend beyond the crop.'))
ctx.assert_unchanged();blend=OUT/'MORI_M1_49_CAM_bench_sequence.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend));ctx.assert_unchanged()
r=dict(status='PASS',scope='Visualisation of existing checked candidate solids; not a new geometric test',sources=ctx.sources,
    inputs={str(p.relative_to(ROOT)):sha(p) for p in set(inputs)},images=images,blend_sha256=sha(blend),
    original_geometry_after_save='PASS',main_changed=False,approved=False,full_harness='BLOCKED',
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(r,indent=2)+'\n');print('BENCH_REVIEW_DONE',r['status'],flush=True)

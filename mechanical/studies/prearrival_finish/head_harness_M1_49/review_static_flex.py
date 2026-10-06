"""Shell-path check and editable views of an unadopted LCD packing allocation."""
from pathlib import Path
import json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
OUT=HERE/'remaining_routes/static_flex';VIEW=OUT/'review'
VIEW.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from common import manifold,bpy,COLS
from render import camera
from static_flex_geometry import core

ctx=Context();started=time.time();geom=core(radius=7.5,width=10.5,z=238.)
m=manifold.Manifold(manifold.Mesh64(geom['vertices_mm'],geom['triangles']))
rows=[]
for name,sign in [('Head_Front',1),('Head_Rear',-1)]:
    failures=[];nearest=1.
    for d in np.linspace(0,68,273):
        shell=ctx.ss[name].m.translate([0,sign*float(d),0])
        overlap=float((m^shell).volume());gap=float(m.min_gap(shell,1.))
        nearest=min(nearest,gap)
        if overlap>1e-7 or gap<.3+geom['metadata']['chord_error_bound_mm']:
            failures.append(dict(translation_y_mm=sign*float(d),overlap_mm3=overlap,gap_mm=gap))
    rows.append(dict(part=name,status='FAIL' if failures else 'PASS',samples=273,
        translation_y_mm=[0,68*sign],step_mm=.25,minimum_capped_gap_mm=nearest,
        min_gap_search_cap_mm=1.,failures=failures,
        scope='This new static central span versus translated shell only; neither full assembly nor cable restraint is established.'))
    print('STATIC_FLEX_SHELL',name,rows[-1]['status'],flush=True)

scene=bpy.context.scene;tag='MORI_STATIC_FLEX_REVIEW__';clones={}
def clone_mesh(name,v,f,color,category='PLACEHOLDER',evidence='ASSUMED'):
    me=bpy.data.meshes.new(tag+name);me.from_pydata(np.asarray(v).tolist(),[],np.asarray(f).tolist());me.update()
    o=bpy.data.objects.new(tag+name,me);scene.collection.objects.link(o);o.color=color
    o['robot_part']=False;o['category']=category;o['data_status']=evidence
    o['scope']='Independent review copy; not main or a printable part.'
    clones[name]=o;return o
for name,s in ctx.ss.items():
    if s.group not in ['pitch','yaw']:continue
    if name in ['Head_Front','Head_Rear']:continue
    color=(.65,.7,.72,1)
    if name in ['CAM_Mainboard','Display_PCB']:color=(.17,.40,.33,1)
    clone_mesh(name,s.v,s.f,color,s.o.get('category','PLACEHOLDER'),s.o.get('data_status','ASSUMED'))
c=clone_mesh('LCD_170mm_storage_ONLY',geom['vertices_mm'],geom['triangles'],(.97,.57,.12,1))
c['scope']='170mm central allocation. Two 15mm approaches and all connector engagement omitted. Width10.5/thickness0.2/R7.5 are assumptions.'
for i,p in enumerate(geom['points_mm'][[0,-1]]):
    sm=manifold.Manifold.sphere(.6,24).translate(p);a=sm.to_mesh64()
    clone_mesh('unconnected_end_'+str(i),a.vert_properties[:,:3],a.tri_verts,(.86,.08,.1,1))

for col in COLS.values():col.hide_render=False;col.hide_viewport=False
for o in scene.objects:
    if o.type in ['MESH','CURVE','FONT']:o.hide_render=True;o.hide_set(True)
for o in clones.values():o.hide_render=False;o.hide_set(False)
scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.color_type='OBJECT'
scene.display.shading.light='STUDIO';scene.display.shading.show_cavity=False
scene.display.shading.show_shadows=True;scene.display.shading.background_type='WORLD'
scene.world.color=(.91,.93,.95);scene.view_settings.view_transform='Standard'
scene.render.resolution_x=1500;scene.render.resolution_y=1150;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';images=[]
for name,eye,target,scale in [('central_span',(-125,140,365),(0,4,240),118),
                             ('top',(-.1,4,435),(0,4,240),117)]:
    camera(tag+name,eye,target,scale)
    scene.render.filepath=str(VIEW/(name+'.png'));bpy.ops.render.render(write_still=True)
    images.append(dict(file=name+'.png',sha256=sha(VIEW/(name+'.png'))))
scene['review_status']='PROTOTYPE / UNVALIDATED — unconnected central FFC capacity only'
camera(tag+'editable',(-125,140,365),(0,4,240),118)
ctx.assert_unchanged()
blend=VIEW/'MORI_M1_49_static_FFC_capacity.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend))
ctx.assert_unchanged()
r=dict(status='PASS' if all(x['status']=='PASS' for x in rows) else 'FAIL',sources=ctx.sources,
    inputs={str((HERE/'static_flex_geometry.py').relative_to(ROOT)):sha(HERE/'static_flex_geometry.py')},
    shell_paths=rows,images=images,blend_sha256=sha(blend),parameters=geom['metadata'],
    main_changed=False,adopted=False,full_flex_fit='BLOCKED',full_harness='BLOCKED',
    scope='Shell-path test versus one unconnected central span and independent review generation only',
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(VIEW/'review.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('STATIC_FLEX_REVIEW_DONE',r['status'],flush=True)

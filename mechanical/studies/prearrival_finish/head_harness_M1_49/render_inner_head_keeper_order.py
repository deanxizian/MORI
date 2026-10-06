"""Show the two checked keeper operations using the tested candidate solids."""
from pathlib import Path
import json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes';REST=BASE/'cam_restraints';OUT=REST/'inner_head_sequence_review'
OUT.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import bpy,manifold
from validate import rigidtr
from render import camera
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text())
source=REST/'keeper_alternating_yaw/review.json';r=read(source)
for f,h in {**r['sources'],**r['inputs']}.items():assert sha(ROOT/f)==h,f
toolfile=source.parent/'tools.npz';assert sha(toolfile)==r['tool_geometry_sha256']
tools=np.load(toolfile);inputs=[source,toolfile,ROOT/'mechanical/scripts/render.py']
absent=set(r['absent_in_inner_head_stage'])
geometry={n:s.m for n,s in ctx.ss.items() if n not in absent};groups={n:s.group for n,s in ctx.ss.items()}
for n,p,g in [('Yaw_Base',BASE/'c6_left_slot_entry/Yaw_Base_candidate.npz','body'),
              ('Pitch_Yoke',REST/'sliding_guide_v4/Pitch_Yoke_candidate.npz','yaw'),
              ('Pitch_Cradle',REST/'return_clamp_v3/Pitch_Cradle_candidate.npz','pitch'),
              ('connector_band',REST/'return_clamp_v3/band.npz','pitch'),('connector_head',REST/'return_clamp_v3/head.npz','pitch')]:
    inputs.append(p);a=np.load(p);geometry[n]=manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles'].astype(np.uint64)));groups[n]=g
for o in bpy.context.scene.objects:o.hide_render=True
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH'
scene.render.resolution_x=1000;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
shade=scene.display.shading;shade.light='STUDIO';shade.color_type='OBJECT';shade.show_shadows=True
shade.show_cavity=True;shade.cavity_type='BOTH';shade.show_object_outline=True
shade.background_type='WORLD';scene.world.color=(.82,.85,.87)
scene.view_settings.view_transform='Standard';scene.render.film_transparent=False
def color(n):
    if n=='tool':return (.07,.44,.94,1)
    if 'Keeper' in n:return (.96,.65,.20,1)
    if n in ['Yaw_Base','Pitch_Yoke','Pitch_Cradle']:return (.30,.44,.51,1)
    if n=='CAM_Mainboard':return (.15,.31,.23,1)
    if 'Servo' in n:return (.68,.70,.73,1)
    if n in ['connector_band','connector_head']:return (.12,.13,.14,1)
    return (.76,.77,.76,1)
def show(name,m):
    mesh=m.to_mesh64();d=bpy.data.meshes.new('MORI_INNER_ORDER_'+name)
    d.from_pydata(mesh.vert_properties[:,:3].tolist(),[],mesh.tri_verts.tolist());d.update()
    o=bpy.data.objects.new('MORI_INNER_ORDER_'+name,d);scene.collection.objects.link(o);o.color=color(name);return o
images=[]
for label,yaw,screw,sign in [('left',60,'Yaw_Keeper_Screw_0',-1),('right',-60,'Yaw_Keeper_Screw_1',1)]:
    shown=[];tr=np.asarray(rigidtr(yaw,0))[:3,:]
    for n,m in geometry.items():shown.append(show(n,m.transform(tr) if groups[n] in ['yaw','pitch'] else m))
    for i in range(3):
        v=tools[f'{screw}_piece{i}_vertices'];f=tools[f'{screw}_piece{i}_triangles']
        shown.append(show('tool',manifold.Manifold(manifold.Mesh64(v,f.astype(np.uint64)))))
    cam=camera('INNER_ORDER_'+label,[sign*145,195,305],[0,0,211],164)
    scene.render.filepath=str(OUT/(label+'_keeper.png'));bpy.ops.render.render(write_still=True)
    images.append(dict(file=label+'_keeper.png',yaw_deg=yaw,sha256=sha(OUT/(label+'_keeper.png'))))
    for o in shown:bpy.data.objects.remove(o,do_unlink=True)
ctx.assert_unchanged()
out=dict(status='PASS',scope='Actual candidate meshes and saved checked tool, illustration only',
    sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},images=images,
    main_changed=False,approved=False,C6_main_applied=False,full_harness='BLOCKED',Yaw_Reaction_Link_present=True,
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'render_review.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('INNER_HEAD_KEEPER_RENDER_DONE',out['status'],out['elapsed_s'],flush=True)

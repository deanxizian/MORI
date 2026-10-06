"""Review views of the saved, unapproved body split candidate."""
from pathlib import Path
import json,math,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes';OUT=BASE/'cam_restraints/body_front_rear_split'
sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import bpy,manifold
from render import camera
from interface_completion import axial
ctx=Context();started=time.time();source=OUT/'review.json';r=json.loads(source.read_text())
for f,h in {**r['sources'],**r['inputs']}.items():assert sha(ROOT/f)==h,f
inputs=[source,ROOT/'mechanical/scripts/render.py',ROOT/'mechanical/scripts/interface_completion.py']
forms={}
for n,row in r['parts'].items():
    p=ROOT/row['file'];assert sha(p)==row['sha256'];inputs.append(p)
    a=np.load(p);forms[n]=manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles'].astype(np.uint64)))
for o in bpy.context.scene.objects:o.hide_render=True
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH'
scene.render.resolution_x=1100;scene.render.resolution_y=850;scene.render.resolution_percentage=100
sh=scene.display.shading;sh.light='STUDIO';sh.color_type='OBJECT';sh.show_shadows=True
sh.show_cavity=True;sh.cavity_type='BOTH';sh.show_object_outline=True
sh.background_type='WORLD';scene.world.color=(.90,.92,.93)
scene.view_settings.view_transform='Standard';scene.render.film_transparent=False
def color(n):
    if n=='Body_Front_candidate':return (.64,.81,.87,1)
    if n=='Body_Rear_candidate':return (.90,.85,.74,1)
    if n.startswith('Body_'):return (.91,.89,.84,1)
    if n.startswith('Tool_'):return (.04,.36,.98,1)
    if 'Tire' in n:return (.085,.10,.105,1)
    if 'Hub' in n:return (.88,.86,.81,1)
    if n in ['Battery_Pack']:return (.12,.31,.48,1)
    if n in ['MCU_Motion','Power_Module','Rear_Interface_PCB','IMU_Module']:return (.13,.32,.22,1)
    if n=='Speaker':return (.10,.12,.13,1)
    return (.42,.49,.51,1)
def show(n,m):
    a=m.to_mesh64();mesh=bpy.data.meshes.new('BODY_SPLIT_REVIEW_'+n)
    mesh.from_pydata(a.vert_properties[:,:3].tolist(),[],a.tri_verts.tolist());mesh.update()
    if n.startswith('Body_'):
        # Presentation normals only. Keep sharp port/seam edges while
        # avoiding a faceted appearance on the unchanged mother surface.
        edges=[[] for _ in mesh.edges]
        for poly in mesh.polygons:
            poly.use_smooth=True
            for k in poly.loop_indices:edges[mesh.loops[k].edge_index].append(poly.index)
        for edge,faces in zip(mesh.edges,edges):
            if len(faces)==2 and mesh.polygons[faces[0]].normal.angle(mesh.polygons[faces[1]].normal,0)>math.radians(30):
                edge.use_edge_sharp=True
        mesh.update()
    o=bpy.data.objects.new('BODY_SPLIT_REVIEW_'+n,mesh);scene.collection.objects.link(o);o.color=color(n);return o
native={n:s.m for n,s in ctx.ss.items() if s.group not in ['yaw','pitch']}
# The right tyre/hub is hidden in all comparison views solely to show the seam.
hidden={'Tire_R','Wheel_Hub_R','Wheel_End_Screw_R','Wheel_End_Washer_R'}
images=[]
for label in ['current','candidate_closed','candidate_open','underside_ports']:
    geo={n:m for n,m in native.items() if n not in hidden}
    if label!='current':
        for n in r['omitted']+['Body_Upper','Body_Lower']:geo.pop(n,None)
        geo.update(forms)
    if label=='candidate_open':
        for n in r['deferred_frame_screws']:geo.pop(n,None)
        for group,sign in [('front',1),('rear',-1)]:
            for n in r['modules'][group]:
                if n in geo:geo[n]=geo[n].translate([0,90*sign,0])
    if label=='underside_ports':
        for i,(x,y) in enumerate(r['proposed_new_tool_ports']['axis_xy_mm']):
            geo[f'Tool_{i}']=axial(2.5,90,[x,y,40],[0,0,1])
    shown=[show(n,m) for n,m in geo.items()]
    if label=='candidate_open':pos=[330,425,260];target=[0,0,104];scale=440
    elif label=='underside_ports':pos=[210,250,-200];target=[0,0,75];scale=255
    else:pos=[240,300,190];target=[0,0,103];scale=255
    camera('BODY_SPLIT_'+label,pos,target,scale)
    image=OUT/(label+'.png');scene.render.filepath=str(image);bpy.ops.render.render(write_still=True)
    images.append(dict(file=image.name,sha256=sha(image)))
    for o in shown:bpy.data.objects.remove(o,do_unlink=True)
ctx.assert_unchanged()
out=dict(status='PASS',scope='Actual candidate meshes; colours distinguish proposed halves, not final finish',
    sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},images=images,
    presentation_hidden=sorted(hidden)+['yaw and pitch assemblies'],
    wire_geometry_hidden=True,main_changed=False,approved=False,C6_main_applied=False,full_harness='BLOCKED',
    Yaw_Reaction_Link_present=True,script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'render_review.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('BODY_SPLIT_RENDER_DONE',out['status'],out['elapsed_s'],flush=True)

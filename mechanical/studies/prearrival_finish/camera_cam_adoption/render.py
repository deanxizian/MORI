"""Current-main detail views; no candidate print or harness is substituted."""
import sys,json,hashlib
from pathlib import Path
OUT=Path(__file__).resolve().parent;P=OUT.parents[3];M=P/'mechanical'
sys.path.insert(0,str(M/'scripts'))
from common import *
from render import camera
from validate_head_cleanup import geometry_record
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load_collections();assembled();bpy.context.view_layer.update()
obs={o.name.removeprefix(PREFIX):o for o in parts() if o.get('group') not in ['dock','coupon']}
before={n:geometry_record(o) for n,o in obs.items()}
for c in COLS.values():c.hide_viewport=False;c.hide_render=False
sc=bpy.context.scene;sc.render.engine='BLENDER_WORKBENCH'
sc.display.shading.color_type='OBJECT';sc.display.shading.light='STUDIO'
sc.display.shading.show_cavity=True;sc.display.shading.cavity_type='BOTH'
sc.display.shading.show_shadows=True;sc.display.shading.show_specular_highlight=False
sc.display.shading.background_type='WORLD';sc.world.color=(.78,.81,.83)
sc.view_settings.view_transform='Standard';sc.render.film_transparent=False
sc.render.resolution_x=1000;sc.render.resolution_y=850;sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG'
key=np.load(M/'studies/prearrival_finish/harness_A8/cam_socket_tool/CAM_Mount_Screw_0_key.npz')
me=bpy.data.meshes.new('review_only_tool');me.from_pydata(key['vertices_mm'].tolist(),[],key['triangles'].tolist());me.update()
tool=bpy.data.objects.new('review_only_Wera_tool',me);sc.collection.objects.link(tool);tool.color=(.08,.6,.3,1)
tools={tool.name:tool};images=[]
def render(name,show,eye,target,scale,key=False):
    for o in sc.objects:
        if o.type in ['MESH','CURVE','FONT']:o.hide_render=True
    for n in show:
        o=obs[n];o.hide_render=False;o.hide_set(False)
        o.color=(.36,.49,.53,1) if o.get('category')=='PRINTABLE' else (.7,.71,.72,1)
        if n=='CAM_Mainboard':o.color=(.06,.09,.1,1)
        if n in ['Camera_PCB']:o.color=(.6,.32,.12,1)
        if n in ['Camera_Lens','Display_Module']:o.color=(.025,.03,.04,1)
    tool.hide_render=not key
    cam=camera('M1_48_'+name,eye,target,scale);cam.data.clip_start=.1
    sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
    images.append({'file':name+'.png','sha256':sha(OUT/(name+'.png')),'parts':sorted(show),'tool_reference_only':key})
construction=json.loads((M/'studies/prearrival_finish/camera_top_clearance/construction.json').read_text())
rc=np.array(construction['camera_local_basis_columns']);p=np.array(construction['camera_pupil_world_mm'])
render('camera_top',{'Display_Frame','Camera_PCB','Camera_Lens'},p+rc@np.array([22,-20,38]),p+rc@np.array([0,-1.5,-2]),23)
camshow={'Pitch_Yoke','Yaw_Servo','Pitch_Servo','Pitch_Cradle','CAM_Mainboard'}|{n for n in obs if n.startswith(('CAM_Mount_','Onboard_MIC_'))}
render('cam_screws',camshow,(40,25,330),(-16,-16,222),55,True)
render('head_overview',camshow|{'Display_Frame','Display_PCB','Camera_PCB','Camera_Lens'},(200,230,360),(0,0,231),135)
assert all(geometry_record(o)==before[n] for n,o in obs.items())
save_json(OUT/'render_manifest.json',{'revision':P['revision'],'source_blend_sha256':sha(M/'mori_v1_2.blend'),'images':images,'robot_geometry_unchanged':True,'saved_to_main':False,'script_sha256':sha(Path(__file__))})

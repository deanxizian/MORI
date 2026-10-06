"""Review-only copies show the proposed four screws and catalogue tool."""
from pathlib import Path
import sys,json,hashlib
SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;OUT=A8/'cam_socket_tool';ROOT=A8.parents[3]
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(ROOT/'mechanical/scripts/vendor'))
from common import *
from render import camera
from validate_head_cleanup import geometry_record
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
SOURCE=A8/'cam_wired_cradle/review.blend';assert Path(bpy.data.filepath)==SOURCE
screen=json.loads((OUT/'screen.json').read_text());check=json.loads((OUT/'verification.json').read_text())
assert screen['status']==check['status']=='PASS'
load_collections();assembled();bpy.context.view_layer.update()
physical={o.name.removeprefix(PREFIX):o for o in parts() if o.get('group') not in ['dock','coupon']}
before={n:geometry_record(o) for n,o in physical.items()}
for c in ['DATUMS','KEEP_OUT','COUPONS','DOCK','ANNOTATIONS']:COLS[c].hide_render=True
show={'Pitch_Yoke','Yaw_Servo','Pitch_Servo','Pitch_Cradle','CAM_Mainboard'}|{n for n in physical if n.startswith(('CAM_Mount_Insert_','Onboard_MIC_','Head_Cradle_Insert_'))}
for o in bpy.context.scene.objects:
    if o.type in ['MESH','CURVE']:o.hide_render=o.name.removeprefix(PREFIX) not in show
extras=[]
def mesh(name,path,color,evidence='ASSUMED'):
    data=np.load(path);d=bpy.data.meshes.new(name);d.from_pydata(data['vertices_mm'].tolist(),[],data['triangles'].tolist());d.update()
    o=bpy.data.objects.new('A8_SOCKET_TOOL_'+name,d);bpy.context.scene.collection.objects.link(o)
    d.materials.append(material('A8_SOCKET_MAT_'+name,color,roughness=.38));o['study_owner']='CAM_SOCKET_TOOL'
    o['part_class']='PURCHASED_REFERENCE' if name.startswith('CAM_Mount_Screw_') else 'PLACEHOLDER';o['data_status']=evidence
    o['evidence_note']='Nominal drawing reconstruction; not manufacturer CAD or measured hardware';extras.append(o);return o
screws={n:mesh(n,OUT/(n+'.npz'),(.63,.66,.69),'VENDOR_DOCUMENTED') for n in screen['changes']['proposed_replacements']}
tool=mesh('Wera_key',OUT/'CAM_Mount_Screw_0_key.npz',(.12,.64,.4))
curves=np.load(A8/'cam_board_last/curves.npz');colors=[(.06,.57,.66),(.9,.23,.07),(.28,.62,.1),(.63,.25,.77)]
for i in range(4):
    pts=curves[f'seating_plug0_board0_slot{i}']
    d=bpy.data.curves.new(f'SOCKET_WIRE{i}','CURVE');d.dimensions='3D';d.bevel_depth=.3302;d.bevel_resolution=3;d.use_fill_caps=True
    s=d.splines.new('POLY');s.points.add(len(pts)-1)
    for q,p in zip(s.points,pts):q.co=(*p,1)
    o=bpy.data.objects.new(f'A8_SOCKET_TOOL_wire{i}',d);bpy.context.scene.collection.objects.link(o)
    d.materials.append(material(f'A8_SOCKET_WIRE_MAT{i}',colors[i],roughness=.5))
    o['study_owner']='CAM_SOCKET_TOOL';o['part_class']='PLACEHOLDER';o['data_status']='ASSUMED';extras.append(o)
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=16;sc.cycles.use_denoising=True
sc.render.resolution_x=1200;sc.render.resolution_y=1000;sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG';images=[]
for label,eye,target,scale in [
    ('key_access',(-105,100,320),(-13,-3,257),151),
    ('socket_closeup',(40,25,330),(-16,-16,222),55)]:
    camera('A8_SOCKET_'+label,eye,target,scale);sc.render.filepath=str(OUT/(label+'.png'));bpy.ops.render.render(write_still=True)
    images.append({'file':label+'.png','sha256':sha(OUT/(label+'.png'))})
for o in extras:o['proposal_approval']='NOT_REQUESTED'
bpy.context.view_layer.update();assert all(geometry_record(o)==before[n] for n,o in physical.items())
sc['independent_unapproved_study']='CAM socket screws with Wera 950 PKLS short-arm key. Main geometry/hardware unchanged; no manufacturing release.'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'review.blend'))
(OUT/'render_manifest.json').write_text(json.dumps({'status':'PASS','script_sha256':sha(SCRIPT),'source_main_sha256':screen['source_main_sha256'],
    'source_candidate_sha256':sha(SOURCE),'screen_sha256':sha(OUT/'screen.json'),'verification_sha256':sha(OUT/'verification.json'),
    'physical_parts_preserved_unchanged':len(physical),'proposed_replacements':list(screws),'review_sha256':sha(OUT/'review.blend'),'images':images,
    'main_applied':False,'whole_harness':'BLOCKED'},ensure_ascii=False,indent=2)+'\n')
print('CAM_SOCKET_RENDER_DONE',len(images),flush=True)

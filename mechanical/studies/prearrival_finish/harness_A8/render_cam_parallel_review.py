"""Render the checked CAM-side four-wire loop; show missing lower connection."""
from pathlib import Path
import sys,json,hashlib
PAR_RENDER_SCRIPT=Path(__file__).resolve();PAR_RENDER_ROOT=PAR_RENDER_SCRIPT.parent
OUT=PAR_RENDER_ROOT/'cam_parallel_pitch';ROOT=PAR_RENDER_ROOT.parents[3]
sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from common import *
from render import camera
from validate import rigidtr
from validate_head_cleanup import geometry_record
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
expected=PAR_RENDER_ROOT/'assembly_feed_v3/open_mouth/cleaned/candidate.blend'
assert Path(bpy.data.filepath)==expected
load_collections();assembled();bpy.context.view_layer.update()
physical={o.name.removeprefix(PREFIX):o for o in parts() if o.get('group') not in ['dock','coupon']}
before={n:geometry_record(o) for n,o in physical.items()}
visible={'CAM_Mainboard','Yaw_Servo','Pitch_Servo','Pitch_Yoke','Display_Frame'}
for c in ['DATUMS','KEEP_OUT','COUPONS','DOCK','ANNOTATIONS']:COLS[c].hide_render=True
for o in bpy.context.scene.objects:
    if o.type in ['MESH','CURVE']:o.hide_render=True
for n,o in physical.items():o.hide_render=n not in visible
packing=json.loads((OUT/'following_arc/packing.json').read_text());assert packing['status']=='PASS'
choice=next(r['candidate'] for r in packing['rows'] if r['status']=='PASS')
curves=np.load(OUT/'following_arc/curves.npz');tails=np.load(OUT/'shifted_tails.npz')
colors=[(.07,.62,.70),(.90,.21,.06),(.3,.69,.08),(.67,.25,.80)]
generated=[]
def make_wire(name,points,i):
    c=bpy.data.curves.new(name,'CURVE');c.dimensions='3D';c.bevel_depth=.6604/2;c.bevel_resolution=4;c.use_fill_caps=True
    s=c.splines.new('POLY');s.points.add(len(points)-1)
    for q,p in zip(s.points,points):q.co=(*p,1)
    o=bpy.data.objects.new(name,c);bpy.context.scene.collection.objects.link(o)
    o['study_owner']='A8_CAM_PARALLEL_REVIEW';o['part_class']='PLACEHOLDER';o['data_status']='ASSUMED'
    o['scope']='CAM-side allocated loop only; lower wire connection and actual retaining mounts absent'
    c.materials.append(material('A8_PARALLEL_WIRE_'+str(i),colors[i],roughness=.55));generated.append(o)
def wires_at(angle):
    for o in list(generated):bpy.data.objects.remove(o,do_unlink=True)
    generated.clear();pose(0,angle);mat=np.asarray(rigidtr(0,angle))
    for i in range(4):
        core=curves[f'candidate{choice}_slot{i}_pitch{angle}']
        end=tails[f'slot{i}']@mat[:3,:3].T+mat[:3,3]
        make_wire('A8_PARALLEL_SLOT_'+str(i),np.vstack([core,end[-2::-1]]),i)
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=24;sc.cycles.use_denoising=True
sc.render.resolution_x=1200;sc.render.resolution_y=1100;sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG';sc.render.film_transparent=False
images=[]
for angle,label in [(0,'zero'),(-20,'down20'),(25,'up25')]:
    wires_at(angle)
    camera('A8_PARALLEL_REVIEW',(-95,92,270),(-9,2,218),85)
    dest=OUT/f'{label}.png';sc.render.filepath=str(dest);bpy.ops.render.render(write_still=True)
    images.append({'file':dest.name,'sha256':sha(dest),'yaw_deg':0,'pitch_deg':angle,
        'camera_eye_mm':[-95,92,270],'target_mm':[-9,2,218],'ortho_scale_mm':85})
assembled();bpy.context.view_layer.update()
assert all(geometry_record(o)==before[n] for n,o in physical.items())
wires_at(0)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'comparison.blend'))
result={'status':'PASS','scope':'Independent CAM-side loop review; fan-in and retaining features absent',
    'script_sha256':sha(PAR_RENDER_SCRIPT),'source_candidate_sha256':sha(expected),'source_packing_sha256':sha(OUT/'following_arc/packing.json'),
    'source_curves_sha256':sha(OUT/'following_arc/curves.npz'),'source_tails_sha256':sha(OUT/'shifted_tails.npz'),
    'comparison_blend_sha256':sha(OUT/'comparison.blend'),'visible_source_parts':sorted(visible),'candidate':choice,'images':images,
    'source_geometry_unchanged':True,'main_applied':False,'harness_status':'BLOCKED','physical_pin_color_meaning':'Geometric slot only'}
(OUT/'render_manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('PARALLEL_REVIEW_RENDERED',flush=True)

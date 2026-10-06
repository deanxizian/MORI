"""Render the actual least-tight failed candidate for review, never adoption."""
from pathlib import Path
import sys,json,hashlib
SCRIPT=Path(__file__).resolve();HERE=SCRIPT.parent;OUT=HERE/'cam_pitch_flex';ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from common import *
from render import camera
from validate import rigidtr
from validate_head_cleanup import geometry_record
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
expected=HERE/'assembly_feed_v3/open_mouth/cleaned/candidate.blend'
assert Path(bpy.data.filepath)==expected
load_collections();assembled();bpy.context.view_layer.update()
physical={o.name.removeprefix(PREFIX):o for o in parts() if o.get('group') not in ['dock','coupon']}
before={n:geometry_record(o) for n,o in physical.items()}
visible={'CAM_Mainboard','Yaw_Servo','Pitch_Servo','Pitch_Yoke'}
for c in ['DATUMS','KEEP_OUT','COUPONS','DOCK','ANNOTATIONS']:COLS[c].hide_render=True
for o in bpy.context.scene.objects:
    if o.type in ['MESH','CURVE']:o.hide_render=True
for n,o in physical.items():o.hide_render=n not in visible
diag=json.loads((OUT/'side/full_pair_diagnostic.json').read_text());choice=diag['best_combination_for_review']['candidates']
worst=diag['best_combination_for_review']['limiting_pair']['worst']['pitch_deg']
curves=np.load(OUT/'side/flex_candidates.npz');tails=np.load(HERE/'cam_pitch_port/departure_curves.npz')
body=np.load(HERE/'cam_pitch_port/lower_staging/body_partial_curves.npz')
colors=[(.07,.62,.70),(.90,.21,.06),(.3,.69,.08),(.67,.25,.80)]
generated=[]
def make_wire(name,points,i):
    c=bpy.data.curves.new(name,'CURVE');c.dimensions='3D';c.bevel_depth=.6604/2;c.bevel_resolution=3;c.use_fill_caps=True
    s=c.splines.new('POLY');s.points.add(len(points)-1)
    for q,p in zip(s.points,points):q.co=(*p,1)
    o=bpy.data.objects.new(name,c);bpy.context.scene.collection.objects.link(o)
    o['study_owner']='A8_PITCH_FLEX';o['part_class']='PLACEHOLDER';o['data_status']='ASSUMED'
    o['scope']='Prescribed unadopted wire path; failed0.3mm whole-bundle gap; not a supplier drawing'
    c.materials.append(material('A8_FLEX_WIRE_'+str(i),colors[i],roughness=.55));generated.append(o)
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=24;sc.cycles.use_denoising=True
sc.render.resolution_x=1200;sc.render.resolution_y=1150;sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG';sc.render.film_transparent=False
images=[]
for angle,label in [(0,'zero'),(worst,'tightest')]:
    for o in list(generated):bpy.data.objects.remove(o,do_unlink=True)
    generated=[];pose(0,angle);tr=np.asarray(rigidtr(0,angle))
    for i,index in enumerate(choice):
        pin=i+1;p=curves[f'pin{pin}_candidate{index}_pitch{angle}']
        end=tails[f'left_slot{i}']@tr[:3,:3].T+tr[:3,3]
        start=body[f'pin{pin}_yaw0'];start=start[start[:,2]>=183.]
        points=np.vstack([start,p[1:],end[-2::-1]])
        make_wire(f'A8_FLEX_{pin}',points,i)
    camera('A8_FLEX_REVIEW',(-110,95,286),(-8,-5,219),96)
    dest=OUT/f'{label}.png';sc.render.filepath=str(dest);bpy.ops.render.render(write_still=True)
    images.append({'file':dest.name,'sha256':sha(dest),'yaw_deg':0,'pitch_deg':angle,
        'camera_eye_mm':[-110,95,286],'target_mm':[-8,-5,219],'ortho_scale_mm':96})
assembled();bpy.context.view_layer.update()
assert all(geometry_record(o)==before[n] for n,o in physical.items())
# Save the same last rendered pose coherently, then reset only for the above
# source-geometry comparison. No source .blend is overwritten.
pose(0,worst)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'comparison.blend'))
result={'status':'PASS','scope':'Review illustration of a BLOCKED bundle, selective physical visibility',
    'source_script_sha256':sha(SCRIPT),'source_candidate_sha256':sha(expected),
    'source_pair_diagnostic_sha256':sha(OUT/'side/full_pair_diagnostic.json'),'source_curves_sha256':sha(OUT/'side/flex_candidates.npz'),
    'comparison_blend_sha256':sha(OUT/'comparison.blend'),'visible_source_parts':sorted(visible),
    'selected_indices_for_illustration':choice,'images':images,'geometry_unchanged':True,'main_applied':False,
    'physical_pin_color_meaning':'Geometric slot; photo-based conditional mapping only','harness_status':'BLOCKED'}
(OUT/'render_manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('PITCH_FLEX_RENDERED',flush=True)

"""Render the checked independent CAM anchor and its bench removal path."""
from pathlib import Path
import sys,json,hashlib
SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent
sys.path.insert(0,str(A8.parents[3]/'mechanical/scripts'))
from common import *
from render import camera
from validate import rigidtr
from validate_head_cleanup import geometry_record
from mathutils.bvhtree import BVHTree

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out=A8/'cam_anchors';candidate=out/'candidate_v3/cleaned'
assert Path(bpy.data.filepath)==candidate/'candidate.blend'
load_collections();assembled();bpy.context.view_layer.update()
physical={o.name.removeprefix(PREFIX):o for o in parts() if o.get('group') not in ['dock','coupon']}
before={n:geometry_record(o) for n,o in physical.items()}
for c in ['DATUMS','KEEP_OUT','COUPONS','DOCK','ANNOTATIONS']:COLS[c].hide_render=True
base=np.load(A8/'assembly_feed_v3/open_mouth/cleaned/Pitch_Yoke.npz')
tree=BVHTree.FromPolygons(base['vertices_mm'],base['triangles'].tolist(),all_triangles=True)
yoke=physical['Pitch_Yoke'];yoke.data.materials.clear()
yoke.data.materials.append(material('A8_CAM_EXISTING_HOST',(.6,.65,.67),roughness=.7))
for polygon in yoke.data.polygons:polygon.material_index=0
index=1
yoke.data.materials.append(material('A8_CAM_INTEGRAL_ANCHOR',(.04,.52,.66),roughness=.65))
for polygon in yoke.data.polygons:
    point=yoke.matrix_world@polygon.center
    in_addition_region=(-35.001<=point.x<=-5.511 and -7.001<=point.y<=-1.749 and 230.599<=point.z<=236.401)
    if in_addition_region and tree.find_nearest(point)[3]>.003:
        polygon.material_index=index

generated=[]
colors=[(.06,.57,.66),(.9,.23,.07),(.28,.62,.10),(.63,.25,.77)]
loops=np.load(A8/'cam_fan_in/short_tail_v2/curves.npz')
tails=np.load(A8/'cam_fan_in/short_tail_v2/tails.npz')
fans=np.load(A8/'cam_fan_in/four_bend_transition/curves.npz')
prefix=np.load(A8/'cam_pitch_port/lower_staging/body_partial_curves.npz')
def wires_at(angle):
    for o in generated:bpy.data.objects.remove(o,do_unlink=True)
    generated.clear();pose(0,angle);mat=np.asarray(rigidtr(0,angle))
    for slot in range(4):
        body=prefix[f'pin{slot+1}_yaw0'];fan=fans[f'pin{slot+1}_candidate0']
        core=loops[f'candidate0_slot{slot}_pitch{angle}'];tail=tails[f'slot{slot}']@mat[:3,:3].T+mat[:3,3]
        points=np.vstack([body[:-1],fan[:-1],core,tail[-2::-1]])
        data=bpy.data.curves.new(f'A8_CAM_ANCHOR_WIRE_{slot}','CURVE')
        data.dimensions='3D';data.bevel_depth=.6604/2;data.bevel_resolution=4;data.use_fill_caps=True
        spline=data.splines.new('POLY');spline.points.add(len(points)-1)
        for a,p in zip(spline.points,points):a.co=(*p,1)
        o=bpy.data.objects.new(f'A8_CAM_ANCHOR_WIRE_{slot}',data);bpy.context.scene.collection.objects.link(o)
        o['study_owner']='A8_CAM_ANCHOR_REVIEW';o['part_class']='PLACEHOLDER';o['data_status']='ASSUMED'
        o['scope']='Nominal prescribed wire shape, not physical flex simulation or pin colors'
        data.materials.append(material(f'A8_CAM_ANCHOR_WIRE_{slot}',colors[slot],roughness=.5));generated.append(o)

def visible(names,tie=True):
    for o in bpy.context.scene.objects:
        if o.type in ['MESH','CURVE']:
            o.hide_render=(o.name.removeprefix(PREFIX) not in names
                           and not (tie and o.name.startswith('A8_CAM_Tie_')))
    for o in generated:o.hide_render=not tie

sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=24;sc.cycles.use_denoising=True
sc.render.resolution_x=1200;sc.render.resolution_y=1000;sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG';sc.render.film_transparent=False
images=[]
def snap(name,eye,target,scale,description):
    camera('A8_CAM_ANCHOR_'+name,eye,target,scale)
    dest=out/(name+'.png');sc.render.filepath=str(dest);bpy.ops.render.render(write_still=True)
    images.append({'file':dest.name,'sha256':sha(dest),'description':description,
                   'camera_eye_mm':eye,'target_mm':target,'ortho_scale_mm':scale})

for angle,label in [(0,'anchor_zero'),(-20,'anchor_down20'),(25,'anchor_up25')]:
    wires_at(angle)
    visible({'Pitch_Yoke','Pitch_Servo','Pitch_Output','Yaw_Servo','CAM_Mainboard'})
    snap(label,(32,96,290),(-13,0,232),82,f'Nominal CAM loop; pitch {angle} deg, cyan is integral support, amber tie is an assumed allocation')
wires_at(0)
visible({'Pitch_Yoke','Pitch_Servo','Pitch_Output'})
snap('anchor_detail',(26,65,270),(-18,-2,230),48,'Local support and tie; color only, no geometry separation or overlay')

# Reverse this removal path for assembly. The tie, yaw servo and pitch head
# are not yet installed at this stage, matching the service-check prerequisites.
report=json.loads((candidate/'servo_installation_replay.json').read_text())
path=next(r['waypoints_mm'] for r in report['accepted'] if r['waypoints_mm'][2][1]==6.5)
assembled();bpy.context.view_layer.update()
bench={'Pitch_Yoke','Pitch_Servo','Pitch_Output'} | {n for n in physical if n.startswith('Pitch_Bearing')}
base_mats={n:physical[n].matrix_world.copy() for n in ['Pitch_Servo','Pitch_Output']}
for i,translation in enumerate(path):
    visible(bench,False)
    for n,mat in base_mats.items():physical[n].matrix_world=Matrix.Translation(Vector(translation))@mat
    bpy.context.view_layer.update()
    snap(f'removal_{i}',(92,145,315),(-7,3,229 if i<4 else 250),100 if i<4 else 140,
         f'Bench removal step {i}; servo/output translation {translation} mm')
for n,mat in base_mats.items():physical[n].matrix_world=mat
assembled();bpy.context.view_layer.update()
assert all(geometry_record(o)==before[n] for n,o in physical.items())
wires_at(0)
visible({'Pitch_Yoke','Pitch_Servo','Pitch_Output','Yaw_Servo','CAM_Mainboard','Yaw_Base','Load_Frame'})
camera('A8_CAM_ANCHOR_OVERVIEW',(-126,138,282),(-8,-4,217),128)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'review.blend'))
manifest={'status':'PASS','scope':'Presentation views of independent candidate and checked bench poses',
          'script_sha256':sha(SCRIPT),'candidate_blend_sha256':sha(candidate/'candidate.blend'),
          'installation_report_sha256':sha(candidate/'servo_installation_replay.json'),
          'review_blend_sha256':sha(out/'review.blend'),'images':images,
          'physical_geometry_preserved':True,'main_applied':False,
          'wire_colors':'Geometric slots, no electrical color assignment'}
(out/'render_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('ANCHOR_REVIEW_RENDER',len(images),'PASS',flush=True)

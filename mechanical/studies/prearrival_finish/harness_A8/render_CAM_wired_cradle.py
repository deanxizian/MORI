"""Show the tested installation poses and failures without changing the main."""
from pathlib import Path
import sys,json,hashlib
VR_SCRIPT=Path(__file__).resolve();VR_ROOT=VR_SCRIPT.parent;VR_OUT=VR_ROOT/'cam_wired_cradle'
sys.path.insert(0,str(VR_ROOT.parents[3]/'mechanical/scripts'))
sys.path.insert(0,str(VR_ROOT.parents[3]/'mechanical/scripts/vendor'))
import manifold3d as manifold
from common import *
from render import camera
from validate_head_cleanup import geometry_record
VR_SOURCE=VR_ROOT/'cam_pitch_anchor/connector_anchor/review.blend'
assert Path(bpy.data.filepath)==VR_SOURCE
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
screen=json.loads((VR_OUT/'screen.json').read_text());witness=json.loads((VR_OUT/'witnesses.json').read_text())
assert screen['status']=='BLOCKED' and witness['curves_sha256']==sha(VR_OUT/'review_curves.npz')
load_collections();assembled();bpy.context.view_layer.update()
physical={o.name.removeprefix(PREFIX):o for o in parts() if o.get('group') not in ['dock','coupon']}
before={n:geometry_record(o) for n,o in physical.items()};matrices={n:o.matrix_world.copy() for n,o in physical.items()}
locations={n:o.location.copy() for n,o in physical.items()}
for c in ['DATUMS','KEEP_OUT','COUPONS','DOCK','ANNOTATIONS']:COLS[c].hide_render=True
moving_names=set(screen['moving_ids'])|{'CAM_Mainboard'}
ties={o.name:o for o in bpy.data.objects if o.name in ['A8_CAM_CONNECTOR_head','A8_CAM_CONNECTOR_band']}
assert len(ties)==2
tie_mats={n:o.matrix_world.copy() for n,o in ties.items()}
tie_locations={n:o.location.copy() for n,o in ties.items()}
moving_objects={o for n,o in physical.items() if n in moving_names}|set(ties.values())
assert all(o.parent not in moving_objects for o in moving_objects)
def local_world_z(o):
    parent_map=o.parent.matrix_world@o.matrix_parent_inverse if o.parent else Matrix.Identity(4)
    return parent_map.to_3x3().inverted()@Vector((0,0,1))
local_shifts={n:local_world_z(o) for n,o in physical.items() if n in moving_names}
tie_shifts={n:local_world_z(o) for n,o in ties.items()}
extras={};wires=[];arrays=np.load(VR_OUT/'review_curves.npz')
colors=[(.06,.57,.66),(.9,.23,.07),(.28,.62,.10),(.63,.25,.77)]
def mesh_object(name,v,f,color):
    d=bpy.data.meshes.new('A8_CAM_INSERT_'+name);d.from_pydata(v.tolist(),[],f.tolist());d.update()
    o=bpy.data.objects.new('A8_CAM_INSERT_'+name,d);bpy.context.scene.collection.objects.link(o)
    d.materials.append(material('A8_CAM_INSERT_MAT_'+name,color,roughness=.6))
    o['study_owner']='A8_CAM_WIRED_CRADLE';o['part_class']='PLACEHOLDER';o['data_status']='ASSUMED'
    extras[name]=o;return o
a=np.load(VR_ROOT/'cam_pitch_port/allocation_meshes.npz')
housing_obj=mesh_object('catalogue_housing',a['housing_v'],a['housing_f'],(.94,.64,.2))
for n in ['head','band']:
    a=np.load(VR_ROOT/f'cam_tie_install/oriented_{n}.npz')
    mesh_object('yaw_tie_'+n,a['vertices_mm'],a['triangles'],(.94,.64,.2))
# Coincident faces of the assumed full head and formed band otherwise look
# like a spurious hole. Hide only the overlapping band for presentation; the
# tested nonempty source solids are unchanged.
hh=np.load(VR_ROOT/'cam_tie_install/oriented_head.npz');bb=np.load(VR_ROOT/'cam_tie_install/oriented_band.npz')
hm=manifold.Manifold(manifold.Mesh64(hh['vertices_mm'],hh['triangles']))
bm=manifold.Manifold(manifold.Mesh64(bb['vertices_mm'],bb['triangles']))
bound=np.array(hm.bounding_box());cut=manifold.Manifold.cube((bound[3:]-bound[:3]+.004).tolist()).translate((bound[:3]-.002).tolist())
visible_band=(bm-cut).to_mesh64();band_mesh=extras['yaw_tie_band'].data
band_mesh.clear_geometry();band_mesh.from_pydata(visible_band.vert_properties[:,:3].tolist(),[],visible_band.tri_verts.tolist());band_mesh.update()
bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,radius=.95)
mark=bpy.context.object;mark.name='A8_CAM_INSERT_failure_marker'
mark.data.materials.append(material('A8_CAM_INSERT_MARKER',(.94,.08,.045),roughness=.5))
mark['study_owner']='A8_CAM_WIRED_CRADLE';mark['scope']='Presentation marker, not physical hardware';extras['marker']=mark

def set_pose(h,show_marker=False,local=False):
    # Only translate moving objects. Reassigning every world matrix needlessly
    # decomposes fixed rotated parts and introduces numerical pose drift.
    for n,o in physical.items():
        if n in moving_names:o.location=locations[n]+local_shifts[n]*h
    for n,o in ties.items():o.location=tie_locations[n]+tie_shifts[n]*h
    housing_obj.matrix_world=Matrix.Translation((0,0,h))
    for o in wires:bpy.data.objects.remove(o,do_unlink=True)
    wires.clear()
    for slot in range(4):
        pts=np.vstack([arrays[f'body{slot}'][:-1],arrays[f'fan{slot}'][:-1],arrays[f'lift{h}_core{slot}'],arrays[f'lift{h}_tail{slot}'][-2::-1]])
        d=bpy.data.curves.new(f'A8_CAM_INSERT_wire{slot}','CURVE');d.dimensions='3D';d.bevel_depth=.3302;d.bevel_resolution=3;d.use_fill_caps=True
        s=d.splines.new('POLY');s.points.add(len(pts)-1)
        for a,p in zip(s.points,pts):a.co=(*p,1)
        o=bpy.data.objects.new(f'A8_CAM_INSERT_wire{slot}',d);bpy.context.scene.collection.objects.link(o)
        d.materials.append(material(f'A8_CAM_INSERT_WIREMAT_{slot}',colors[slot],roughness=.55))
        o['study_owner']='A8_CAM_WIRED_CRADLE';o['part_class']='PLACEHOLDER';o['data_status']='ASSUMED'
        o['scope']='Prescribed constant-length curve; not natural cable simulation or pin colour';wires.append(o)
    names={'Pitch_Yoke','Yaw_Base','Yaw_Servo','Pitch_Servo','Pitch_Cradle','CAM_Mainboard'}|{n for n in physical if n.startswith(('CAM_Mount_','Head_Cradle_Insert_','Onboard_MIC_'))}
    if local:names-={'Yaw_Servo','Pitch_Servo','Pitch_Cradle','CAM_Mainboard'}|{n for n in names if n.startswith(('CAM_Mount_','Onboard_MIC_','Head_Cradle_Insert_'))}
    for o in bpy.context.scene.objects:
        if o.type in ['MESH','CURVE']:o.hide_render=o.name.removeprefix(PREFIX) not in names and o not in wires and o not in extras.values() and o not in ties.values()
    if show_marker:
        row=next(r for r in witness['rows'] if r['lift_mm']==h);mark.location=np.mean(row['points_mm'],axis=0)
    mark.hide_render=not show_marker
    bpy.context.view_layer.update()

sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=16;sc.cycles.use_denoising=True
sc.render.resolution_x=1200;sc.render.resolution_y=1000;sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG';sc.render.film_transparent=False
images=[]
def snap(name,h,eye,target,scale,scope,local=False):
    set_pose(h,show_marker=h in [9.,42.],local=local)
    camera('A8_CAM_INSERT_'+name,eye,target,scale);sc.render.filepath=str(VR_OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
    images.append({'file':name+'.png','sha256':sha(VR_OUT/(name+'.png')),'lift_mm':h,'scope':scope})
snap('seated',0.,(-100,130,315),(-5,0,240),170,'Seated candidate with four modeled wires; optics, trunnions and outer shells not fitted')
snap('raised42',42.,(-100,130,315),(-5,0,240),170,'Rejected 42 mm lift: red point marks self-intersection of one prescribed wire')
snap('wire_conflict42',42.,(-55,66,255),(-9.7,-1.5,244.1),29,'Self-intersection detail; servos, cradle and CAM board hidden only to expose the wires',True)
snap('neck_gap9',9.,(-60,70,197),(-10.2,10.85,211.3),30,'9 mm lift falls below the chosen 0.3 mm noncontact allowance; no physical overlap claim',True)
set_pose(0.);camera('A8_CAM_INSERT_final',(-100,130,315),(-5,0,240),170)
for n,o in physical.items():
    if n in moving_names:o.location=locations[n]
for n,o in ties.items():o.location=tie_locations[n]
bpy.context.view_layer.update();assert all(geometry_record(o)==before[n] for n,o in physical.items())
sc['independent_unapproved_study']='CAM/cradle prescribed assembly family fails at 42 mm; main M1.47 unchanged'
bpy.ops.wm.save_as_mainfile(filepath=str(VR_OUT/'review.blend'))
report={'status':'PASS','script_sha256':sha(VR_SCRIPT),'source_main_sha256':screen['source_main_sha256'],
    'source_candidate_sha256':sha(VR_SOURCE),'screen_sha256':sha(VR_OUT/'screen.json'),'witnesses_sha256':sha(VR_OUT/'witnesses.json'),
    'physical_parts_restored_unchanged':len(physical),'review_sha256':sha(VR_OUT/'review.blend'),
    'images':images,'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False}
report['render_only']='Overlap of the full yaw-tie head and band hidden to avoid coincident display faces; source collision NPZ files unchanged.'
(VR_OUT/'render_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('CAM_WIRED_RENDER_DONE',len(images),'PASS',flush=True)

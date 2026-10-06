"""Save and render the independently checked CAM connector anchor candidate."""
from pathlib import Path
import sys,json,hashlib
RC_SCRIPT=Path(__file__).resolve();RC_ROOT=RC_SCRIPT.parent
sys.path.insert(0,str(RC_ROOT.parents[3]/'mechanical/scripts'))
sys.path.insert(0,str(RC_ROOT.parents[3]/'mechanical/scripts/vendor'))
from common import *
from render import camera
from validate import rigidtr
from validate_head_cleanup import geometry_record
from head_surface_display import planar_faces
from mathutils.bvhtree import BVHTree
import manifold3d as manifold
RC_OUT=RC_ROOT/'cam_pitch_anchor/connector_anchor'
RC_SOURCE=RC_ROOT/'cam_anchors/candidate_v3/cleaned/candidate.blend'
assert Path(bpy.data.filepath)==RC_SOURCE
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load_collections();assembled();bpy.context.view_layer.update()
physical={o.name.removeprefix(PREFIX):o for o in parts() if o.get('group') not in ['dock','coupon']}
before={n:geometry_record(o) for n,o in physical.items()}
host=physical['Pitch_Cradle'];old_vertices=[host.matrix_world@v.co for v in host.data.vertices]
old_faces=[list(p.vertices) for p in host.data.polygons]
old_tree=BVHTree.FromPolygons(old_vertices,old_faces,all_triangles=True)
a=np.load(RC_OUT/'Pitch_Cradle.npz');desired=manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles']))
mesh=bpy.data.meshes.new('A8_CAM_CONNECTOR_Pitch_Cradle')
mesh.from_pydata(a['vertices_mm'].tolist(),[],a['triangles'].tolist());mesh.update()
host.data=mesh;host.matrix_world=Matrix.Identity(4)
mesh.materials.append(material('A8_CAM_CONNECTOR_EXISTING',(.63,.68,.7),roughness=.7))
mesh.materials.append(material('A8_CAM_CONNECTOR_ADDITION',(.03,.48,.60),roughness=.7))
for p in mesh.polygons:
    p.use_smooth=False
    local=(-12.801<=p.center.x<=-7.399 and -30.501<=p.center.y<=-21.049 and 210.299<=p.center.z<=218.301)
    p.material_index=1 if local and old_tree.find_nearest(p.center)[3]>.003 else 0
# Restore the project's display-only planar/curved normal policy on this new
# mesh, without calling the helper that would overwrite a main-model report.
flat=planar_faces(host)
edge_faces=[[] for _ in mesh.edges]
for p,is_flat in zip(mesh.polygons,flat):
    p.use_smooth=not is_flat and p.material_index==0
    for k in p.loop_indices:edge_faces[mesh.loops[k].edge_index].append(p.index)
for e,fs in zip(mesh.edges,edge_faces):
    if len(fs)!=2:continue
    a,b=fs;delta=mesh.polygons[a].normal.angle(mesh.polygons[b].normal,0)
    if delta>math.radians(P['head_surface_display']['sharp_edge_angle_deg']) or ((flat[a] or flat[b]) and delta>math.radians(P['head_surface_display']['planar_alignment_tolerance_deg'])):e.use_edge_sharp=True
mesh.update();normals=[n.vector[:] for n in mesh.corner_normals]
for p,is_flat in zip(mesh.polygons,flat):
    if is_flat or p.material_index==1:
        for k in p.loop_indices:normals[k]=p.normal[:]
mesh.normals_split_custom_set(normals);mesh.update()
host['independent_candidate']='A8 CAM connector strain relief; main not adopted'
v=np.array([host.matrix_world@p.co for p in mesh.vertices]);f=np.array([list(p.vertices) for p in mesh.polygons],np.uint64)
stored=manifold.Manifold(manifold.Mesh64(v,f));assert stored.status()==manifold.Error.NoError and len(stored.decompose())==1
diff=abs(float((stored-desired).volume()))+abs(float((desired-stored).volume()))
assert diff<.05,diff
oldsolid=manifold.Manifold(manifold.Mesh64(np.array(old_vertices),np.array(old_faces,np.uint64)))
region=manifold.Manifold.cube([5.402,9.452,8.002]).translate([-12.801,-30.501,210.299])
outside_difference=abs(float(((stored-oldsolid)-region).volume()))+abs(float(((oldsolid-stored)-region).volume()))
assert outside_difference<.05,outside_difference
assert all(geometry_record(o)==before[n] for n,o in physical.items() if n!='Pitch_Cradle')
for c in ['DATUMS','KEEP_OUT','COUPONS','DOCK','ANNOTATIONS']:COLS[c].hide_render=True
extras={}
def solid_object(name,path,color):
    aa=np.load(path);m=bpy.data.meshes.new('A8_CAM_CONNECTOR_'+name)
    m.from_pydata(aa['vertices_mm'].tolist(),[],aa['triangles'].tolist());m.update()
    o=bpy.data.objects.new('A8_CAM_CONNECTOR_'+name,m);bpy.context.scene.collection.objects.link(o)
    m.materials.append(material('A8_CAM_CONNECTOR_MAT_'+name,color,roughness=.7))
    o['study_owner']='A8_CAM_CONNECTOR_ANCHOR';o['category']='PLACEHOLDER';o['data_status']='ASSUMED'
    o['scope']='Catalogue dimensional allocation, no measured latch/grip qualification';extras[name]=o
    return o
solid_object('head',RC_OUT/'z212.0_head.npz',(.95,.52,.08))
solid_object('band',RC_OUT/'z212.0_band.npz',(.95,.52,.08))
# Hide only the band portion inside the full head box for display, leaving
# every collision NPZ unchanged. Otherwise coincident surfaces look like holes.
aa=np.load(RC_OUT/'z212.0_head.npz');hm=manifold.Manifold(manifold.Mesh64(aa['vertices_mm'],aa['triangles']));bb=np.array(hm.bounding_box())
aa=np.load(RC_OUT/'z212.0_band.npz');bm=manifold.Manifold(manifold.Mesh64(aa['vertices_mm'],aa['triangles']))
hidden=manifold.Manifold.cube((bb[3:]-bb[:3]+.004).tolist()).translate((bb[:3]-.002).tolist())
am=(bm-hidden).to_mesh64();extras['band'].data.clear_geometry();extras['band'].data.from_pydata(am.vert_properties[:,:3].tolist(),[],am.tri_verts.tolist());extras['band'].data.update()

loops=np.load(RC_ROOT/'cam_fan_in/short_tail_v2/curves.npz');tails=np.load(RC_ROOT/'cam_fan_in/short_tail_v2/tails.npz')
fans=np.load(RC_ROOT/'cam_fan_in/four_bend_transition/curves.npz');prefix=np.load(RC_ROOT/'cam_pitch_port/lower_staging/body_partial_curves.npz')
wires=[];colors=[(.06,.57,.66),(.9,.23,.07),(.28,.62,.10),(.63,.25,.77)]
def set_pose(angle,local=False):
    for o in wires:bpy.data.objects.remove(o,do_unlink=True)
    wires.clear();pose(0,angle);mat=np.asarray(rigidtr(0,angle))
    for o in extras.values():o.matrix_world=Matrix(mat.tolist())
    for slot in range(4):
        if local:
            p=np.array([[tails[f'slot{slot}'][0,0],tails[f'slot{slot}'][0,1],200.],tails[f'slot{slot}'][0]])
            pts=p@mat[:3,:3].T+mat[:3,3]
        else:
            tail=tails[f'slot{slot}']@mat[:3,:3].T+mat[:3,3]
            pts=np.vstack([prefix[f'pin{slot+1}_yaw0'][:-1],fans[f'pin{slot+1}_candidate0'][:-1],loops[f'candidate0_slot{slot}_pitch{angle}'],tail[-2::-1]])
        d=bpy.data.curves.new(f'A8_CAM_CONNECTOR_WIRE_{slot}','CURVE');d.dimensions='3D';d.bevel_depth=.3302;d.bevel_resolution=3;d.use_fill_caps=True
        s=d.splines.new('POLY');s.points.add(len(pts)-1)
        for t,p in zip(s.points,pts):t.co=(*p,1)
        o=bpy.data.objects.new(f'A8_CAM_CONNECTOR_WIRE_{slot}',d);bpy.context.scene.collection.objects.link(o)
        d.materials.append(material(f'A8_CAM_CONNECTOR_WIREMAT_{slot}',colors[slot],roughness=.6))
        o['study_owner']='A8_CAM_CONNECTOR_ANCHOR';o['category']='PLACEHOLDER';o['data_status']='ASSUMED';o['scope']='Temporary straight staging' if local else 'Prescribed wire shape; no passive flex or pin-color claim'
        wires.append(o)
def visible(names,tie=True):
    for o in bpy.context.scene.objects:
        if o.type in ['MESH','CURVE']:o.hide_render=o.name.removeprefix(PREFIX) not in names and o not in wires and not(tie and o in extras.values())
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=16;sc.cycles.use_denoising=True
sc.render.resolution_x=1200;sc.render.resolution_y=1000;sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG';sc.render.film_transparent=False
images=[]
def snap(name,eye,target,scale,scope):
    camera('A8_CAM_CONNECTOR_'+name,eye,target,scale);sc.render.filepath=str(RC_OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
    images.append({'file':name+'.png','sha256':sha(RC_OUT/(name+'.png')),'scope':scope})
set_pose(0,True);visible({'Pitch_Cradle','CAM_Mainboard'})
snap('connector_detail',(-2,46,187),(-10,-24,214),34,'Detached CAM/cradle from below; cyan is integral addition, amber is tie allocation, straight wires temporary')
set_pose(0,False);visible({'Pitch_Cradle','CAM_Mainboard','Pitch_Yoke','Yaw_Servo','Pitch_Servo'})
snap('connector_overview',(-88,104,292),(-7,-7,233),96,'Connected prescribed wires with all original hardware datums retained')
set_pose(-20,False);visible({'Pitch_Cradle','CAM_Mainboard','Pitch_Yoke','Yaw_Servo','Pitch_Servo'})
snap('connector_down20',(-88,104,292),(-7,-7,233),96,'Pitch -20 degree finite pose; no physical cable behavior qualification')
set_pose(0,True);visible({'Pitch_Cradle','CAM_Mainboard'},False)
snap('connector_before_tie',(-2,46,187),(-10,-24,214),34,'Install preplugged board on detached cradle, then place/tighten tie; flexible threading pending')
set_pose(0,False);visible({'Pitch_Cradle','CAM_Mainboard','Pitch_Yoke','Yaw_Servo','Pitch_Servo'})
camera('A8_CAM_CONNECTOR_final',(-88,104,292),(-7,-7,233),96)
assembled();bpy.context.view_layer.update()
assert all(geometry_record(o)==before[n] for n,o in physical.items() if n!='Pitch_Cradle')
sc['independent_unapproved_study']='CAM connector anchor; unchanged main M1.47; no manufacturing release'
bpy.ops.wm.save_as_mainfile(filepath=str(RC_OUT/'review.blend'))
report={'status':'PASS','source_candidate_sha256':sha(RC_SOURCE),'source_main_sha256':sha(RC_ROOT.parents[3]/'mechanical/mori_v1_2.blend'),
 'script_sha256':sha(RC_SCRIPT),'root_report_sha256':sha(RC_OUT/'root_v3_screen.json'),'images':images,
 'unchanged_other_physical_parts':len(physical)-1,'changed_existing_ids':['Pitch_Cradle'],'stored_volume_components':1,
 'stored_symmetric_volume_difference_mm3':diff,'outside_change_region_difference_mm3':outside_difference,'review_sha256':sha(RC_OUT/'review.blend'),
 'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False,
 'render_only':'Internal band/head overlap hidden; saved collision NPZ unmodified. Other scene objects retained and hidden for local views.'}
(RC_OUT/'render_manifest.json').write_text(json.dumps(report,indent=2)+'\n')
print('CAM_CONNECTOR_RENDER_DONE',len(images),'PASS',flush=True)

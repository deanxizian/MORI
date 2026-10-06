"""Inspection images for the oriented tie and its bench tool allocation."""
from pathlib import Path
import sys,json,hashlib
TIR_SCRIPT=Path(__file__).resolve();TIR_A8=TIR_SCRIPT.parent
sys.path.insert(0,str(TIR_A8.parents[3]/'mechanical/scripts'))
from common import *
from render import camera
from validate_head_cleanup import geometry_record
sys.path.insert(0,str(TIR_A8.parents[3]/'mechanical/scripts/vendor'))
import manifold3d as manifold
TIR_OUT=TIR_A8/'cam_tie_install'
TIR_CANDIDATE=TIR_A8/'cam_anchors/candidate_v3/cleaned/candidate.blend'
assert Path(bpy.data.filepath)==TIR_CANDIDATE
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load_collections();assembled();bpy.context.view_layer.update()
physical={o.name.removeprefix(PREFIX):o for o in parts() if o.get('group') not in ['dock','coupon']}
before={n:geometry_record(o) for n,o in physical.items()}
for c in ['DATUMS','KEEP_OUT','COUPONS','DOCK','ANNOTATIONS']:COLS[c].hide_render=True
added={}
def from_npz(name,color):
    a=np.load(TIR_OUT/(name+'.npz'))
    if name=='oriented_band':
        # The full head allocation deliberately includes the return strap.
        # Hide its internal overlap only in this render, so coincident end
        # faces do not resemble a fabricated latch hole. Collision solids stay.
        h=np.load(TIR_OUT/'oriented_head.npz')
        bounds=np.array(manifold.Manifold(manifold.Mesh64(h['vertices_mm'],h['triangles'])).bounding_box())
        hidden=manifold.Manifold.cube((bounds[3:]-bounds[:3]+.004).tolist()).translate((bounds[:3]-.002).tolist())
        exterior=manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles']))-hidden
        assert exterior.volume()>1
        clean=exterior.to_mesh64()
        a={'vertices_mm':np.asarray(clean.vert_properties[:,:3]),'triangles':np.asarray(clean.tri_verts)}
    d=bpy.data.meshes.new('A8_TIE_INSTALL_'+name)
    d.from_pydata(a['vertices_mm'].tolist(),[],a['triangles'].tolist());d.update()
    o=bpy.data.objects.new('A8_TIE_INSTALL_'+name,d);bpy.context.scene.collection.objects.link(o)
    d.materials.append(material('A8_TIE_INSTALL_MAT_'+name,color,roughness=.7))
    o['study_owner']='A8_TIE_INSTALLATION';o['part_class']='PLACEHOLDER';o['data_status']='ASSUMED'
    o['scope']='Oriented catalogue work allocation, not detailed purchased CAD'
    added[name]=o
    return o
for n in ['oriented_head','oriented_band']:from_npz(n,(.95,.53,.08))
from_npz('cutter_allocation',(.1,.52,.42))
from_npz('tail_corridor',(.67,.69,.73))
# Show the checked solid's sharp edges, not an opaque box hiding the work.
# This curve is presentation-only; collision checks keep the full solid.
def edge_view(key):
    obj=added[key];mesh=obj.data
    adjacent={}
    for poly in mesh.polygons:
        for edge in poly.edge_keys:adjacent.setdefault(tuple(sorted(edge)),[]).append(poly.normal.copy())
    curves=bpy.data.curves.new('A8_TIE_INSTALL_'+key+'_edges','CURVE')
    curves.dimensions='3D';curves.bevel_depth=.10;curves.bevel_resolution=2
    for edge,normals in adjacent.items():
        if len(normals)==2 and normals[0].dot(normals[1])>.99:continue
        spline=curves.splines.new('POLY');spline.points.add(1)
        for pt,idx in zip(spline.points,edge):pt.co=(*mesh.vertices[idx].co,1.)
    shown=bpy.data.objects.new('A8_TIE_INSTALL_'+key+'_edges',curves)
    bpy.context.scene.collection.objects.link(shown)
    curves.materials.append(material('A8_TIE_INSTALL_WORK_EDGES',(.05,.42,.25),roughness=.6))
    shown['study_owner']='A8_TIE_INSTALLATION';shown['scope']='Presentation edges of checked solid tool envelope'
    obj.hide_render=True;obj.hide_viewport=True
    added[key]=shown
edge_view('cutter_allocation')
colors=[(.06,.57,.66),(.9,.23,.07),(.28,.62,.10),(.63,.25,.77)]
xs=[-9.712500143,-8.712500143,-7.712500143,-6.712500143]
for slot,x in enumerate(xs):
    d=bpy.data.curves.new(f'A8_TIE_INSTALL_loose_{slot}','CURVE')
    d.dimensions='3D';d.bevel_depth=.6604/2;d.bevel_resolution=3;d.use_fill_caps=True
    s=d.splines.new('POLY');s.points.add(1)
    s.points[0].co=(x,-1.5,229.9,1.);s.points[1].co=(x,-1.5,274.9,1.)
    o=bpy.data.objects.new(f'A8_TIE_INSTALL_loose_{slot}',d);bpy.context.scene.collection.objects.link(o)
    d.materials.append(material(f'A8_TIE_INSTALL_WIRE_{slot}',colors[slot],roughness=.6))
    o['part_class']='PLACEHOLDER';o['data_status']='ASSUMED';o['study_owner']='A8_TIE_INSTALLATION'
    o['scope']='Local loose staging column only, not full harness routing or electrical color'
    added[f'wire_{slot}']=o

bench={'Pitch_Yoke','Pitch_Servo','Pitch_Output'}|{n for n in physical if n.startswith(('Pitch_Bearing','Head_Pitch_Ear_'))}
def visibility(keys):
    for o in bpy.context.scene.objects:
        if o.type in ['MESH','CURVE']:
            o.hide_render=o.name.removeprefix(PREFIX) not in bench and o not in [added[k] for k in keys]

sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=16;sc.cycles.use_denoising=True
sc.render.resolution_x=1200;sc.render.resolution_y=1000;sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG';sc.render.film_transparent=False
images=[]
def snap(name,eye,target,scale,scope):
    camera('A8_TIE_INSTALL_'+name,eye,target,scale)
    sc.render.filepath=str(TIR_OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
    images.append({'file':name+'.png','sha256':sha(TIR_OUT/(name+'.png')),'scope':scope})
visibility({'oriented_head','oriented_band'}|{f'wire_{s}' for s in range(4)})
snap('tie_orientation',(28,65,273),(-16,-2,232),49,'Amber strap/head are oriented dimensional allocations; wires are local loose columns')
visibility({'oriented_head','oriented_band','cutter_allocation'}|{f'wire_{s}' for s in range(4)})
snap('tool_detail',(40,65,265),(-9,1,234),40,'Green edges show the checked solid cutter work envelope; local wires staged behind tool')
snap('tool_overview',(105,150,346),(-4,5,282),158,'Cutter may approach from above on the detached bench assembly; final pitch loop not yet formed')
visibility({'oriented_head','oriented_band'})
for n in ['oriented_head','oriented_band']:added[n].location.z=-12.
snap('ring_below',(35,70,273),(-13,-2,226),51,'Blocked example: preclosed ring intersects installed pitch servo; not a valid slide-on sequence')
for n in ['oriented_head','oriented_band']:added[n].location.z=0
visibility({'oriented_head','oriented_band'}|{f'wire_{s}' for s in range(4)})
camera('A8_TIE_INSTALL_final',(28,65,273),(-16,-2,232),49)
bpy.context.view_layer.update()
assert all(geometry_record(o)==before[n] for n,o in physical.items())
sc['independent_unapproved_study']='A8 oriented tie and bench tooling; main not updated'
bpy.ops.wm.save_as_mainfile(filepath=str(TIR_OUT/'review.blend'))
(TIR_OUT/'render_manifest.json').write_text(json.dumps({'status':'PASS','script_sha256':sha(TIR_SCRIPT),
 'source_candidate_sha256':sha(TIR_CANDIDATE),'physical_geometry_preserved':True,
 'review_sha256':sha(TIR_OUT/'review.blend'),'images':images,'main_applied':False,
 'presentation_only':'Cutter sharp edges; band inside head hidden with a 0.002 mm render-only overlap margin to avoid coincident float faces. Collision solids unchanged.'},indent=2)+'\n')
print('TIE_INSTALL_RENDER',len(images),'PASS',flush=True)

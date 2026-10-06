"""MORI shared functions. All coordinates are mm, not metres. No external modules."""
import bpy, bmesh, json, math, os, sys, csv
from pathlib import Path
from mathutils import Vector, Matrix

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
OWNER = 'mori_v1_stage_a'
PREFIX = 'MORI_V1__'
P = json.loads((PROJECT/'config/geometry.json').read_text())
INTERFACES = json.loads((PROJECT/'contracts/mechanical_interfaces.json').read_text())
COLS = {}
MATS = {}
sys.path.insert(0,str(ROOT/'scripts/vendor'))
import numpy as np
try:
    import manifold3d as manifold
except ImportError as exc:
    raise RuntimeError('Install manifold3d==3.5.3 into scripts/vendor with Blender\'s Python; see README.md') from exc
SOLIDS={}

def derived():
    br=P['body_diameter_mm']/2; hr=P['head_diameter_mm']/2; wr=P['wheel_diameter_mm']/2
    body_min_local_z=-br  # Both declared profile variants retain poles at +/-R.
    bz=P['ground_clearance_mm']-body_min_local_z; top=bz+br-P['body_top_cut_depth_mm']
    hz=top+hr-P['head_embedding_depth_mm']
    return dict(body_radius=br,head_radius=hr,wheel_radius=wr,body_z=bz,body_top_z=top,head_z=hz,
        wheel_z=wr,wheel_x=P['body_side_cut_x_mm']+P['wheel_body_gap_mm']+P['wheel_width_mm']/2,
        axle_drop=bz-wr,normal_height_mm=hz+hr,face_y=P['display']['face_y_from_head_mm'])
D=derived()

def body_z_mm(relative_z_mm):
    """Position anchored to the body sphere center, not a second ground height."""
    return D["body_z"]+relative_z_mm


def mark(block):
    block['mori_owner']=OWNER
    return block

def setup_scene():
    SOLIDS.clear()
    scene=bpy.data.scenes.get('MORI_V1_Assembly')
    if scene is None: scene=bpy.data.scenes.new('MORI_V1_Assembly')
    bpy.context.window.scene=scene
    for o in list(bpy.data.objects):
        if o.get('mori_owner')==OWNER: bpy.data.objects.remove(o,do_unlink=True)
    for c in list(bpy.data.collections):
        if c.get('mori_owner')==OWNER and not c.objects and not c.children:
            bpy.data.collections.remove(c)
    for coll in [bpy.data.meshes,bpy.data.curves,bpy.data.cameras,bpy.data.lights,bpy.data.materials]:
        for b in list(coll):
            if b.get('mori_owner')==OWNER and b.users==0: coll.remove(b)
    scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=0.001
    scene.unit_settings.length_unit='MILLIMETERS'
    for name in ['PRINTABLE','PURCHASED_REFERENCE','PLACEHOLDER','ANNOTATIONS','CAMERAS_LIGHTS','DATUMS','CONTROLS','COUPONS','DOCK','KEEP_OUT']:
        c=bpy.data.collections.get(PREFIX+name)
        if not c:
            c=mark(bpy.data.collections.new(PREFIX+name)); scene.collection.children.link(c)
        COLS[name]=c
    COLS['DATUMS'].hide_render=True; COLS['DATUMS'].hide_viewport=True
    COLS['ANNOTATIONS'].hide_render=True; COLS['ANNOTATIONS'].hide_viewport=True
    COLS['COUPONS'].hide_render=True; COLS['COUPONS'].hide_viewport=True
    scene['mori_owner']=OWNER; scene['front_direction']='+Y'; scene['units_contract']='1 coordinate = 1 mm; STL in mm'
    scene['reference_images']='V1 specification; historical imagery is non-authoritative'
    COLS['KEEP_OUT'].hide_render=True; COLS['KEEP_OUT'].hide_viewport=True; COLS['DOCK'].hide_render=True; COLS['DOCK'].hide_viewport=True; COLS['COUPONS'].hide_render=True
    return scene

def load_collections():
    for c in bpy.data.collections:
        if c.get('mori_owner')==OWNER: COLS[c.name.removeprefix(PREFIX)]=c

def material(name, color, metallic=0, roughness=.5, emission=0, transmission=0):
    m=bpy.data.materials.get(PREFIX+name) or mark(bpy.data.materials.new(PREFIX+name))
    m.diffuse_color=(*color,1); m.use_nodes=True
    n=next((node for node in m.node_tree.nodes if node.type=='BSDF_PRINCIPLED'),None)
    if n is None: n=m.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
    n.inputs['Base Color'].default_value=(*color,1)
    n.inputs['Metallic'].default_value=metallic; n.inputs['Roughness'].default_value=roughness
    if 'Transmission Weight' in n.inputs: n.inputs['Transmission Weight'].default_value=transmission
    if 'Emission Color' in n.inputs:
        n.inputs['Emission Color'].default_value=(*color,1); n.inputs['Emission Strength'].default_value=emission
    MATS[name]=m; return m

def move_collection(o,name):
    for c in list(o.users_collection): c.objects.unlink(o)
    COLS[name].objects.link(o)

def raw(o,name):
    o.name=PREFIX+name; mark(o); mark(o.data)
    SOLIDS.pop(o.name,None)
    return o

def mesh(name,verts,faces):
    me=mark(bpy.data.meshes.new(PREFIX+name)); me.from_pydata(verts,[],faces); me.update()
    o=mark(bpy.data.objects.new(PREFIX+name,me)); bpy.context.scene.collection.objects.link(o)
    SOLIDS.pop(o.name,None)
    return o

def active(o):
    bpy.ops.object.select_all(action='DESELECT'); o.hide_set(False); o.select_set(True)
    bpy.context.view_layer.objects.active=o

def apply(o,mod):
    active(o); bpy.ops.object.modifier_apply(modifier=mod.name)

def box(name,loc,dim,bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    o=raw(bpy.context.object,name); o.dimensions=dim
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:
        m=o.modifiers.new('Small edge relief','BEVEL'); m.width=bevel; m.segments=2; apply(o,m)
    return o

def sphere(name,loc,r):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=P['mesh']['sphere_segments'],ring_count=P['mesh']['sphere_rings'],radius=r,location=loc)
    o=raw(bpy.context.object,name)
    return o

def cyl(name,loc,r,depth,axis='Z',n=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=n or P['mesh']['cylinder_segments'],radius=r,depth=depth,location=loc)
    o=raw(bpy.context.object,name)
    if axis=='X': o.rotation_euler[1]=math.pi/2
    elif axis=='Y': o.rotation_euler[0]=math.pi/2
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    return o

def boolean(o,c,op='DIFFERENCE'):
    # Robust triangle solid kernel, still authored/executed through local Blender + bpy.
    # Keep the double-precision construction solid between Boolean steps; Blender vertices are float32.
    bpy.context.view_layer.update()
    def solid(obj):
        if obj.name in SOLIDS: return SOLIDS[obj.name]
        obj.data.calc_loop_triangles()
        v=np.array([tuple(obj.matrix_world@p.co) for p in obj.data.vertices],dtype=np.float64)
        f=np.array([tuple(t.vertices) for t in obj.data.loop_triangles],dtype=np.uint64)
        m=manifold.Manifold(manifold.Mesh64(v,f))
        if m.status()!=manifold.Error.NoError: raise RuntimeError(f'{obj.name}: {m.status()}')
        return m
    a=solid(o); b=solid(c)
    result=({'DIFFERENCE':lambda:a-b,'UNION':lambda:a+b,'INTERSECT':lambda:a^b}[op]()).simplify(P['mesh']['boolean_simplify_tolerance_mm'])
    if result.status()!=manifold.Error.NoError: raise RuntimeError(f'{o.name}: Boolean {op} failed {result.status()}')
    data=result.to_mesh64(); inv=o.matrix_world.inverted()
    old=o.data; me=mark(bpy.data.meshes.new(PREFIX+'solid_mesh'))
    me.from_pydata([tuple(inv@Vector(p[:3])) for p in data.vert_properties],[],data.tri_verts.tolist()); me.update(); o.data=me
    if old.users==0 and old.get('mori_owner')==OWNER: bpy.data.meshes.remove(old)
    SOLIDS[o.name]=result; SOLIDS.pop(c.name,None); bpy.data.objects.remove(c,do_unlink=True)
    return o

def clean(o):
    if o.get('preserve_vendor_tessellation'):
        return
    bm=bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=P['mesh']['weld_tolerance_mm'])
    bmesh.ops.dissolve_degenerate(bm,dist=P['mesh']['weld_tolerance_mm'],edges=list(bm.edges))
    bm.to_mesh(o.data); bm.free(); o.data.update()

def union(o,c): return boolean(o,c,'UNION')
def intersect(o,c): return boolean(o,c,'INTERSECT')

def ring(name,loc,ro,ri,depth,axis='Z',n=None):
    n=n or P['mesh']['cylinder_segments']; verts=[]; faces=[]
    for z,r in [(-depth/2,ro),(depth/2,ro),(-depth/2,ri),(depth/2,ri)]:
        for k in range(n):
            a=2*math.pi*k/n; u=r*math.cos(a); v=r*math.sin(a)
            p=(u,v,z) if axis=='Z' else ((z,u,v) if axis=='X' else (u,z,v))
            verts.append(tuple(p[i]+loc[i] for i in range(3)))
    for k in range(n):
        j=(k+1)%n
        faces += [(k,j,n+j,n+k),(2*n+k,3*n+k,3*n+j,2*n+j),
                  (k,2*n+k,2*n+j,j),(n+k,n+j,3*n+j,3*n+k)]
    o=mesh(name,verts,faces); recalc(o); return o

def recalc(o):
    bm=bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(o.data); bm.free(); o.data.update()

def clone(o,name):
    c=o.copy(); c.data=o.data.copy(); c.name=PREFIX+name; mark(c); mark(c.data)
    bpy.context.scene.collection.objects.link(c)
    if o.name in SOLIDS: SOLIDS[c.name]=SOLIDS[o.name]
    return c

def clip_z(o,low=-500,high=500): return intersect(o,box('cut_z',(0,0,(low+high)/2),(1000,1000,high-low)))
def clip_y(o,low=-500,high=500): return intersect(o,box('cut_y',(0,(low+high)/2,150),(1000,high-low,1000)))

def finish(o,category,label,mat='shell',group='body',candidate=False,explode=(0,0,0),note='',role='part'):
    move_collection(o,category); o.data.materials.clear(); o.data.materials.append(MATS[mat])
    o['category']=category if category not in ['COUPONS','DOCK'] else 'PRINTABLE'; o['label_zh']=label
    o['data_status']='ASSUMED'; o['stage']='M1/M2_PRESTUDY'; o['verification_status']='UNVALIDATED' ; o['group']=group; o['export_candidate']=bool(candidate); o['interface_status']=note or 'PROVISIONAL / parameterized study'
    o['role']=role; o['explode_offset_mm']=list(explode)
    o['material_suggestion']={'shell':'PLA/PETG prototype; material and loads unqualified','frame':'PETG/PA candidate; load validation required','tire':'Purchased rubber or flexible TPU; NOT rigid shell material','metal':'Metal hardware placeholder','pcb':'FR4 envelope, connectors included separately','battery':'Unselected battery pack','dark':'Black reference / printed bezel','glass':'Clear protector reference','eye':'Simulated display pixels','belt':'Flexible purchased transmission','copper':'Unselected electrical / wire','coupon':'Same material and printer as mating parts'}.get(mat,mat)
    if o.type=='MESH':
        # Do not independently reorient a cavity's disconnected surface component.
        # Boolean result winding already describes the solid and its cavities.
        clean(o)
        active(o)
        try: bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))
        except: 
            for face in o.data.polygons: face.use_smooth=False
    return o

def empty(name,loc):
    o=mark(bpy.data.objects.new(PREFIX+name,None)); COLS['CONTROLS'].objects.link(o); o.location=loc
    o.empty_display_type='PLAIN_AXES'; o.empty_display_size=12; return o

def set_origin(o,loc):
    # Bake world geometry and rebase origin without moving a vertex.
    mw=o.matrix_world.copy(); inv=Matrix.Translation(Vector(loc)).inverted()
    o.data.transform(inv@mw); o.matrix_world=Matrix.Translation(Vector(loc))

def parts(include_coupons=False):
    return [o for o in bpy.context.scene.objects if o.type=='MESH' and o.get('mori_owner')==OWNER
            and o.get('role') in (['part','coupon'] if include_coupons else ['part'])]

def assembled():
    for name in ['Root','Yaw','Pitch','Wheel_L','Wheel_R']:
        o=bpy.data.objects.get(PREFIX+'CTRL_'+name)
        if o:
            o.rotation_euler=(0,0,0)
    bpy.context.view_layer.update()

def pose(yaw_deg=0,pitch_deg=0):
    bpy.data.objects[PREFIX+'CTRL_Yaw'].rotation_euler.z=math.radians(yaw_deg)
    bpy.data.objects[PREFIX+'CTRL_Pitch'].rotation_euler.x=math.radians(pitch_deg)
    bpy.context.view_layer.update()

def vertices_world(o): return [o.matrix_world@v.co for v in o.data.vertices]
def bounds(o):
    v=vertices_world(o)
    return [[min(p[i] for p in v),max(p[i] for p in v)] for i in range(3)]

def save_json(path,data):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(data,ensure_ascii=False,indent=2))

def write_bom():
    items=[]
    for o in sorted(parts(True),key=lambda o:o.name):
        bb=bounds(o)
        items.append(dict(id=o.name.removeprefix(PREFIX),name=o.get('label_zh'),quantity=1,category=o.get('category'),data_status=o.get('data_status'),
                          material=o.get('material_suggestion'),confirmation=o.get('interface_status'),
                          candidate_stl=o.get('export_candidate'),dimensions_mm=[round(b-a,3) for a,b in bb],
                          group=o.get('group'),model_fidelity=o.get('model_fidelity','DESIGN_GEOMETRY'),
                          measured_unit=bool(o.get('measured_unit',False))))
    save_json(ROOT/'reports/bom.json',items)
    with (ROOT/'reports/bom.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(items[0])); w.writeheader(); w.writerows(items)

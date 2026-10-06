"""Editable source-CAD inspection assembly and real Blender review renders.
Not a release of the still-unlaid-out S3 power PCB or finished PCB mounts.
"""
import sys,json,math,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from render import camera
from p2_component_envelopes import missing_xt30_envelopes,SOURCE_URL

OUT=ROOT/'studies/pcb_P2_fit';TAG='MORI_PCBFIT__'
fit=json.loads((OUT/'fit_results.json').read_text());inv=json.loads((OUT/'native_inventory.json').read_text())
assert hashlib.sha256((ROOT/'mori_v1_2.blend').read_bytes()).hexdigest()==inv['source_assembly_sha256']
sc=bpy.data.scenes['MORI_V1_Assembly'];bpy.context.window.scene=sc;load_collections();assembled()
for o in list(bpy.data.objects):
    if o.get('pcb_fit_owner')=='P2_FIT_STUDY_1':bpy.data.objects.remove(o,do_unlink=True)
cols={}
for n in ['MOTION_P2','IMU_P2','POWER_P2_HISTORICAL','PROPOSED_SUPPORTS','S3_CAPACITY_ONLY','ANNOTATIONS']:
    c=bpy.data.collections.new(TAG+n);sc.collection.children.link(c);cols[n]=c

def mat(n,c,metal=0):
    m=bpy.data.materials.new(TAG+n);m.diffuse_color=(*c,1);m.use_nodes=True
    bs=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
    if bs is None:bs=m.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
    out=next((n for n in m.node_tree.nodes if n.type=='OUTPUT_MATERIAL'),None)
    if out is None:out=m.node_tree.nodes.new('ShaderNodeOutputMaterial')
    m.node_tree.links.new(bs.outputs['BSDF'],out.inputs['Surface'])
    bs.inputs['Base Color'].default_value=(*c,1)
    bs.inputs['Roughness'].default_value=.5;bs.inputs['Metallic'].default_value=metal
    if n=='annotation':
        bs.inputs['Emission Color'].default_value=(*c,1);bs.inputs['Emission Strength'].default_value=1.2
    return m
mats={'pcb':mat('native_PCB',(.025,.26,.115)), 'chip':mat('library_package',(.08,.09,.1)),
      'connector':mat('library_connector',(.76,.72,.61)), 'metal':mat('metal',(.42,.47,.50),.7),
      'capacity':mat('proposed_space',(.025,.48,.67)), 'allowance':mat('unverified_allowance',(.82,.32,.06)),
      'frame':mat('proposed_frame',(.25,.33,.36)), 'wire':mat('routing_reserve',(.46,.19,.07)),
      'text':mat('annotation',(.75,.94,1)), 'xt30':mat('vendor_XT30_envelope',(.76,.40,.035))}

def obj(n,verts,faces,group,material,tr=None,status='ASSUMED'):
    me=bpy.data.meshes.new(TAG+n);me.from_pydata(verts,[],faces);me.update()
    o=bpy.data.objects.new(TAG+n,me);cols[group].objects.link(o)
    o.data.materials.append(mats[material]);o['pcb_fit_owner']='P2_FIT_STUDY_1'
    o['category']='PLACEHOLDER' if group in ['S3_CAPACITY_ONLY','PROPOSED_SUPPORTS'] else 'PURCHASED_REFERENCE'
    o['data_status']=status;o['export_candidate']=False;o['physical_measurement']=False
    if tr is not None:o.matrix_world=Matrix(tr)
    return o

def import_component(kind,c,tr):
    verts=[];faces=[]
    for s in c['solids']:
        offset=len(verts);verts+=s['vertices_mm'];faces += [[i+offset for i in f] for f in s['triangles']]
    ref=c['reference'];material='pcb' if ref=='PCB' else ('connector' if ref.startswith('J') else 'chip')
    group={'motion':'MOTION_P2','imu':'IMU_P2','power':'POWER_P2_HISTORICAL'}[kind]
    o=obj(kind+'__'+ref,verts,faces,group,material,tr)
    o['source_pcb']=inv['boards'][kind]['source'];o['source_sha256']=inv['boards'][kind]['source_sha256']
    o['native_reference']=ref;o['fabrication']='CUSTOM_PCB_ASSEMBLY'
    o['geometry_source_status']='Native PCB design and linked KiCad library model; not measured hardware'
    if kind=='power':o['historical_only']='P2; not the S3 circuit or board size'
    return o

def m4(r,t):
    m=np.eye(4);m[:3,:3]=r;m[:3,3]=t;return m

chosen=fit['maximum_sampled_rectangle'];power_z=chosen['pcb_dielectric_bottom_z_mm'];cy=chosen['center_y_mm']
placements={'motion':chosen['motion'],'imu':chosen['imu'],'power':{'center':[0,cy],'z':power_z,'angle':0}}
for kind,place in placements.items():
    data=json.loads((OUT/f'{kind}_mesh.json').read_text())
    b=next(c for c in data['components'] if c['reference']=='PCB')['bounds_xyz_mm'];w=b[0][1]-b[0][0];d=b[1][1]-b[1][0]
    r=np.array(Matrix.Rotation(math.radians(place['angle']),3,'Z'))
    tr=m4(r,np.array([*place['center'],place['z']])-r@np.array([w/2,-d/2,0]))
    for comp in data['components']:import_component(kind,comp,tr)
    if kind=='motion':
        wc=json.loads((ROOT/'sources/v1_2_detail_fit/weact_v11_mesh.json').read_text())
        rr=np.array(fit['weact_mapping']['rotation']);tt=np.array([61.016,116.078,1.595+6])
        transform=m4(r@rr,np.array([*place['center'],place['z']])+r@tt)
        for i,s in enumerate(wc['solids']):
            o=obj('WeAct__'+str(i),s['vertices_mm'],s['triangles'],'MOTION_P2','pcb' if i==0 else ('connector' if i in [159,160,161,162] else 'metal'),transform,'VENDOR_DOCUMENTED')
            o['source_step_sha256']=wc['source_sha256'];o['mating_header_gap_mm_assumed']=6

def from_manifold(n,m,group,material):
    mm=m.to_mesh64();return obj(n,mm.vert_properties[:,:3].tolist(),mm.tri_verts.tolist(),group,material)
for ref,m in missing_xt30_envelopes(inv).items():
    o=from_manifold('power__'+ref+'_VENDOR_ENVELOPE',m.translate([-40,22.5+cy,power_z]),'POWER_P2_HISTORICAL','xt30')
    o['data_status']='VENDOR_DOCUMENTED';o['representation']='Conservative dimensions; not detailed original CAD; no mated plug';o['source_url']=SOURCE_URL
def block(n,center,size,group,material):
    return from_manifold(n,manifold.Manifold.cube(size).translate((np.array(center)-np.array(size)/2).tolist()),group,material)
def rod(n,a,b,group='ANNOTATIONS',material='capacity',radius=.16):
    a=Vector(a);b=Vector(b);r=np.array((b-a).to_track_quat('Z','Y').to_matrix())
    m=manifold.Manifold.cylinder((b-a).length,radius,radius,16).transform(np.column_stack([r,np.array(a)]))
    return from_manifold(n,m,group,material)
def wire_box(n,lo,hi,group='S3_CAPACITY_ONLY'):
    corners=[(lo[0] if i&1==0 else hi[0],lo[1] if i&2==0 else hi[1],lo[2] if i&4==0 else hi[2]) for i in range(8)]
    for i,a in enumerate(corners):
        for k in [1,2,4]:
            if not i&k:rod(n+f'_{i}_{k}',a,corners[i|k],group)

proposals=json.loads((OUT/'proposed_support_meshes.json').read_text())
for n,meshdata in proposals.items():
    obj(n+'_PROPOSED',meshdata['vertices_mm'],meshdata['triangles'],'PROPOSED_SUPPORTS','frame' if n=='Load_Frame' else 'wire')

# Blue outlines are space requirements, not fictitious new S3 electronics.
wire_box('S3_80x55_RESERVE',[-40,cy-27.5,power_z-3],[40,cy+27.5,power_z+17.6])
wire_box('S3_PCB_OUTLINE',[-40,cy-27.5,power_z],[40,cy+27.5,power_z+1.6])
for ref in ['C10','C30']:
    c=next(c for c in json.loads((OUT/'power_mesh.json').read_text())['components'] if c['reference']==ref)
    b=c['bounds_xyz_mm'];x=(b[0][0]+b[0][1])/2-40;y=(b[1][0]+b[1][1])/2+22.5+cy
    cap=manifold.Manifold.cylinder(16,5,5,64).translate([x,y,power_z+1.56])
    o=from_manifold('CAP_'+ref+'_16MM_RESERVE',cap,'POWER_P2_HISTORICAL','allowance')
    o['category']='PLACEHOLDER';o['source_note']='S3 requests16mm capacitors; P2 generic KiCad model is10mm. Conservative cylinder, not supplier detailed CAD.'
    bpy.data.objects[TAG+'power__'+ref].hide_render=True
    bpy.data.objects[TAG+'power__'+ref].hide_set(True)

hide_names={'Body_Upper','Body_Lower','MCU_Motion','Body_IMU','Power_Module','Power_Board_Carrier','Load_Frame','Head_Trunk'}
base_vis={}
for o in sc.objects:
    if o.get('pcb_fit_owner'):continue
    n=o.name.removeprefix(PREFIX)
    if o.get('role') in ['part','routing','display_content']:
        hidden=n in hide_names or n.startswith('Power_Carrier_') or o.get('group') in ['yaw','pitch']
        if o.type=='MESH' and bounds(o)[2][0]>161:hidden=True
        o.hide_render=hidden;o.hide_set(hidden);base_vis[o.name]=hidden
for n in ['DATUMS','KEEP_OUT','COUPONS','DOCK','ANNOTATIONS']:
    COLS[n].hide_render=True;COLS[n].hide_viewport=True
ground=bpy.data.objects.get(PREFIX+'Studio_Ground')
if ground:ground.hide_render=True
sc.render.engine='CYCLES';sc.cycles.samples=32;sc.cycles.use_denoising=True
sc.render.resolution_x=1300;sc.render.resolution_y=1050;sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG';sc.render.film_transparent=False
sc.world.color=(.12,.12,.12)

def label(n,text,loc,size,cam):
    cu=bpy.data.curves.new(TAG+n,'FONT');cu.body=text;cu.size=size;cu.align_x='CENTER'
    o=bpy.data.objects.new(TAG+n,cu);cols['ANNOTATIONS'].objects.link(o);o.location=loc
    o.rotation_euler=cam.rotation_euler.copy();o.data.materials.append(mats['text']);o['pcb_fit_owner']='P2_FIT_STUDY_1'
    o.location+=cam.rotation_euler.to_quaternion()@Vector((0,0,300))
    return o
def clear_labels():
    for o in list(cols['ANNOTATIONS'].objects):bpy.data.objects.remove(o,do_unlink=True)

cam=camera('PCB_fit_angled',(230,290,260),(0,-8,119),186)
sc.render.filepath=str(OUT/'pcb_fit_assembly.png');bpy.ops.render.render(write_still=True)
clear_labels()

# Plan view hides only the upper bridge to expose the boards; it remains in
# the editable file and all solid checks. Battery/wheels hidden for clarity.
for o in sc.objects:
    if o.get('pcb_fit_owner'):continue
    n=o.name.removeprefix(PREFIX)
    if o.get('role') in ['part','routing','display_content']:
        if n in ['Yaw_Base','Yaw_Reaction_Link','Yaw_Bearing','Yaw_Horn','Yaw_Lock_Screw'] or (o.type=='MESH' and bounds(o)[2][1]<111):o.hide_render=True
sc.render.resolution_y=1300
cam=camera('PCB_fit_plan',(0,0,650),(0,0,120),202)
for x in [-40,40]:rod('width_extension',(x,cy+28,170),(x,74,170))
rod('width_dimension',(-40,74,170),(40,74,170))
label('width','80 mm',(0,76,170),4.5,cam)
for y in [cy-27.5,cy+27.5]:rod('depth_extension',(40,y,170),(66,y,170))
rod('depth_dimension',(63,cy-27.5,170),(63,cy+27.5,170))
label('depth','55 mm',(72,cy,170),4.2,cam)
label('title','POWER PCB DESIGN LIMIT',(0,92,170),4.5,cam)
label('subtitle','80 x 55 x 1.6 mm | COMPONENTS: +16 / -3 mm',(0,85,170),3.2,cam)
label('motion','P2 CARRIER 70 x 35 | REARWARD 7 mm',(0,-82,170),3.4,cam)
label('limit','P2 POWER SHOWN: 80 x 45 | BLUE: PROPOSED S3 SPACE',(0,-90,170),2.8,cam)
sc.render.filepath=str(OUT/'power_capacity_plan.png');bpy.ops.render.render(write_still=True)

# Save this inspection view. Hidden objects are accessible in the Outliner;
# custom boards remain independent native-reference component meshes.
sc['study_status']='P2 native CAD fit audit; 80x55 S3 capacity PROPOSED; mounts/headers/plug routing NOT_RELEASED'
sc['power_P2_is_historical']=True;sc['released_model_unchanged']=True
sc['source_assembly_sha256']=inv['source_assembly_sha256'];sc['fit_results']='fit_results.json'
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.overlay.show_extras=False
            area.spaces.active.region_3d.view_location=(0,-5,125)
            area.spaces.active.region_3d.view_distance=200
            area.spaces.active.region_3d.view_rotation=cam.rotation_euler.to_quaternion()
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'MORI_P2_PCB_FIT_STUDY.blend'))
files=['MORI_P2_PCB_FIT_STUDY.blend','pcb_fit_assembly.png','power_capacity_plan.png']
save_json(OUT/'render_provenance.json',{'blender_version':bpy.app.version_string,'actual_model_renders':True,
          'source_model_sha256':inv['source_assembly_sha256'],
          'source_model_unchanged':hashlib.sha256((ROOT/'mori_v1_2.blend').read_bytes()).hexdigest()==inv['source_assembly_sha256'],
          'sha256':{n:hashlib.sha256((OUT/n).read_bytes()).hexdigest() for n in files}})
print('P2_FIT_RENDER_COMPLETE',flush=True)

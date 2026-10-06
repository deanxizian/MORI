"""Run in Blender background. Make a separate fit-review .blend and trial STLs.

Reads root CAD/parameters without modifying them. Catalog envelopes are not
manufacturer product meshes. Collision volumes are geometric checks only.
"""
from pathlib import Path
import sys, json, hashlib, math, struct
import bpy, bmesh
from mathutils import Vector, Quaternion

R=Path(__file__).resolve().parents[1]
ROOT=R.parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import common as c
P=c.P; D=c.D
OUT=R/'mechanical'; OUT.mkdir(exist_ok=True)
sources=[ROOT/'params.json',ROOT/'reports/derived.json',ROOT/'models/MORI_assembly.blend']
before={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/MORI_assembly.blend'))
scene=bpy.context.scene;scene.frame_set(1)
collection=bpy.data.collections.new('HW_A05_FIT_REVIEW');scene.collection.children.link(collection)
trialcol=bpy.data.collections.new('HW_A05_TRIAL_PRINTS');scene.collection.children.link(trialcol)
materials={}
for name,color in [('candidate',(0.1,.65,.85,1)),('conflict',(.9,.21,.14,1)),('trial',(.95,.66,.15,1))]:
    m=bpy.data.materials.new('HW_A05_'+name);m.diffuse_color=color;materials[name]=m

def add(obj,kind='candidate',note='',trial=False):
    for col in list(obj.users_collection):col.objects.unlink(obj)
    (trialcol if trial else collection).objects.link(obj)
    obj['mori_owner']='mori_hw_A05';obj['status']='NOT_TESTED';obj['basis']=note
    obj.data.materials.clear();obj.data.materials.append(materials[kind]);obj.color=materials[kind].diffuse_color
    return obj

retired=['Controller_PLACEHOLDER','Imu_PLACEHOLDER','Battery_PLACEHOLDER','Head_Servo_PLACEHOLDER',
         'Battery_Tray','Controller_Mount','Imu_Mount','Driver_Mount']
for obj in scene.objects:
    if obj.name.removeprefix('MORI__') in retired:
        obj.hide_set(True);obj.hide_render=True
    if any(s in obj.name for s in ['Body_Upper','Body_Lower','Head_Front','Head_Rear']):
        obj.display_type='WIRE';obj.hide_render=True

items=[]
def candidate(name,center,dims,note,kind='candidate'):
    obj=add(c.box('HW_A05_'+name,center,dims),kind,note)
    items.append((name,obj,center,dims,note));return obj

candidate('ANSMANN2447_0105',[0,0,P['battery']['center_z_mm']],[39,71,18],
          'Catalog candidate, dimension table inconsistent; battery purchase and charge HOLD.')
candidate('DevKitC1_full_keepout',[0,-25,123],[71,28,18],
          '71x28 planar allocation derived conservatively from official DXF; 18 high is an unmeasured allowance. Head-support interference expected.','conflict')
candidate('LSM6DSOX_original_location',P['electronics']['imu_center_mm'],[25.6,17.8,4.6],
          'Product maximum envelope at original IMU center; original bracket is incompatible.','conflict')
imu=candidate('LSM6DSOX_proposed_location',[0,30,120.7],[25.6,17.8,4.6],
          'Alternative module-first location only; requires new rigid mount and measured sensor-axis matrix.')
candidate('SER0037_body',P['head_joint']['servo_center_mm'],[22.9,12.3,22.6],
          'Body only; mounting ears, spline and cable are NOT included, so no assembled-fit claim.')
add(c.ring('HW_A05_6805ZZ_candidate',(0,0,D['bearing_z']-.5),18.5,12.5,7),
    'conflict','25x37x7 candidate replaces 24x36x6. Lower center by0.5 preserves top face; seat/spindle not revised.')

# Revision-only battery tray. Keep root X cavity, floor elevation and hanger
# centers; lengthen internal Y to73.0. 39x71x18 pack has0.8/1.0mm side gaps.
ba=P['battery'];s=P['structure'];det=P['details_mm']['battery']
ix=ba['envelope_mm'][0]+2*P['assembly_clearance_per_side_mm'];iy=73.0
wall=ba['tray_wall_mm'];floor=ba['tray_floor_mm'];h=ba['tray_wall_height_mm']
top=ba['center_z_mm']-ba['envelope_mm'][2]/2-P['assembly_clearance_per_side_mm']
tray=c.box('HW_A05_Battery_Tray_TRIAL',(0,0,top-floor/2),(ix+2*wall,iy+2*wall,floor))
for sign in [-1,1]:
    c.union(tray,c.box('hw_tray_side',(sign*(ix/2+wall/2),0,top+h/2),(wall,iy+2*wall,h+.1)))
    c.union(tray,c.box('hw_tray_end',(0,sign*(iy/2+wall/2),top+h/2),(ix,wall,h+.1)))
for x,y in s['battery_hanger_xy_mm']:
    c.union(tray,c.box('hw_tab',(x,y,top-floor/2),(*det['slot_tab_size_xy'],floor)))
    cut=c.box('hw_slot',(x,y,top),(det['slot_diameter'],2*ba['adjust_y_limit_mm'],12))
    for sign in [-1,1]:c.union(cut,c.cyl('hw_slot_end',(x,y+sign*ba['adjust_y_limit_mm'],top),det['slot_diameter']/2,12))
    c.boolean(tray,cut)
for sign in [-1,1]:
    c.boolean(tray,c.box('hw_strap_slot',(sign*(ix/2+wall/2),0,top+1),(wall+1,ba['strap_width_mm']+.6,12)))
add(tray,'trial','TRIAL ONLY: internal40.6x73.0; pad thickness1.3 to retain battery centerZ63. Not structural/thermal/pack validation.',True)

# A dedicated IMU hole-pattern coupon, NOT an approved installation bracket.
gauge=c.box('HW_A05_IMU_20p32_hole_gauge',(0,30,115.2),(30,22,2.4))
for x in [-10.16,10.16]:
    c.boolean(gauge,c.cyl('imu_gauge_hole',(x,36.35,115.2),1.35,6))
add(gauge,'trial','Hole-pattern coupon:2x2.7 through,20.32 pitch,y+6.35 from center. Board itself has2.5 plated holes. No deck fixing designed.',True)

def solid(obj):
    obj.data.calc_loop_triangles()
    verts=c.np.asarray([tuple(obj.matrix_world@v.co) for v in obj.data.vertices],dtype=c.np.float64)
    faces=c.np.asarray([tuple(t.vertices) for t in obj.data.loop_triangles],dtype=c.np.uint64)
    result=c.manifold.Manifold(c.manifold.Mesh64(verts,faces))
    assert result.status()==c.manifold.Error.NoError,(obj.name,str(result.status()))
    return result

frame=bpy.data.objects.get('MORI__Load_Frame');assert frame
bpy.context.view_layer.update();frame_s=solid(frame)
report={'mechanical_source_sha256':before,'unit':'mm','physical_tests':'NOT_TESTED',
        'method':'Exact triangle-solid intersection with existing Load_Frame; conservative box-corner inner-sphere test. Not a full assembly/wire sweep.',
        'candidate_checks':[],'print_trials':[]}
inner=P['body_diameter_mm']/2-P['shell_thickness_mm']
for name,obj,center,dims,note in items:
    pts=[Vector(center)+Vector((sx*dims[0]/2,sy*dims[1]/2,sz*dims[2]/2)) for sx in [-1,1] for sy in [-1,1] for sz in [-1,1]]
    sphere_margin=min(inner-(v-Vector((0,0,D['body_z']))).length for v in pts)
    overlap=float((solid(obj)^frame_s).volume())
    report['candidate_checks'].append({'name':name,'center_mm':center,'envelope_mm':dims,'basis':note,
        'inner_sphere_corner_margin_mm':sphere_margin,'load_frame_overlap_mm3':overlap,
        'geometric_status':'FAIL' if overlap>.001 or sphere_margin<0 else 'PASS',
        'geometric_status_scope':'Only these two geometric checks; installed fit is NOT_TESTED'})
report['tray_load_frame_overlap_mm3']=float((solid(tray)^frame_s).volume())
report['tray_pack_intersection_mm3']=float((solid(tray)^solid(items[0][1])).volume())

def export_trial(obj,filename):
    obj.data.calc_loop_triangles();verts=[obj.matrix_world@v.co for v in obj.data.vertices]
    low=Vector(tuple(min(v[j] for v in verts) for j in range(3)))
    high=Vector(tuple(max(v[j] for v in verts) for j in range(3)))
    offset=Vector(((low.x+high.x)/2,(low.y+high.y)/2,low.z))
    data=bytearray(b'MORI A0.5 TRIAL / mm / NOT ASSEMBLY-VALIDATED'.ljust(80,b' '))
    data.extend(struct.pack('<I',len(obj.data.loop_triangles)))
    for tri in obj.data.loop_triangles:
        a,b,d=[verts[i]-offset for i in tri.vertices];normal=(b-a).cross(d-a).normalized()
        data.extend(struct.pack('<12fH',*normal,*a,*b,*d,0))
    path=OUT/filename;path.write_bytes(data)
    m=solid(obj);components=len(m.decompose())
    assert components==1,(obj.name,components)
    report['print_trials'].append({'file':filename,'size_mm':list(high-low),
        'assembly_to_stl_translation_mm':list(-offset),'volume_mm3':float(m.volume()),
        'closed_manifold_status':'PASS','connected_components':components,
        'print_and_fit_test':'NOT_TESTED','sha256':hashlib.sha256(data).hexdigest()})
export_trial(tray,'Battery_Tray_A05_TRIAL.stl')
export_trial(gauge,'IMU_20p32_Hole_Gauge.stl')

# The target keeps 1mm roof allowance but assumes an unverified 10mm stack.
report['mcu_low_profile_alternative']={'center_mm':[0,-31,119],'envelope_mm':[71,28,10],
    'status':'NOT_TESTED','note':'Target only, not an actual DevKit measurement. Relieves head posts; pin/header/cable and antenna clearance remain unconfirmed. Do not cut pins or order from this target.'}
report['bearing_proposal']={'old_center_z':D['bearing_z'],'new_center_z':D['bearing_z']-.5,
    'old_top_z':D['bearing_z']+3,'new_top_z':D['bearing_z']-.5+3.5,
    'new_bottom_z':D['bearing_z']-.5-3.5,'status':'NOT_TESTED','note':'Seat/spindle/retention need redesign; model is only bearing-envelope overlay.'}
report['root_sources_unchanged']=all(hashlib.sha256(p.read_bytes()).hexdigest()==before[str(p.relative_to(ROOT))] for p in sources)
assert report['root_sources_unchanged']
(OUT/'fit_review.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
text=bpy.data.texts.new('HW_A05_README');text.write('MORI HARDWARE A0.5 FIT REVIEW\n1 unit=1mm. Original CAD read-only; this is a separate copy.\nRed=known conflict / redesign, cyan=catalog envelope, yellow=trial print.\nSee fit_review.json for exact scope and measured-vs-assumed dimensions.\nNeither DRC nor a closed STL proves installed fit or safe operation.\n')
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        area.spaces.active.shading.color_type='MATERIAL'
        area.spaces.active.region_3d.view_distance=330
        area.spaces.active.region_3d.view_location=(0,0,110)
        area.spaces.active.region_3d.view_rotation=Quaternion((.827,.437,.166,.308)).normalized()
scene['hardware_revision']='A0.5 REVIEW / NOT_TESTED'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'MORI_Hardware_Fit_A0.5.blend'))
print(json.dumps(report,ensure_ascii=False,indent=2))

"""Editable joint proposal against the current released assembly; never writes the released assembly.

Run Blender with mechanical/mori_v1_2.blend loaded and --python this file.
All trial dimensions below belong only to this explicitly unreleased study.
"""
import sys, hashlib, itertools
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from common import *
from validate import Solid, intersect_volume, rigidtr
from export import topology
from render import camera

OUT = Path(__file__).resolve().parent
SOURCE = ROOT / 'mori_v1_2.blend'
HASH = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
PROTECTED = [PROJECT/'config/geometry.json', PROJECT/'contracts/mechanical_interfaces.json',
             PROJECT/'contracts/components.json', SOURCE, ROOT/'mori_assembly_animation.blend']
BEFORE = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in PROTECTED}
bpy.context.window.scene = bpy.data.scenes['MORI_V1_Assembly']
sc = bpy.context.scene
load_collections(); assembled()
baseline = {o.name.removeprefix(PREFIX): Solid(o) for o in parts() if o.get('group') != 'dock'}
routes = {o.name.removeprefix(PREFIX): Solid(o) for o in sc.objects if o.type=='MESH' and o.get('role')=='routing'}
TRIAL = dict(bridge_outer_half_width_mm=47.1, leg_thickness_mm=6.0,
    tongue_depth_y_mm=30.0, tongue_bottom_z_mm=98.5, root_fillet_radius_mm=1.0,
    slot_clearance_per_side_mm=.2, cheek_sliding_gap_mm=.3,
    bolt_y_mm=0., bolt_z_mm=105.5, screw_length_mm=8., screw_diameter_model_mm=2.9,
    screw_clearance_diameter_mm=3.4, head_diameter_mm=5.7, head_height_mm=1.65,
    head_recess_diameter_mm=6.2, head_recess_depth_mm=1.8,
    nut_af_mm=5.5, nut_thickness_mm=2.4, nut_pocket_af_mm=5.8,
    nut_pocket_depth_mm=2.6, tool_diameter_mm=4.2, insertion_travel_mm=30.)
top = P['layout']['deck_z_mm'] + P['layout']['deck_thickness_mm']/2
bottom = top - P['layout']['deck_thickness_mm']
ss = P['structure']['simple_modules']
outer = ss['side_plate_abs_x_mm'] + ss['side_plate_thickness_mm']/2
half = TRIAL['bridge_outer_half_width_mm']; thick = TRIAL['leg_thickness_mm']
inner = half-thick; headseat = outer-TRIAL['head_recess_depth_mm']

def ownclone(n, new):
    o=clone(baseline[n].o,new)
    for k in ['validation_solid_source','validation_proxy']:
        if k in o: del o[k]
    o['verification_status']='UNRELEASED_JOINT_STUDY / STRENGTH_NOT_TESTED'
    o['export_candidate']=False
    return o

def prism(name, profile_yz, xmin, width):
    m=manifold.CrossSection([profile_yz]).extrude(width)
    m=m.transform(np.array([[0,0,1,xmin],[1,0,0,0],[0,1,0,0]],dtype=float))
    data=m.to_mesh64()
    o=mesh(name,data.vert_properties[:,:3].tolist(),data.tri_verts.tolist())
    SOLIDS[o.name]=m
    return o

base = ownclone('Yaw_Base','STUDY_Yaw_Base')
frame = ownclone('Load_Frame','STUDY_Load_Frame')
material('study_bridge',(.075,.30,.38),roughness=.46)
material('study_frame',(.72,.75,.76),roughness=.58)
material('study_hardware',(.32,.38,.44),metallic=.65,roughness=.3)
hw = {}
for sign in [-1,1]:
    # Refill the superseded underside blind insert holes before making a new joint.
    union(base,box('fill_old_bridge_pilots',(sign*45,0,118.7),(6,42,7.4)))
    rr=TRIAL['root_fillet_radius_mm']; ty=TRIAL['tongue_depth_y_mm']/2
    z0=TRIAL['tongue_bottom_z_mm']
    profile=[(-ty,z0),(ty,z0),(ty,top-rr)]
    profile += [(ty+rr+rr*math.cos(a),top-rr+rr*math.sin(a)) for a in np.linspace(math.pi,math.pi/2,13)[1:]]
    profile += [(21,top),(21,147.1),(-21,147.1),(-21,top),(-ty-rr,top)]
    profile += [(-ty-rr+rr*math.cos(a),top-rr+rr*math.sin(a)) for a in np.linspace(math.pi/2,0,13)[1:]]
    union(base,prism('lapping_bridge_leg',profile,inner if sign>0 else -half,thick))
    # Restore the old M2 clearance and counterbore in the untouched deck thickness.
    union(frame,cyl('fill_old_M2_deck_hole',(sign*45,-17,(top+bottom)/2),2.2,top-bottom))
    c=TRIAL['slot_clearance_per_side_mm']
    # The old deck/cheek joint also has an integral 3.5mm underside ledge.
    # Make the real socket through both that ledge and the deck, not a blind slot.
    slot=[(-ty-c,z0-1),(ty+c,z0-1),(ty+c,top-rr),
          (ty+c+rr,top),(ty+c+rr,top+1),(-ty-c-rr,top+1),
          (-ty-c-rr,top),(-ty-c,top-rr)]
    boolean(frame,prism('tongue_socket',slot,inner-c if sign>0 else -half-c,thick+2*c))
    y,z=TRIAL['bolt_y_mm'],TRIAL['bolt_z_mm']
    for o in [base,frame]:
        boolean(o,cyl('cross_M3_clear',(sign*45,y,z),TRIAL['screw_clearance_diameter_mm']/2,20,'X'))
    # Nut pocket opens on the inside; its outer bearing face stays inside the leg.
    nut_seat=inner+TRIAL['nut_pocket_depth_mm']
    boolean(base,cyl('captive_hex_pocket',(sign*(inner+(TRIAL['nut_pocket_depth_mm']-.1)/2),y,z),
        TRIAL['nut_pocket_af_mm']/math.sqrt(3),TRIAL['nut_pocket_depth_mm']+.1,'X',6))
    boolean(frame,cyl('flush_button_head_seat',(sign*((headseat+outer+.2)/2),y,z),
        TRIAL['head_recess_diameter_mm']/2,outer+.2-headseat,'X'))
    n=cyl('STUDY_Nut_'+str(sign),(sign*(nut_seat-TRIAL['nut_thickness_mm']/2),y,z),
        TRIAL['nut_af_mm']/math.sqrt(3),TRIAL['nut_thickness_mm'],'X',6)
    boolean(n,cyl('model_thread_bore',(sign*(nut_seat-TRIAL['nut_thickness_mm']/2),y,z),1.52,4,'X'))
    b=cyl('STUDY_Bolt_'+str(sign),(sign*(headseat-TRIAL['screw_length_mm']/2),y,z),
        TRIAL['screw_diameter_model_mm']/2,TRIAL['screw_length_mm'],'X')
    union(b,cyl('button_head_envelope',(sign*(headseat+TRIAL['head_height_mm']/2),y,z),
        TRIAL['head_diameter_mm']/2,TRIAL['head_height_mm'],'X'))
    boolean(b,cyl('hex_drive_illustration',(sign*(headseat+1.45),y,z),2/math.sqrt(3),.6,'X',6))
    for ob,label in [(n,'M3金属六角螺母 / 标准外形参考'),(b,'M3×8低圆头螺钉 / 保守圆柱头包络')]:
        finish(ob,'PURCHASED_REFERENCE',label,'study_hardware',candidate=False)
        ob['model_fidelity']='Nominal interface envelope; smooth threads, cylindrical button-head envelope, no certified tolerance stack'
        hw[ob.name.removeprefix(PREFIX)]=ob

# Keep one constant-width open U bridge, with no projecting ears or external grooves.
intersect(base,box('straight_bridge_outer_faces',(0,0,140),(2*half,200,150)))
clean(base);clean(frame)
for o,key,label in [(base,'study_bridge','插接承重桥 / 候选'),(frame,'study_frame','带插槽主框架 / 候选')]:
    o.data.materials.clear();o.data.materials.append(MATS[key]);o['label_zh']=label
    o['role']='part';o['category']='PRINTABLE';o['data_status']='ASSUMED'
    o['group']='body';o['export_candidate']=False
bpy.context.view_layer.update()
changed={'Yaw_Base':Solid(base),'Load_Frame':Solid(frame),**{n:Solid(o) for n,o in hw.items()}}
retired={n for n in baseline if n.startswith('Yaw_Base_')}
allsolids={n:a for n,a in baseline.items() if n not in retired}
allsolids.update(changed)

def collisions(movers,obstacles,tol=.01):
    hits=[]
    for n,a in movers.items():
        for k,b in obstacles.items():
            if a.o==b.o:continue
            v=intersect_volume(a,b)
            if v>tol:hits.append(dict(a=n,b=k,overlap_mm3=round(v,5)))
    return hits

static=collisions(changed,allsolids)
wire=collisions(changed,routes,.1)
withdraw=[]
# Fit of the bridge by itself, before fitting the head and fixed torque link.
# The source's head-bearing interfaces are not treated as arbitrary collisions.
body_obstacles={n:a for n,a in allsolids.items() if a.group=='body'
    and n not in changed and not n.startswith('Yaw_') and n not in ['Body_Upper','Body_Lower']}
body_obstacles['Load_Frame']=changed['Load_Frame']
for d in range(31):
    mover=Solid(base,changed['Yaw_Base'],Matrix.Translation((0,0,d)))
    for h in collisions({'Yaw_Base':mover},body_obstacles):withdraw.append(dict(distance_mm=d,**h))
removed={'Body_Upper','Body_Lower'}
# Only detach the tyres/hubs and their two end retainers; motor outputs, shafts,
# output bolts and spacers remain obstacles throughout the access check.
wheel_names={n for n in allsolids if n.startswith(('Tire_','Wheel_Hub_','Wheel_End_Screw_','Wheel_End_Washer_'))}
removed|=wheel_names
insertion=[];toolhits=[];wheel_access=[]
for sign in [-1,1]:
    name='STUDY_Bolt_'+str(sign);a=changed[name]
    obstacles={n:s for n,s in allsolids.items() if n not in removed and n!=name}
    for d in range(31):
        mover=Solid(a.o,a,Matrix.Translation((sign*d,0,0)))
        for h in collisions({name:mover},obstacles):insertion.append(dict(side=sign,distance_mm=d,**h))
    t=cyl('driver_test',(sign*(headseat+16),TRIAL['bolt_y_mm'],TRIAL['bolt_z_mm']),TRIAL['tool_diameter_mm']/2,30,'X')
    ts=Solid(t)
    toolhits+=collisions({'tool_'+str(sign):ts},{n:s for n,s in obstacles.items() if not n.startswith('STUDY_Bolt_')})
    wheel_access+=collisions({'tool_'+str(sign):ts},{n:s for n,s in allsolids.items() if n in wheel_names})
    bpy.data.objects.remove(t,do_unlink=True)
nut_insert=[]
for sign in [-1,1]:
    n='STUDY_Nut_'+str(sign);a=changed[n]
    for d in range(7):
        mover=Solid(a.o,a,Matrix.Translation((-sign*d,0,0)))
        nut_insert+=collisions({n:mover},{'bridge':changed['Yaw_Base']})
motion=[]
ys=list(range(-60,61,15));ps=list(range(-20,26,5))
for yaw,pitch in itertools.product(ys,ps):
    moving={n:Solid(a.o,a,rigidtr(yaw,pitch if a.group=='pitch' else 0))
            for n,a in baseline.items() if a.group in ['yaw','pitch']}
    for h in collisions(changed,moving):motion.append(dict(yaw_deg=yaw,pitch_deg=pitch,**h))

topologies={}
for n,a in changed.items():
    t=topology(a.v.tolist(),a.f.tolist());t['positive_solid_components']=sum(m.volume()>1e-6 for m in a.m.decompose())
    topologies[n]=t
# Confirm real shoulder bearing by probing both mating solids, not only AABBs.
bear=[]
for sign in [-1,1]:
    for y in [-19,19]:
        x=sign*(half-thick/2)
        foot=changed['Yaw_Base'].m.ray_cast([x,y,110],[x,y,120])
        seat=changed['Load_Frame'].m.ray_cast([x,y,120],[x,y,110])
        bear.append(dict(x_mm=x,y_mm=y,foot_z_mm=float(foot[0].position[2]) if foot else None,
                         deck_z_mm=float(seat[0].position[2]) if seat else None))
gaps={n:round(changed['Yaw_Base'].m.min_gap(baseline[n].m,30),3)
      for n in ['Battery','Battery_Tray','Power_Module','MCU_Carrier','Body_IMU'] if n in baseline}
mass=json.loads((ROOT/'reports/mass_budget.json').read_text())
load_parts=[r for r in mass['density_and_component_mass_assumptions'] if r['group'] in ['yaw','pitch']
            or (r['id'].startswith('Yaw_') and r['id'] not in retired)]
mg=sum(r['mass_g'] for r in load_parts)
com=sum(np.array(r['com_mm'])*r['mass_g'] for r in load_parts)/mg
lever=(com[2]-top)/1000
scenarios=[dict(horizontal_acceleration_g=a,assumed_mass_multiplier=q,
    lateral_force_N=round(mg/1000*q*9.80665*a,2),overturning_moment_at_deck_Nm=round(mg/1000*q*9.80665*a*lever,2))
    for a,q in [(1,1),(3,1),(3,1.35)]]
good=not any([static,wire,withdraw,insertion,toolhits,nut_insert,motion]) and all(
    t['nonmanifold_edges']==t['inconsistent_edges']==t['degenerate_triangles']==0 and t['positive_solid_components']==1
    for t in topologies.values()) and all(r['foot_z_mm'] is not None and abs(r['foot_z_mm']-r['deck_z_mm'])<.01 for r in bear)
report=dict(status='PASS_LOCAL_GEOMETRY_ONLY' if good else 'FAIL',source_revision=P['revision'],
    source_blend=str(SOURCE),source_sha256=HASH,blender=bpy.app.version_string,
    timestamp_utc=datetime.now(timezone.utc).isoformat(),study_parameters=TRIAL,
    old_joint=dict(screws='2 × M2×8 into unselected trial heat-set inserts',
        same_rear_y_line_mm=-17,insert_pilot_diameter_mm=3.4,minimum_nominal_plastic_side_wall_mm=1.3,
        deck_remaining_above_head_pocket_mm=2.1,positive_shear_key=False,strength_status='NOT_TESTED'),
    proposal=dict(parts_added=0,robot_print_parts=15,fasteners='2 × M3×8 + 2 × M3 metal hex nuts replace 2 × M2 + 2 inserts',
        tongue_total_depth_below_deck_top_mm=top-TRIAL['tongue_bottom_z_mm'],
        overlap_below_deck_bottom_mm=bottom-TRIAL['tongue_bottom_z_mm'],
        head_recess_margin_mm=TRIAL['head_recess_depth_mm']-TRIAL['head_height_mm'],
        screw_thread_envelope_overlap_with_nut_mm=2.4,
        residual_cheek_under_head_mm=ss['side_plate_thickness_mm']-TRIAL['head_recess_depth_mm'],
        nut_pocket_backing_in_leg_mm=thick-TRIAL['nut_pocket_depth_mm'],
        lower_nut_pocket_edge_ligament_mm=TRIAL['bolt_z_mm']-TRIAL['nut_pocket_af_mm']/math.sqrt(3)-TRIAL['tongue_bottom_z_mm'],
        assembly='Seat nuts on bench; lower bridge into deck sockets; remove upper/lower body shell and wheels for side screws; battery/tray can remain. Fit head after securing bridge.',
        fit_clearances='Trial 0.2mm/socket side and 0.3mm cheek gap; require coupons and a clamped fit check. Nut is manually held during first screw engagement, not snap-retained.',
        printability='No slicer run. Compare bridge on a planar Y end against roof-down; check layer direction at tongues, socket support, bearing roundness and heat creep.'),
    changed_static_intersections=static,routing_intersections=wire,bridge_insertion_0_to_30_mm_each_1_mm=withdraw,
    side_screw_insertion_0_to_30_mm_each_1_mm=insertion,driver_diameter_4_2_mm_hits=toolhits,
    wheel_blocks_driver_before_removal=wheel_access,removed_for_side_access=sorted(removed),
    nut_bench_insertion_each_1_mm=nut_insert,combined_motion=dict(yaw_deg=ys,pitch_deg=ps,failures=motion),
    shoulder_contacts=bear,bridge_to_components_minimum_gap_mm=gaps,topology=topologies,
    illustrative_loads=dict(estimated_supported_mass_g=round(mg/5)*5,estimated_com_z_mm=round(float(com[2])),
        approximate_lever_arm_above_deck_mm=round(lever*1000),included_parts=[r['id'] for r in load_parts],
        cases=scenarios,not_a_design_load='1g/3g are illustrative horizontal acceleration assumptions, not a measured impact profile, safety factor or proof load. Static upright weight compresses the feet; it does not simply pull both inserts out.'),
    strength='NOT_TESTED',fatigue='NOT_TESTED',creep='NOT_TESTED',independent_exact_self_intersection='NOT_TESTED',
    global_wall_thickness='NOT_TESTED',print_fit='NOT_TESTED',complete_real_electronics_fit='BLOCKED by existing P4/P5 populated board and connector unknowns',
    method='Blender-generated closed triangle solids; Manifold intersection including containment. Finite 1mm translation samples and 90 joint poses are not a continuous collision proof. Existing vendor proxies are preserved and not promoted to exact CAD.',
    engineering_sources=[dict(url='https://www.spirol.com/resources/white-papers/how-to-design-the-proper-hole-for-heat-ultrasonic-inserts/',
        relevance='Supplier explains dependency on surrounding plastic, installed hole and proper insertion. This is general guidance, not a pull-out rating for these FDM parts.'),
        dict(url='https://www.westfieldfasteners.co.uk/Bolts-Screws-Metric/Socket-Head-Button-Dome-Screw-M3x8-A4-Stainless.html',relevance='Nominal M3×8 button head 5.7mm diameter, 1.65mm maximum head height; cylindrical envelope used here.'),
        dict(url='https://kvt.partcommunity.com/3d-cad-models/bn-115-hex-nuts-0-8d-din-934-iso-4032-cl-8-plain-bossard-catalog?info=bossard%2F01%2F01_100%2F01_100_200%2F01_100_200_10%2Fbn_115_116_117_20237_20539_20540_118_82415_119%2Fbn_115.prj',relevance='Bossard BN115 M3 nominal nut 5.5mm AF ×2.4mm thick; unchamfered conservative hex envelope.' )])
save_json(OUT/'fit_report.json',report)
print('LOCAL_REVIEW',report['status'],'failures',len(static),len(wire),len(withdraw),len(insertion),len(toolhits),len(nut_insert),len(motion),flush=True)
if not good:
    print('FAIL_DETAILS',json.dumps({k:report[k] for k in ['changed_static_intersections','routing_intersections','bridge_insertion_0_to_30_mm_each_1_mm','side_screw_insertion_0_to_30_mm_each_1_mm','driver_diameter_4_2_mm_hits','nut_bench_insertion_each_1_mm']})[:14000],flush=True)

# Original objects remain as hidden baseline references in the study file only.
for n in ['Yaw_Base','Load_Frame',*retired]:
    o=baseline[n].o;o.hide_render=True;o.hide_set(True);o['role']='study_baseline';o['export_candidate']=False
show={base.name,frame.name,*[o.name for o in hw.values()]}
for o in sc.objects:
    if o.type=='MESH':o.hide_render=o.name not in show;o.hide_set(o.hide_render)
for n in ['DATUMS','KEEP_OUT','COUPONS','DOCK','ANNOTATIONS']:
    COLS[n].hide_render=True;COLS[n].hide_viewport=True
sc['joint_study_status']='UNRELEASED PROPOSAL / STRENGTH NOT TESTED'
sc['joint_study_source_sha256']=HASH
sc['joint_study_report']=str(OUT/'fit_report.json')
sc.render.engine='CYCLES';sc.cycles.samples=24;sc.cycles.use_denoising=True
sc.render.resolution_x=1200;sc.render.resolution_y=1050;sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG'
cam=camera('joint_study',(260,360,270),(0,0,121),175)
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            sp=area.spaces.active;sp.overlay.show_extras=False
            sp.region_3d.view_location=(0,0,121);sp.region_3d.view_distance=215
bpy.ops.object.select_all(action='DESELECT');base.hide_set(False);base.select_set(True);bpy.context.view_layer.objects.active=base
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'yaw_bridge_joint_PROPOSAL.blend'))
for name,explosion in [('assembled',False),('exploded',True)]:
    if explosion:
        base.location.z+=34
        for n,o in hw.items():
            sign=-1 if n.endswith('-1') else 1
            o.location.x += sign*(22 if 'Bolt' in n else -13)
            if 'Nut' in n:o.location.z+=34
        cam=camera('joint_exploded',(260,360,305),(0,0,139),203)
    sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
    if explosion:
        base.location.z-=34
        for n,o in hw.items():
            sign=-1 if n.endswith('-1') else 1
            o.location.x -= sign*(22 if 'Bolt' in n else -13)
            if 'Nut' in n:o.location.z-=34
report['protected_files_unchanged']={str(p):hashlib.sha256(p.read_bytes()).hexdigest()==BEFORE[str(p)] for p in PROTECTED}
report['study_blend_sha256']=hashlib.sha256((OUT/'yaw_bridge_joint_PROPOSAL.blend').read_bytes()).hexdigest()
report['render_sha256']={n:hashlib.sha256((OUT/(n+'.png')).read_bytes()).hexdigest() for n in ['assembled','exploded']}
save_json(OUT/'fit_report.json',report)
print('JOINT_STUDY_COMPLETE',report['status'],flush=True)

"""T81 catalogue outer-size screening; no hub design, hardware resize or adoption."""
from pathlib import Path
import sys,json,hashlib,math,datetime
HERE=Path(__file__).resolve().parent;PROJECT_DIR=HERE.parents[3]
sys.path.insert(0,str(PROJECT_DIR/'mechanical/scripts'))
from common import *
from validate import Solid,rigidtr
from interface_completion import axial
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
main=Path(bpy.data.filepath)
before=sha(main)
assert before=='bcaa5736a8cdf43441a6a83a6cb69606546cc01d2c0d28d98f4c09383e07368f'
load_collections()
for n in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[n].hide_viewport=False
assembled();bpy.context.view_layer.update()
solids={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.get('group')!='dock'}
assert len(solids)==209
excluded=sorted([n for n in solids if n.startswith(('Tire_','Wheel_Hub_','Wheel_Axle_','Wheel_Spacer_','Wheel_End_Screw_','Wheel_End_Washer_'))])
assert len(excluded)==14,excluded
assert all(n in solids for n in ('Wheel_Cap_Clamp_Screw_0','Wheel_Cap_Clamp_Nut_0'))
# These interfaces require a different T81 centre. They are not quietly treated
# as compatible with the new wheel's unknown inner shape.
targets={n:s for n,s in solids.items() if n not in excluded}
segments=512
cases=[]
for cid,radius,width,shift in [
    ('CURRENT_OUTER_BOUND_ONLY',52.5,18.,0.),
    ('T81_KEEP_WIDTH_CENTRE',50.8,20.32,0.),
    ('T81_KEEP_INNER_PLANE',50.8,20.32,1.16)]:
    dz=radius-D['wheel_radius']
    records=[];wheels=[]
    for sign in [-1,1]:
        centre=[sign*(D['wheel_x']+shift),0,D['wheel_z']]
        wheel=axial(radius/math.cos(math.pi/segments),width,centre,[1,0,0],segments=segments)
        wheels.append(wheel)
        for name,s in targets.items():
            # Distances capped at10mm are reported as such; every target is
            # screened with the closed conservative cylinder, including containment.
            lo=np.array(centre)-np.array([width/2,radius+.002,radius+.002])
            hi=np.array(centre)+np.array([width/2,radius+.002,radius+.002])
            bboxgap=float(np.linalg.norm(np.maximum(np.maximum(s.lo-hi,lo-s.hi),0)))
            if bboxgap>10:continue
            volume=max(0.,(wheel^s.m).volume())
            gap=wheel.min_gap(s.m,10.)
            records.append(dict(side='L' if sign<0 else 'R',part=name,intersection_mm3=volume,gap_mm=gap))
    shell=[r for r in records if r['part'] in ['Body_Upper','Body_Lower']]
    nearest=min(shell,key=lambda r:r['gap_mm'])
    lower_targets={'Body_Upper','Body_Lower','Load_Frame','Drive_Bridge','Motor_Retainer','Battery_Tray'}
    local=[r for r in records if r['part'] in lower_targets]
    # Independent head movement is bounded without rotating the wheel. Circle
    # construction is conservative for any wheel angle, not37 mesh poses only.
    moving=[]
    for yaw in range(-60,61,10):
        for pitch in range(-20,26,5):
            for n,s in targets.items():
                if s.group not in ['yaw','pitch']:continue
                tr=np.array(rigidtr(yaw,pitch if s.group=='pitch' else 0))
                # Exact transformed source vertices, conservative AABB separation.
                v=s.v@tr[:3,:3].T+tr[:3,3]
                for sign in [-1,1]:
                    centre=np.array([sign*(D['wheel_x']+shift),0,D['wheel_z']])
                    ext=np.array([width/2,radius+.002,radius+.002])
                    gap=float(np.linalg.norm(np.maximum(np.maximum(v.min(axis=0)-centre-ext,centre-ext-v.max(axis=0)),0)))
                    moving.append(gap)
    lean=[]
    for deg in range(-15,16):
        # Same mechanical attachment locations, whole robot settles by dz.
        c=Vector((0,0,D['wheel_z']))
        tr=np.array(Matrix.Translation((0,0,dz))@Matrix.Translation(c)@Matrix.Rotation(math.radians(-deg),4,'X')@Matrix.Translation(-c))
        rows=[(n,float((s.v@tr[:3,:3].T+tr[:3,3])[:,2].min())) for n,s in solids.items() if not n.startswith(('Tire_','Wheel_Hub_'))]
        name,low=min(rows,key=lambda row:row[1]);lean.append(dict(lean_deg=deg,lowest_part=name,clearance_mm=low))
    cases.append(dict(id=cid,diameter_mm=2*radius,width_mm=width,outward_shift_per_side_mm=shift,
        tyre_centre_abs_x_mm=D['wheel_x']+shift,inner_face_abs_x_mm=D['wheel_x']+shift-width/2,
        tyre_outer_span_mm=2*(D['wheel_x']+shift+width/2),axle_ground_z_mm=radius,
        whole_assembly_settlement_mm=dz,belly_clearance_mm=float(solids['Body_Lower'].lo[2]+dz),
        actual_source_max_height_shifted_mm=float(max(s.hi[2] for s in solids.values())+dz),
        shell_minimum=nearest,shell_target_gap_mm=P['wheel_body_gap_mm'],
        shell_target_status='PASS' if nearest['gap_mm']>=P['wheel_body_gap_mm']-1e-5 else 'FAIL',
        source_geometric_minimum3mm_status='PASS' if nearest['gap_mm']>=3 else 'FAIL',
        lower_frame_envelope_status='PASS' if all(r['intersection_mm3']<1e-5 for r in local) else 'BLOCKED',
        all_nonexcluded_near_pairs=records,
        local_envelope_overlaps=[r for r in local if r['intersection_mm3']>=1e-5],
        combined_head_pose_count=130,minimum_head_AABB_separation_mm=min(moving),
        lean_ground_screen=lean,hub_shaft_retention='BLOCKED',loaded_radius='NOT_TESTED',
        nominal_belly_20mm_status='PASS' if solids['Body_Lower'].lo[2]+dz>=20-1e-5 else 'FAIL'))
assert sha(main)==before
out=dict(status='PASS',scope='Completed finite outer-size/ground-clearance study, not a passing wheel replacement',
    revision=P['revision'],source_blend_sha256=before,config_sha256=sha(PROJECT_DIR/'config/geometry.json'),
    verified_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),blender=bpy.app.version_string,
    sources=dict(product='https://banebots.com/banebots-compliant-wheel-4-x-0-8-hub-mount-60a-black/',
        saved_html_sha256=sha(HERE/'sources/banebots_T81P406BB.html')),
    source_part_count=len(solids),excluded_mating_or_replaced_parts=excluded,cases=cases,
    ground_screen_excluded_parts=sorted(n for n in solids if n.startswith(('Tire_','Wheel_Hub_'))),
    cylinder_facets=segments,maximum_radial_overbound_mm=52.5*(1/math.cos(math.pi/segments)-1),
    main_geometry_changed=False,candidate_adopted=False,manufacturing_release=False,replacement_status='BLOCKED',
    limits=['The product centre, tread profile and attachment are not modeled as exact vendor geometry.',
        'A full cylinder bounds the nominal outer wheel; an overlap would mean this bound is insufficient, not proof of real product collision.',
        'Old hubs/shafts/spacers/retention are excluded and remain explicitly BLOCKED for T81 compatibility.',
        'The inner-plane case is a conceptual lateral placement, not permission or a completed axle modification.',
        'Ground clearance assumes undeformed catalogue radius; loaded deflection, runout and manufacturing tolerances are unknown.',
        '130 head poses are finite; lean samples are geometry only, not balance or power-off standing.',
        'No tyre mass delta is claimed because the90.7g product weight scope and replacement hub masses are not settled.'])
(HERE/'outer_fit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
for row in cases:print(row['id'],'shell',row['shell_minimum'],'belly',row['belly_clearance_mm'],'local',row['lower_frame_envelope_status'],flush=True)

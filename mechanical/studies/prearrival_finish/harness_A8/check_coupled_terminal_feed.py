"""Independent loose-terminal feed with its attached, tangent-continuous wire.

The contact's REAR follows the wire centreline; the full rigid contact extends
forwards along the tangent.  This repairs the previous bare-centre trajectory's
missing trailing-wire constraint.  The physical hand/feed force, real crimp
profile and subsequent placement of the slack wire are not certified here.
"""
from pathlib import Path
FEED_SCRIPT=Path(__file__).resolve();FEED_DIR=FEED_SCRIPT.parent
FEED_HELPER=FEED_DIR/'plan_h06_documented_mates.py';__file__=str(FEED_HELPER)
exec(compile(FEED_HELPER.read_text().split('\nports=json.loads',1)[0],str(FEED_HELPER),'exec'),globals())
__file__=str(FEED_SCRIPT)
FEED_START=time.time()
OUT=FEED_DIR/'assembly_feed_v3';OUT.mkdir(exist_ok=True)
CONTACT_LENGTH=3.9;DIMS=[.8,1.35,CONTACT_LENGTH];R=8.;PAD=.32
template=manifold.Manifold.cube(DIMS,center=True).minkowski_sum(manifold.Manifold.sphere(PAD,32))
target_ids={'Yaw_Base','Pitch_Yoke'}
stage_without_mates={n for n in obstacles if n.startswith('Plug_')}

def radial_path(r0,upper_z=178.,step=.12):
    # A short accessible loose-wire lead starts the finite neck study.  Its
    # body-end PH plug is not connected and the rest of the harness is absent.
    rr=[];zz=[];aa=[];parts=[]
    def add(r,z,a,label):
        if rr:r,z,a=r[1:],z[1:],a[1:]
        rr.extend(r);zz.extend(z);aa.extend(a);parts.extend([label]*len(r))
    r=np.linspace(r0+R+3,r0+R,math.ceil(3/step)+1)
    add(r,np.full_like(r,139.),np.full_like(r,-math.pi/2),'body_free_lead')
    a=np.linspace(math.pi/2,0,math.ceil(R*math.pi/2/step)+1)
    add(r0+R*(1-np.cos(a)),147-R*np.sin(a),-a,'lower_R8')
    z=np.linspace(147,upper_z,math.ceil((upper_z-147)/step)+1)
    add(np.full_like(z,r0),z,np.zeros_like(z),'central_straight')
    t=np.linspace(0,math.pi/3,math.ceil(R*math.pi/3/step)+1)
    add(r0+R*(1-np.cos(t)),upper_z+R*np.sin(t),t,'upper_R8_out')
    q=t[::-1];zend=upper_z+2*R*math.sin(math.pi/3)
    add(r0+R-R*(1-np.cos(q)),zend-R*np.sin(q),q,'upper_R8_return')
    z=np.linspace(zend,202.1,math.ceil((202.1-zend)/step)+1)
    add(np.full_like(z,r0+R),z,np.zeros_like(z),'upper_free_end')
    return np.column_stack([rr,zz,aa]),parts

def pose(r,z,a,azimuth):
    phi=math.radians(azimuth);er=np.array([math.cos(phi),math.sin(phi),0.]);ez=np.array([0.,0.,1.])
    et=np.cross(ez,er);axis=er*math.sin(a)+ez*math.cos(a);x=er*math.cos(a)-ez*math.sin(a)
    rear=r*er+z*ez
    return rear,np.column_stack([x,et,axis,rear+CONTACT_LENGTH/2*axis])

def contact_hits(path,phase):
    found={};poses=[]
    for i,(r,z,a) in enumerate(path):
        rear,tr=pose(r,z,a,phase);poses.append(tr.tolist());m=template.transform(tr);bb=np.array(m.bounding_box())
        for name,s in obstacles.items():
            if name in target_ids or name in found:continue
            if np.any(bb[:3]>s.hi) or np.any(bb[3:]<s.lo):continue
            v=max(0.,float((m^s.m).volume()))
            if v>1e-6:found[name]={'object':name,'station':i,'rear_mm':rear.tolist(),'overlap_mm3':v}
        for name,s in fixed.items():
            if name in found or np.any(bb[:3]>s['hi']) or np.any(bb[3:]<s['lo']):continue
            v=max(0.,float((m^s['m']).volume()))
            if v>1e-6:found[name]={'object':name,'station':i,'rear_mm':rear.tolist(),'overlap_mm3':v}
    return found,poses

rows=[];selected=None
for r0 in [7.4,7.5,7.6,7.7,7.8]:
    path,parts=radial_path(r0);cases=[]
    for phase in [45,135,225,315]:
        pts=np.array([pose(*row,phase)[0] for row in path])
        hit,poses=contact_hits(path,phase)
        curve_error=R*(1-math.cos(.12/R/2))
        wire_installed=clear(pts,curve_error,target_ids)
        wire_preplugs=clear(pts,curve_error,target_ids|stage_without_mates)
        cases.append({'phase_deg':phase,'contact_hits':list(hit.values()),
            'contact_without_plugs_hits':[v for k,v in hit.items() if k not in stage_without_mates],
            'wire_with_mates_hit':wire_installed,'wire_before_mates_hit':wire_preplugs,
            'contact_transforms_3x4':poses,'wire_rear_curve_mm':pts.tolist()})
    all_clear=all(not c['contact_hits'] and c['wire_with_mates_hit'] is None for c in cases)
    stage_clear=all(not c['contact_without_plugs_hits'] and c['wire_before_mates_hit'] is None for c in cases)
    row={'radius_mm':r0,'status_with_mates':'PASS' if all_clear else 'BLOCKED',
        'status_before_mates':'PASS' if stage_clear else 'BLOCKED','cases':cases,
        'radial_z_axis_angle':path.tolist(),'segment_names':parts,'stations':len(path),
        'minimum_wire_centreline_radius_mm':R,'curve_chord_error_bound_mm':curve_error,
        'lower_contact_radial_minimum_bound_mm':r0+R-math.sqrt((R+DIMS[0]/2)**2+CONTACT_LENGTH**2)}
    rows.append(row)
    print('COUPLED_FEED',r0,row['status_with_mates'],row['status_before_mates'],
          [{k:c[k] for k in ['phase_deg','contact_hits','wire_with_mates_hit','wire_before_mates_hit']} for c in cases],
          round(time.time()-FEED_START,1),flush=True)
    if stage_clear:selected=row;break

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report={'status':'PASS' if selected else 'BLOCKED',
    'scope':'Coherent nominal contact plus all trailing wire centreline prefixes at yaw/pitch zero; excludes two candidate prints',
    'source_blend_sha256':source_hash,'source_script_sha256':sha(FEED_SCRIPT),'source_helper_sha256':sha(FEED_HELPER),
    'source_fixed_wires_sha256':sha(fixed_path),'source_mates_sha256':sha(FEED_DIR/'amass_mating/received_dimensions.json'),
    'source_contact_pdf_sha256':'ea3071ca5ee5a6069eba534fa39a10f34c9fb742ee42135a69ab4156bfa0f5de',
    'wire_OD_mm':OD,'reference_contact_dimensions_mm':DIMS,'contact_padding_mm':PAD,
    'required_wire_bend_radius_mm':REQUIRED_R,'excluded_prints':sorted(target_ids),
    'source_objects_included':207,'mating_allocations':len(plug),'prior_fixed_wires':len(fixed),
    'tested_cases':rows,'selected_radius_mm':selected['radius_mm'] if selected else None,
    'main_geometry_changed':False,'new_prints_built':False,'continuous_contact_sweep':'NOT_TESTED',
    'relaxation_into_installed_wire_routes':'NOT_TESTED','hand_access_and_grip':'NOT_TESTED',
    'complete_harness':'BLOCKED','manufacturing_release':False,
    'limitations':['Catalogue nominal reference box; no actual post-crimp profile or tolerances.',
        'The finite path starts3mm outside the lower R8 bend, not at a PH housing.',
        'Bare head contact follows its trailing wire tangent; body plug and wire anchors remain loose.',
        'An unoccupied following guide curve is a kinematic envelope, not passive wire-shape or friction proof.',
        'Excluding two prints is planning, not a complete installation PASS; full swept cuts still need evaluation.',
        'The installed r6.8 slack paths differ from the temporary feed; transition remains unverified.'],
    'elapsed_s':time.time()-FEED_START}
(OUT/'coupled_feed_screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('COUPLED_FEED_COMPLETE',report['status'],report['selected_radius_mm'],flush=True)

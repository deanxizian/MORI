"""Choose a wider temporary lower bend without changing actual hardware.

The earlier R8 contact sweep runs too close to the fixed reaction shaft. This
bounded family preserves the central/upper guide and varies only the lower
wire approach. Two prior unadopted print channels are excluded for later
explicit subtraction; no reaction shaft or real component is resized.
"""
from pathlib import Path
LBS_SCRIPT=Path(__file__).resolve(); LBS_HELPER=LBS_SCRIPT.parent/'build_CAM_larger_neck_candidate.py'
__file__=str(LBS_HELPER)
exec(compile(LBS_HELPER.read_text().split('\nfeed_path =',1)[0],str(LBS_HELPER),'exec'),globals())
__file__=str(LBS_SCRIPT)
LBS_OUT=LNC_OUT/'lower_bend';LBS_OUT.mkdir(exist_ok=True)
LBS_START=time.time()
LBS_DIMS=np.array([1.,1.8,4.1]);LBS_PAD=.32
LBS_TEMPLATE=manifold.Manifold.cube(LBS_DIMS.tolist(),center=True).minkowski_sum(manifold.Manifold.sphere(LBS_PAD,48))
LBS_TARGETS={n:m for n,m in current.items() if n not in ('Yaw_Base','Pitch_Yoke')}
LBS_TARGETS.update({'Plug_'+n:s.m for n,s in plug.items()})
LBS_TARGETS.update({'fixed_wire_'+n:s['m'] for n,s in fixed.items()})
LBS_BOXES={n:np.asarray(m.bounding_box()) for n,m in LBS_TARGETS.items()}
def lbs_path(radius,lower_top=147.,step=.08):
    R=8.;r0=7.6;rows=[];labels=[]
    def add(r,z,a,label):
        p=np.column_stack([r,z,a])
        if rows:p=p[1:]
        rows.extend(p.tolist());labels.extend([label]*len(p))
    r=np.linspace(r0+radius+3.,r0+radius,math.ceil(3/step)+1)
    add(r,np.full_like(r,lower_top-radius),np.full_like(r,-math.pi/2),'body_free_lead')
    a=np.linspace(math.pi/2,0,math.ceil(radius*math.pi/2/step)+1)
    add(r0+radius*(1-np.cos(a)),lower_top-radius*np.sin(a),-a,'lower_bend')
    z=np.linspace(lower_top,178,math.ceil((178-lower_top)/step)+1)
    add(np.full_like(z,r0),z,np.zeros_like(z),'central_straight')
    t=np.linspace(0,math.pi/3,math.ceil(R*math.pi/3/step)+1)
    add(r0+R*(1-np.cos(t)),178+R*np.sin(t),t,'upper_R8_out')
    q=t[::-1];zend=178+2*R*math.sin(math.pi/3)
    add(r0+R-R*(1-np.cos(q)),zend-R*np.sin(q),q,'upper_R8_return')
    z=np.linspace(zend,202.1,math.ceil((202.1-zend)/step)+1)
    add(np.full_like(z,r0+R),z,np.zeros_like(z),'upper_free_end')
    return np.asarray(rows),labels
def lbs_transforms(path,phase):
    ph=math.radians(phase);er=np.array([math.cos(ph),math.sin(ph),0.]);ez=np.array([0.,0.,1.]);et=np.cross(ez,er)
    ts=[]
    for r,z,a in path:
        axis=er*math.sin(a)+ez*math.cos(a);x=er*math.cos(a)-ez*math.sin(a)
        ts.append(np.column_stack([x,et,axis,r*er+z*ez+axis*LBS_DIMS[2]/2]))
    return ts
def lbs_first_hit(m):
    box=np.array(m.bounding_box())
    for n,target in LBS_TARGETS.items():
        b=LBS_BOXES[n]
        if np.any(box[:3]>b[3:]) or np.any(b[:3]>box[3:]):continue
        volume=max(0.,float((m^target).volume()))
        if volume>1e-5:return dict(obstacle=n,padded_intersection_mm3=volume)
    return None
rows=[];selected=None
for radius,lower_top in [(r,147.) for r in (8.,9.,10.,11.,12.,14.,16.)] + [(10.,z) for z in (147.25,147.5,147.75,148.,148.5,149.)]:
    path,labels=lbs_path(radius,lower_top);cases=[]
    for phase in (45,135,225,315):
        ts=lbs_transforms(path,phase);failure=None;checked=0
        for index,t in enumerate(ts):
            failure=lbs_first_hit(LBS_TEMPLATE.transform(t));checked+=1
            if failure:
                failure.update(station=index,segment=labels[index],transform_3x4=t.tolist());break
        cases.append(dict(phase_deg=phase,status='BLOCKED' if failure else 'PASS',checked_positions=checked,planned_positions=len(ts),failure=failure))
    row=dict(lower_bend_radius_mm=radius,lower_top_z_mm=lower_top,status='PASS' if all(c['status']=='PASS' for c in cases) else 'BLOCKED',cases=cases)
    rows.append(row);print('LARGER_NECK_LOWER',radius,lower_top,row['status'],[(c['phase_deg'],c['failure']) for c in cases],flush=True)
    if row['status']=='PASS':
        selected=row;np.savez_compressed(LBS_OUT/'selected_path.npz',radial_z_axis_angle=path,segment_names=np.asarray(labels));break
report=dict(status='PASS' if selected else 'BLOCKED',scope='Finite larger-contact lower-bend screening against all unchanged hardware and mating allocations; two print channels excluded',
    script_sha256=sha(LBS_SCRIPT),helper_sha256=sha(LBS_HELPER),source_main_sha256=source_hash,protected_sources=protected,
    replacement_sources={n:dict(path=str(p.relative_to(PROJECT)),sha256=sha(p)) for n,p in replacement_paths.items()},
    source_objects=len(ss),excluded_prints=['Yaw_Base','Pitch_Yoke'],mating_allocations=len(plug),fixed_wire_solids=len(fixed),
    contact_dimensions_mm=LBS_DIMS.tolist(),contact_evidence='ASSUMED requested space',clearance_padding_mm=LBS_PAD,
    maximum_spatial_step_mm=.08,rows=rows,selected_radius_mm=selected['lower_bend_radius_mm'] if selected else None,
    selected_lower_top_z_mm=selected['lower_top_z_mm'] if selected else None,
    selected_path_sha256=sha(LBS_OUT/'selected_path.npz') if selected else None,
    continuous_contact_sweep='NOT_TESTED',whole_trailing_wire_and_supply='NOT_TESTED',
    printed_geometry='NOT_TESTED',main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,elapsed_s=time.time()-LBS_START)
(LBS_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('LARGER_NECK_LOWER_DONE',report['status'],report['selected_radius_mm'],round(time.time()-LBS_START,2),flush=True)

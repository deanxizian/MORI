# Independent J3M replay copy; only study output directory differs from check_coupled_feed_relaxation.py.
"""Unanchored neck-wire reshaping after the bare contact has passed.

First shift the temporary straight feed inward; then introduce the existing
zero-yaw slack curve. Loose tails supply changing internal length. This is a
finite kinematic study, not body plug manipulation or the whole robot build.
"""
from pathlib import Path
RELAX_SCRIPT=Path(__file__).resolve();RELAX_DIR=RELAX_SCRIPT.parent
RELAX_HELPER=RELAX_DIR/'plan_h06_documented_mates.py';__file__=str(RELAX_HELPER)
exec(compile(RELAX_HELPER.read_text().split('\nports=json.loads',1)[0],str(RELAX_HELPER),'exec'),globals())
__file__=str(RELAX_SCRIPT);RELAX_START=time.time();OUT=RELAX_DIR/'assembly_feed_v3/open_mouth'
from numpy.polynomial import polynomial as poly
from mathutils.kdtree import KDTree
from interface_completion import replace_owned
RAW_MODE='--raw' in sys.argv
for name in ['Yaw_Base','Pitch_Yoke']:
    path=OUT/f'{name}_candidate.npz' if RAW_MODE else OUT/'cleaned'/f'{name}.npz'
    assert path.is_file()
    raw=np.load(path);m=manifold.Manifold(manifold.Mesh64(vert_properties=raw['vertices_mm'],tri_verts=raw['triangles'].astype(np.uint64)))
    if RAW_MODE:
        solid=ss[name];solid.v=np.array(raw['vertices_mm']);solid.f=raw['triangles'].astype(np.uint64);solid.m=m
        solid.lo=solid.v.min(0);solid.hi=solid.v.max(0);solid.tree=None
    else:
        obj=ss[name].o;replace_owned(name,m);ss[name]=Solid(obj)
    obstacles[name]=ss[name];trees[name]=ss[name].bvh()
central=json.loads((RELAX_DIR/'central_uart_curves.json').read_text())
zero=next(r for r in central['selected']['poses'] if r['yaw_deg']==0)
co=np.array(zero['angular_polynomial_coefficients']);contact=manifold.Manifold.cube([.8,1.35,3.9],center=True).minkowski_sum(manifold.Manifold.sphere(.32,32))
packing=json.loads((RELAX_DIR/'body_prefix_v2/packing.json').read_text())
pin_by_phase={r['azimuth_deg']:r['pin'] for r in packing['selected']}
installed=np.load(RELAX_DIR/'body_prefix_v2/body_to_yaw_curves.npz')
installed_meta=json.loads((RELAX_DIR/'body_prefix_v2/body_to_yaw_motion.json').read_text())
stage_rows=[];curves={};other={}
for phase,pin in pin_by_phase.items():
    points=installed[f'pin{pin}_yaw0'];fine=[]
    for a,b in zip(points,points[1:]):fine.extend(np.linspace(a,b,max(1,math.ceil(np.linalg.norm(b-a)/.015))+1)[:-1])
    fine=np.vstack([fine,points[-1:]]);kd=KDTree(len(fine))
    for i,p in enumerate(fine):kd.insert(Vector(p),i)
    kd.balance();err=next(r['curve_error_bound_mm'] for r in installed_meta['rows'] if r['pin']==pin and r['yaw_deg']==0)
    other[phase]=(fine,kd,err)

def core_curve(r0,z_upper,z_end,angular_fraction,phase):
    R=8.;a=np.linspace(math.pi/2,0,1051)
    low=np.column_stack([r0+R*(1-np.cos(a)),np.zeros(len(a)),147-R*np.sin(a)])
    t=np.linspace(0,1,4097);c=co*angular_fraction;theta=poly.polyval(t,c);d=poly.polyval(t,poly.polyder(c));dd=poly.polyval(t,poly.polyder(c,2));h=z_upper-147
    cs,sn=np.cos(theta),np.sin(theta)
    mid=np.column_stack([r0*cs,r0*sn,147+h*t])
    d1=np.column_stack([-r0*sn*d,r0*cs*d,np.full(len(t),h)])
    d2=np.column_stack([-r0*cs*d*d-r0*sn*dd,-r0*sn*d*d+r0*cs*dd,np.zeros(len(t))])
    curv=np.linalg.norm(np.cross(d1,d2),axis=1)/np.linalg.norm(d1,axis=1)**3
    bend=math.inf if curv.max()<1e-12 else 1/float(curv.max())
    nodes,weights=np.polynomial.legendre.leggauss(96);qt=(nodes+1)/2;qw=weights/2
    length_mid=float(np.sum(qw*np.sqrt(h*h+r0*r0*poly.polyval(qt,poly.polyder(c))**2)))
    # Polynomial extrema bound the whole central curve-to-chord error.
    def ext(coeff):
        roots=poly.polyroots(poly.polyder(coeff));samples=[0.,1.]+[float(v.real) for v in roots if abs(v.imag)<1e-8 and 0<v.real<1]
        return float(np.abs(poly.polyval(samples,coeff)).max())
    err=r0*(ext(poly.polyder(c))**2+ext(poly.polyder(c,2)))/(len(t)-1)**2/8
    a=np.linspace(0,math.pi/3,701);b=a[::-1][1:];zz=z_upper+2*R*math.sin(math.pi/3)
    rad=np.r_[r0+R*(1-np.cos(a)),r0+R-R*(1-np.cos(b))]
    z=np.r_[z_upper+R*np.sin(a),zz-R*np.sin(b)]
    up=np.column_stack([rad,np.zeros(len(rad)),z]);tail=np.linspace(zz,z_end,math.ceil((z_end-zz)/.012)+1)
    final=np.column_stack([np.full(len(tail),r0+R),np.zeros(len(tail)),tail])
    points=np.vstack([low,mid[1:],up[1:],final[1:]])
    rot=np.asarray(Matrix.Rotation(math.radians(phase),3,'Z'));points=points@rot.T
    total=R*math.pi/2+length_mid+2*R*math.pi/3+z_end-zz
    return points,max(err,R*(1-math.cos(math.pi/4200))),min(8.,bend),total

for stage in ['radial_and_height','introduce_slack']:
    for ix,u in enumerate(np.linspace(0,1,11)):
        r0=7.6-.8*u if stage=='radial_and_height' else 6.8
        zu=178+u if stage=='radial_and_height' else 179.
        ze=202.1+3.9*u if stage=='radial_and_height' else 206.
        angular=0. if stage=='radial_and_height' else float(u)
        for phase in [45,135,225,315]:
            points,err,bend,length=core_curve(r0,zu,ze,angular,phase)
            hit=clear(points,err)
            # Bare end parked tangent-up; the body side is deliberately loose.
            centre=points[-1]+[0,0,3.9/2];end=contact.translate(centre.tolist());bb=np.array(end.bounding_box());end_hits=[]
            for name,s in obstacles.items():
                if np.any(bb[:3]>s.hi) or np.any(bb[3:]<s.lo):continue
                vol=max(0.,float((end^s.m).volume()))
                if vol>1e-6:end_hits.append({'object':name,'overlap_mm3':vol})
            pair_gaps=[]
            for phase2,(p2,kd,err2) in other.items():
                if phase2==phase:continue
                minimum=min(float(kd.find(Vector(p))[2]) for p in points)
                step=float(np.linalg.norm(np.diff(points,axis=0),axis=1).max())
                bound=minimum-(step+.015)/2-err-err2-.6604-1e-5
                pair_gaps.append({'other_phase':phase2,'gap_lower_bound_mm':bound})
            key=f'{stage}_{ix}_{phase}';curves[key]=points
            row={'stage':stage,'fraction':float(u),'phase_deg':phase,'array_key':key,
                'status':'PASS' if hit is None and not end_hits and bend>=REQUIRED_R and all(p['gap_lower_bound_mm']>=.3 for p in pair_gaps) else 'BLOCKED',
                'source_hit':hit,'parked_contact_hits':end_hits,'other_installed_wire_gaps':pair_gaps,
                'minimum_sampled_bend_mm':bend,'partial_wire_length_mm':length,'chord_error_bound_mm':err}
            stage_rows.append(row)
        print('FEED_RELAX',stage,ix,[r['source_hit'] for r in stage_rows[-4:]],round(time.time()-RELAX_START,2),flush=True)
stem='relaxation_raw' if RAW_MODE else 'relaxation'
np.savez_compressed(OUT/f'{stem}_curves.npz',**curves)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
result={'status':'PASS' if all(r['status']=='PASS' for r in stage_rows) else 'BLOCKED',
    'scope':'22 prescribed finite unanchored wire-core shape stages, at yaw/pitch zero; free tails not complete body routing',
    'source_blend_sha256':source_hash,'source_script_sha256':sha(RELAX_SCRIPT),'source_helper_sha256':sha(RELAX_HELPER),
    'source_candidate_sha256':sha(OUT/'candidate.blend' if RAW_MODE else OUT/'cleaned/candidate.blend'),
    'solid_input':'exact_kernel_npz_before_storage_repair' if RAW_MODE else 'cleaned_reloaded_float32_npz',
    'source_installed_routes_sha256':sha(RELAX_DIR/'body_prefix_v2/body_to_yaw_curves.npz'),
    'source_central_law_sha256':sha(RELAX_DIR/'central_uart_curves.json'),
    'row_count':len(stage_rows),'source_objects':209,'mating_allocations':29,'fixed_wire_count':14,
    'rows':stage_rows,'internal_length_growth_mm':stage_rows[-1]['partial_wire_length_mm']-stage_rows[0]['partial_wire_length_mm'],
    'intermediate_shape_between_stages':'NOT_TESTED','tail_feeding_and_hand_access':'NOT_TESTED',
    'main_applied':False,'complete_harness':'BLOCKED','manufacturing_release':False,
    'elapsed_s':time.time()-RELAX_START}
(OUT/f'{stem}_screen.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('FEED_RELAX_COMPLETE',result['status'],result['internal_length_growth_mm'],flush=True)

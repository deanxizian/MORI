"""Temporary rigid-contact insertion paths; distinct from installed slack wires.

The central passage is traversed straight at zero yaw. Outward smooth offsets
around the two turns make room for the length of the contact. No hardware or
main print is changed. Contact is a catalogue-sized reference box, not CAD of
the final crimped terminal.
"""
from pathlib import Path
SCRIPT=Path(__file__).resolve()
HELPER=SCRIPT.parent.parent/'head_harness/check_loop_source_solids.py'
__file__=str(HELPER)
exec(compile(HELPER.read_text().split('\ngroups=[]')[0],str(HELPER),'exec'),globals())
__file__=str(SCRIPT);OUT=SCRIPT.parent/'terminal_threading';OUT.mkdir(exist_ok=True)
assert before=='bcaa5736a8cdf43441a6a83a6cb69606546cc01d2c0d28d98f4c09383e07368f'
R=8.;r0=6.8;L=3.9;width=.8;side=1.35;gap=.3
nominal=manifold.Manifold.cube([width,side,L],center=True)
envelope=nominal.minkowski_sum(manifold.Manifold.sphere(gap,32))
ev=np.asarray(envelope.to_mesh64().vert_properties[:,:3])
ef=np.asarray(envelope.to_mesh64().tri_verts)
np.savez_compressed(OUT/'nominal_contact_clearance_envelope.npz',vertices_mm=ev,triangles=ef)
fixed_manifolds={n:manifold.Manifold(manifold.Mesh64(vert_properties=r['vertices'],tri_verts=np.asarray(r['triangles'],dtype=np.uint64))) for n,r in fixed.items()}

def trajectory(lower_bump,upper_bump,upper_z):
    radial=list(np.linspace(32,14.8,116));zs=[139.]*len(radial);tilt=[-math.pi/2]*len(radial)
    a=np.linspace(math.pi/2,0,101)[1:]
    radial.extend(r0+R*(1-np.cos(a))+lower_bump*np.sin(2*a)**2)
    zs.extend(147-R*np.sin(a));tilt.extend(-a)
    zz=np.linspace(147,upper_z,int((upper_z-147)/.15)+2)[1:]
    radial.extend([r0]*len(zz));zs.extend(zz);tilt.extend([0.]*len(zz))
    alpha=math.pi/3;t=np.linspace(0,alpha,81)[1:];q=np.linspace(alpha,0,81)[1:]
    frac=np.r_[t,2*alpha-q]/(2*alpha)
    radial.extend(np.r_[r0+R*(1-np.cos(t)),r0+8-R*(1-np.cos(q))]+upper_bump*np.sin(math.pi*frac)**2)
    zs.extend(np.r_[upper_z+R*np.sin(t),upper_z+2*R*math.sin(alpha)-R*np.sin(q)])
    tilt.extend(np.r_[t,q])
    zend=upper_z+2*R*math.sin(alpha)
    zz=np.linspace(zend,206,int((206-zend)/.15)+2)[1:]
    radial.extend([r0+8]*len(zz));zs.extend(zz);tilt.extend([0.]*len(zz))
    return np.array(radial),np.array(zs),np.array(tilt)

def transform(radial,z,tilt,azimuth):
    a=math.radians(azimuth);er=np.array([math.cos(a),math.sin(a),0]);et=np.array([-math.sin(a),math.cos(a),0]);ez=np.array([0,0,1.])
    x=er*math.cos(tilt)-ez*math.sin(tilt);axis=er*math.sin(tilt)+ez*math.cos(tilt)
    return np.column_stack([x,et,axis,radial*er+z*ez])

angles=np.linspace(.0001,math.pi/2-.0001,20001)
need=6.33-(r0+R*(1-np.cos(angles))-L/2*np.sin(angles)-width/2*np.cos(angles))
lower_required=max(0.,float(np.max(need/np.sin(2*angles)**2)))
angles=np.linspace(.0001,math.pi/3,20001)
need=6.33-(r0+R*(1-np.cos(angles))-L/2*np.sin(angles)-width/2*np.cos(angles))
upper_required=max(0.,float(np.max(need/np.sin(1.5*angles)**2)))
# Deliberate allowance over the sampled analytic stem inequality, then actual
# source solids decide whether the complete collar and all other parts clear.
lower_selected=math.ceil(lower_required*1.05*10)/10
upper_selected=math.ceil(upper_required*1.05*10)/10
results=[]
for lower_bump,upper_bump,z0 in [(0.,0.,178.),(1.,1.5,178.),(lower_selected,upper_selected,178.)]:
    rr,zz,tt=trajectory(lower_bump,upper_bump,z0);cases=[]
    for angle in [45,135,225,315]:
        hits={};fixed_hits={};poses=[]
        for i,(r,z,t) in enumerate(zip(rr,zz,tt)):
            tr=transform(r,z,t,angle);m=envelope.transform(tr);bb=np.asarray(m.bounding_box())
            poses.append(tr.tolist())
            for name,s in ss.items():
                if name in ['Yaw_Base','Pitch_Yoke'] or name in hits:continue
                if np.any(bb[:3]>s.hi) or np.any(bb[3:]<s.lo):continue
                volume=max(0.,float((m^s.m).volume()))
                if volume>1e-5:hits[name]=dict(object=name,index=i,centre_mm=tr[:,3].tolist(),clearance_envelope_intersection_mm3=volume)
            for name,mf in fixed_manifolds.items():
                f=fixed[name]
                if name in fixed_hits or np.any(bb[:3]>f['hi']) or np.any(bb[3:]<f['lo']):continue
                volume=max(0.,float((m^mf).volume()))
                if volume>1e-5:fixed_hits[name]=dict(object=name,index=i,clearance_envelope_intersection_mm3=volume)
        cases.append(dict(azimuth_deg=angle,status='PASS' if not hits and not fixed_hits else 'FAIL',
                          source_hits=list(hits.values()),fixed_wire_hits=list(fixed_hits.values()),transforms_3x4=poses))
    results.append(dict(lower_outward_bump_mm=lower_bump,upper_outward_bump_mm=upper_bump,
                        upper_turn_start_z_mm=z0,status='PASS' if all(c['status']=='PASS' for c in cases) else 'BLOCKED',
                        cases=cases,station_count=len(rr),radial_z_tilt_rad=np.column_stack([rr,zz,tt]).tolist()))
    print('THREAD_TRANSIT',lower_bump,upper_bump,z0,
          [(c['azimuth_deg'],[h['object'] for h in c['source_hits']],c['fixed_wire_hits']) for c in cases],
          round(time.time()-start,1),flush=True)

out=dict(status='PASS' if any(r['status']=='PASS' for r in results) else 'BLOCKED',
    scope='Temporary bare-contact reference envelope vs207 unchanged source objects at discrete insertion stations; two prints excluded for candidate planning',
    source_blend_sha256=before,source_script_sha256=hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
    source_catalogue='hardware/v1_2/head_harness_A8_20261003/sources/JST_SH_20261003.pdf',
    source_catalogue_sha256='ea3071ca5ee5a6069eba534fa39a10f34c9fb742ee42135a69ab4156bfa0f5de',
    dimensions_mm=[width,side,L],gap_reference_mm=gap,contact_model='ASSUMED conservative nominal box from catalogue dimensions; no crimped-profile tolerances',
    approaches_and_handling='Bare precrimped end, housing not fitted; candidate only, supplier instruction not released',
    bump_design_basis={'reference_stem_radius_mm':6.,'minimum_radial_coordinate_mm':6.33,
        'lower_required_sampled_mm':lower_required,'upper_required_sampled_mm':upper_required,
        'lower_selected_mm':lower_selected,'upper_selected_mm':upper_selected,
        'formula':'r - (L/2)*abs(sin(tilt)) - (width/2)*abs(cos(tilt)) >= 6.33; outward sin-squared bump; 5 percent amplitude margin'},
    assembly_yaw_pitch_deg=[0,0],main_geometry_changed=False,results=results,
    actual_contact_fit='NOT_TESTED',trailing_flexible_wire='NOT_TESTED',
    sweep_between_stations='NOT_TESTED',full_harness='BLOCKED')
(OUT/'transit_screen.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==before

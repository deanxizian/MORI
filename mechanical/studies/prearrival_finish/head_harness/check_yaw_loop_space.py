"""All-eleven-wire planning cross-section and existing body annulus screen.

Catalogue wires are unselected samples. SPK and complete USB/servo cable
construction remain unknown. This never chooses a cable or changes a print.
"""
from pathlib import Path
BASE=Path(__file__).resolve().with_name('check_outer_neck_probes.py')
exec(compile(BASE.read_text().split('# Endpoints are named')[0],str(BASE),'exec'),globals())
power=float(wire_rows['P_J9']['绝缘外径最大mm']);signal=float(wire_rows['H06']['绝缘外径最大mm'])
pitch=power+.05;vstep=math.sqrt(3)*pitch/2
layout=[]
for iz,z in [(-1,-vstep),(0,0.),(1,vstep)]:
    coords=[-1.5,-.5,.5,1.5] if iz else [-1,0,1]
    for column,x in enumerate(coords):
        uart=bool(iz and abs(x)==1.5)
        branch='H06' if uart else 'P_J9' if not iz else 'P_J18' if iz==1 else 'SPK'
        layout.append(dict(branch=branch,cross_radial_mm=x*pitch,cross_vertical_mm=z,
            sample_OD_mm=signal if uart else power,
            evidence='ASSUMED_SPK_GAUGE_ALLOCATION' if branch=='SPK' else 'UNSELECTED_VENDOR_DOCUMENTED_WIRE_SAMPLE'))
assert len(layout)==11
radius=max(math.hypot(q['cross_radial_mm'],q['cross_vertical_mm'])+q['sample_OD_mm']/2 for q in layout)
gap=.3;bundle_with_gap=radius+gap
trees={n:s.bvh() for n,s in ss.items()}
angles=np.linspace(0,2*math.pi,361)[:-1];circle=np.column_stack([np.cos(angles),np.sin(angles),np.zeros(len(angles))])
results=[]
for z in np.arange(146.,158.01,.5):
    accepted=[];reject=collections.Counter()
    for rr in np.arange(30.,59.01,.5):
        pp=circle*rr+np.array([0,0,z]);clear=bundle_with_gap+rr*math.sin(math.pi/360)+1e-4
        fail=None;least=(1e9,None)
        for name,s in ss.items():
            mask=np.all(pp>=s.lo-clear,axis=1)&np.all(pp<=s.hi+clear,axis=1)
            for point in pp[mask]:
                dd=trees[name].find_nearest(Vector(point))[3]
                if dd<least[0]:least=(dd,name)
                if dd<clear:fail=name;break
            if fail:break
            if np.all(pp>=s.lo) and np.all(pp<=s.hi):
                tiny=manifold.Manifold.sphere(.01,16).translate(pp[0].tolist())
                if (tiny^s.m).volume()>tiny.volume()*.5:fail=name;break
        if fail:reject[fail]+=1
        else:accepted.append(dict(centre_radius_mm=float(rr),certified_project_gap_mm=gap,
            minimum_true_clearance_computed=False,nearest_tested_surface=least[1]))
    results.append(dict(z_mm=float(z),accepted_circles=accepted,reject_counts=dict(reject)))
    print('YAW_LOOP_LEVEL',z,[q['centre_radius_mm'] for q in accepted],flush=True)
out=dict(revision=P['revision'],source_blend_sha256=before,
    status='PASS' if any(q['accepted_circles'] for q in results) else 'BLOCKED',
    scope='Static complete-circle occupancy for one explicitly assumed eleven-wire envelope only',
    source_wire_csv_sha256=hashlib.sha256(wire_path.read_bytes()).hexdigest(),
    selected_harness=False,wire_cross_section=layout,wire_packing_gap_mm=.05,
    conservative_enclosing_diameter_mm=2*radius,project_external_gap_mm=gap,
    circle_angle_step_deg=1,circles_tested=len(results)*59,results=results,elapsed_s=time.time()-start,
    actual_fixed_endpoints='NOT_TESTED',constant_length_motion='NOT_TESTED',lead_approach='NOT_TESTED',
    main_geometry_changed=False,limits=['All eleven functional conductors are represented; actual USB shielding, servo cable and SPK gauge remain unknown.',
        'No core wire, terminal, jacket, tie, anchor or construction is selected.',
        '360 circle samples include between-sample distance coverage; this is a nominal source-solid occupancy check, not elastic behaviour.',
        'These complete circles have no fixed endpoints and are not a service-loop design.'])
(HERE/'yaw_loop_space.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
print('YAW_LOOP_SPACE_COMPLETE',out['status'],out['conservative_enclosing_diameter_mm'],time.time()-start,flush=True)

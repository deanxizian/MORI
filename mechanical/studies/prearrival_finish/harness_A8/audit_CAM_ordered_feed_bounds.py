"""Independent pose-stencil regression for the derived feed motion bounds.

The continuous certificate comes from the affine-secant derivative bound;
these direct corner comparisons guard against a code/frame mismatch. They
are not presented as a replacement continuous proof.
"""
from pathlib import Path
OFA_SCRIPT=Path(__file__).resolve();OFA_ROOT=OFA_SCRIPT.parent
OFA_HELPER=OFA_ROOT/'check_CAM_ordered_feed_continuous.py';__file__=str(OFA_HELPER)
exec(compile(OFA_HELPER.read_text().split('\nfor slot in ou_order:',1)[0],str(OFA_HELPER),'exec'),globals())
__file__=str(OFA_SCRIPT)
ofa_source=OFC_OUT/'screen.json';ofa_report=json.loads(ofa_source.read_text())
assert ofa_report['status']=='PASS' and ofa_report['script_sha256']==sha(OFA_HELPER)
import itertools
ofa_corners=np.array(list(itertools.product(*[[-d/2.,d/2.] for d in ofc_dims])))
ofa_checked=0;ofa_maxratio=0.;ofa_worst=None;ofa_vertical=0
for row in ofa_report['passed_intervals']:
    slot=row['slot'];a,b=row['arc_interval_mm'];mid=(a+b)/2.
    if row['method']=='bounded_guide_pose':
        tr,_=ou_terminal_pose(slot,mid,ofc_dims);reference=ofa_corners@tr[:,:3].T+tr[:,3]
        for s in np.linspace(a,b,9):
            tr,_=ou_terminal_pose(slot,float(s),ofc_dims);points=ofa_corners@tr[:,:3].T+tr[:,3]
            difference=float(np.linalg.norm(points-reference,axis=1).max());bound=row['displacement_mm']
            assert difference<=bound*(1+1e-8)+1e-9,(slot,a,b,float(s),difference,bound)
            ratio=difference/bound
            if ratio>ofa_maxratio:ofa_maxratio=ratio;ofa_worst=dict(slot=slot,arc_interval_mm=[a,b],sample_arc_mm=float(s),actual_corner_displacement_mm=difference,certified_bound_mm=bound)
            ofa_checked+=1
    else:
        assert row['method']=='exact_vertical_sweep'
        p0=ofc_at(slot,[a])[0];p1=ofc_at(slot,[b])[0]
        lo=p0+[-ofc_dims[0]/2.,-ofc_dims[1]/2.,0.];hi=p1+[ofc_dims[0]/2.,ofc_dims[1]/2.,ofc_dims[2]]
        for s in np.linspace(a,b,21):
            tr,_=ou_terminal_pose(slot,float(s),ofc_dims);points=ofa_corners@tr[:,:3].T+tr[:,3]
            assert np.max(abs(tr[:,:3]-np.eye(3)))<1e-10
            assert np.all(points>=lo-1e-9) and np.all(points<=hi+1e-9)
            ofa_vertical+=1
report=dict(status='PASS',scope='Direct pose/corner regression of the continuous derivative certificate; not physical validation',
    script_sha256=sha(OFA_SCRIPT),helper_sha256=sha(OFA_HELPER),source_continuous_sha256=sha(ofa_source),
    source_main_sha256=source_hash,corner_pose_comparisons=ofa_checked,vertical_pose_comparisons=ofa_vertical,
    worst_ratio=ofa_maxratio,worst_case=ofa_worst,all_eight_contact_vertices_checked=True,
    continuous_evidence='Analytic affine-secant derivative and exact vertical sweeps in the referenced report',
    main_applied=False,whole_harness='BLOCKED',manufacturing_release=False)
(OFC_OUT/'bound_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
(OFC_OUT/'BOUND_METHOD.md').write_text('''# Continuous ordered-feed bounds

For guide arclength s, the stored polyline p(s) has unit speed on each segment.
The orientation uses D(s) = p(s + e) - p(s - e), e = 0.002 mm, with clamped
end coordinates. Partitioning at guide knots shifted by +e and -e makes D
affine on every subinterval. Clamping breakpoints are included explicitly.

The minimum norm of an affine vector is found by projecting the origin onto
its line segment. Thus |T prime| is bounded by |D cross D prime| / min|D|^2.
For the projected-X frame, the YZ azimuth derivative is bounded by
|Dy Dz prime - Dz Dy prime| / min|(Dy,Dz)|^2. The base angular speed is at
most hypot(tangent-rate bound, azimuth-rate bound). Add the declared smooth
roll-rate bound; the helper's singular fallback is excluded by an explicit
positive projection check.

For a contact point at distance <= R from the rear datum, its speed is at
most 1 + R * angular-speed-bound. Half-interval displacement is added to
the midpoint collision clearance requirement. The active trailing-wire
prefix is taken through the interval end minus the explicit 2 mm crimp
region, so no newly fed material is omitted.

The long final stroke is exactly vertical with fixed orientation. Its box
sweep is checked directly. Own trailing material on that same axis remains
at least 2 mm behind the moving rear outside the declared crimp region;
other wires and previously completed contacts remain in the sweep checks.

The companion bound_audit.json compares all eight transformed contact
vertices at interval endpoints and interior poses against the derived
bound. This is a regression for frame/code correspondence, not the source
of the continuous proof. Numerical allowances and the assumed contact
allocation are recorded in screen.json. Real crimp shape, friction, hand
access and body-end material supply are outside this local certificate.
''')
assert sha(source)==source_hash
print('ORDERED_FEED_BOUND_AUDIT PASS',ofa_checked,ofa_vertical,ofa_maxratio,flush=True)

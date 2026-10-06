"""Read-only A8 fine-wire UART study. Never save or mutate the main model."""
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent / 'head_harness/check_outer_neck_probes.py'
# Reuse the established read-only Solid loading and exact validation proxies.
exec(compile(BASE.read_text().split('# Endpoints are named')[0], str(BASE), 'exec'), globals())
OUT = Path(__file__).resolve().parent
handoff = PROJECT / 'hardware/v1_2/handoff/mechanical_P5R7_prearrival_A8_shortlead.json'
a8 = json.loads(handoff.read_text())
evidence = PROJECT / a8['evidence']
assert hashlib.sha256(evidence.read_bytes()).hexdigest() == a8['evidence_sha256']
assert before == 'bcaa5736a8cdf43441a6a83a6cb69606546cc01d2c0d28d98f4c09383e07368f'
od = a8['geometry_candidate']['wire_od_max_mm']
assert od == .6604
gap = .3
within_gap = .1  # Trial independent-wire spacing, no sleeve or ribbon asserted.
trees = {n:s.bvh() for n,s in ss.items()}
angles = np.linspace(0, 2*math.pi, 721)[:-1]
unit = np.column_stack([np.cos(angles), np.sin(angles), np.zeros(len(angles))])
levels = []
for zmid in [158.8, 159.2, 159.5, 159.8, 160.2, 160.6]:
    zs = [zmid + (i-1.5)*(od+within_gap) for i in range(4)]
    accepted = []; rejects = collections.Counter()
    for rr in np.arange(32., 55.01, .5):
        failed = None
        for z in zs:
            pp = unit*rr + np.array([0,0,z])
            clear = od/2 + gap + rr*math.sin(math.pi/720) + 1e-4
            for name,s in ss.items():
                mask = np.all(pp>=s.lo-clear,axis=1)&np.all(pp<=s.hi+clear,axis=1)
                for p in pp[mask]:
                    if trees[name].find_nearest(Vector(p))[3] < clear:
                        failed = name; break
                if failed: break
                if np.all(pp>=s.lo) and np.all(pp<=s.hi):
                    tiny = manifold.Manifold.sphere(.01,16).translate(pp[0].tolist())
                    if (tiny^s.m).volume() > tiny.volume()*.5:
                        failed = name; break
            if failed: break
        if failed: rejects[failed] += 1
        else: accepted.append(float(rr))
    row = dict(id=f'UART_{zmid}',midplane_z_mm=zmid,individual_plane_z_mm=zs,
        accepted_static_circle_radii_mm=accepted,rejects=dict(rejects))
    levels.append(row)
    print('A8_UART_STATIC_SPACE',zmid,accepted,round(time.time()-start,2),flush=True)
result = dict(status='PASS' if any(r['accepted_static_circle_radii_mm'] for r in levels) else 'BLOCKED',
    scope='Four separate candidate wire circles, static assembled source only; no installed harness',
    source_blend_sha256=before,source_handoff=str(handoff.relative_to(PROJECT)),
    source_handoff_sha256=hashlib.sha256(handoff.read_bytes()).hexdigest(),
    source_evidence_sha256=hashlib.sha256(evidence.read_bytes()).hexdigest(),
    wire_reference='Alpha 2841/7 catalogue candidate, not released for procurement',
    wire_od_max_mm=od,wire_catalogue_bend_reference_mm=6.604,
    wire_count=4,member_ids=['H06_1','H06_2','H06_3','H06_4'],
    pin3='CAM local 3V3 reference; retained, not a main power conductor',
    external_project_surface_gap_mm=gap,within_group_surface_gap_assumed_mm=within_gap,
    sleeve_or_bundle=False,main_geometry_changed=False,levels=levels,elapsed_s=time.time()-start,
    dynamic_life='NOT_TESTED',real_anchors='NOT_TESTED',wire_ordering_suffix='BLOCKED',
    limitations=['Static circular screening does not prove the whole annulus or dynamic route clear.',
        'Wire layout and spacing are assumed allocations, not an installed retained assembly.',
        'Each later curve needs source solid, head poses, other loops and fixed-wire checks.'])
(OUT/'uart_space.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==before

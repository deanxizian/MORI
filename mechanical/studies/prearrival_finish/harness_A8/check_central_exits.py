"""Locate first clearance limit on straight continuations of central paths."""
from pathlib import Path
SCRIPT=Path(__file__).resolve();HELPER=SCRIPT.parent.parent/'head_harness/check_loop_source_solids.py'
__file__=str(HELPER)
exec(compile(HELPER.read_text().split('\ngroups=[]')[0],str(HELPER),'exec'),globals())
__file__=str(SCRIPT);OUT=SCRIPT.parent
src=OUT/'central_uart_curves.json';curves=json.loads(src.read_text())
assert curves['source_blend_sha256']==before
radius=curves['wire_od_max_mm']/2;required=radius+.3+.125+1e-4
rows=[]
for end,first,last,sign in [('body',150.,130.,-1),('yaw',182.,205.,1)]:
    for phase in curves['wire_zero_azimuths_deg']:
        p0=np.array([6.8*math.cos(math.radians(phase)),6.8*math.sin(math.radians(phase)),first])
        first_hit=None;last_clear=first
        # Only contiguous continuation from a checked clear endpoint. Surface
        # distance with half-step margin cannot skip a boundary crossing.
        for z in np.arange(first,last+sign*.01,sign*.25):
            trial=p0.copy();trial[2]=z;hit=None
            for yaw in range(-60,61,10):
                yawtr=np.asarray(rigidtr(yaw,0));world=trial if end=='body' else yawtr[:3,:3]@trial+yawtr[:3,3]
                for pitch in range(-20,26,5):
                    for name,s in ss.items():
                        if s.group in ['yaw','pitch']:
                            inv=np.linalg.inv(np.asarray(rigidtr(yaw,pitch if s.group=='pitch' else 0)))
                            point=inv[:3,:3]@world+inv[:3,3]
                        else:point=world
                        if np.any(point<s.lo-required) or np.any(point>s.hi+required):continue
                        d=trees[name].find_nearest(Vector(point))[3]
                        if d<required:
                            hit=dict(object=name,yaw_deg=yaw,pitch_deg=pitch,distance_mm=d,
                                point_world_mm=world.tolist(),required_with_sample_coverage_mm=required);break
                    if hit:break
                if hit:break
            if hit:first_hit=dict(z_mm=float(z),**hit);break
            last_clear=float(z)
        row=dict(end=end,wire_zero_azimuth_deg=phase,last_clear_z_mm=last_clear,
            clear_continuation_mm=abs(last_clear-first),first_clearance_bound_failure=first_hit,
            status='PASS' if first_hit is None else 'BLOCKED')
        rows.append(row);print('CENTRAL_EXIT',end,phase,last_clear,first_hit,flush=True)
result=dict(status='PASS' if all(x['status']=='PASS' for x in rows) else 'BLOCKED',
    scope='Eight straight endpoint continuations only, not an exhaustive route search',
    source_blend_sha256=before,source_curve_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),
    step_mm=.25,results=rows,main_geometry_changed=False,
    limits=['A failed straight continuation does not rule out a bent, side-entry or earlier branch.',
        'No connector axis, clamp or actual assembly path inferred from these staging points.',
        'Checks use the same finite head poses and closed source meshes as central-segment verification.'])
(OUT/'central_exit_check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==before

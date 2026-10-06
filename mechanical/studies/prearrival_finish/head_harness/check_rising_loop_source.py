"""Validate finite UART rising-loop candidates against current unedited solids."""
from pathlib import Path
BASE=Path(__file__).resolve().with_name('check_loop_source_solids.py')
exec(compile(BASE.read_text().split('\ngroups=[]')[0],str(BASE),'exec'),globals())
REFINE='--refine' in sys.argv
rise_path=HERE/('uart_rising_loops_refined.json' if REFINE else 'uart_rising_loops.json');rise=json.loads(rise_path.read_text())
assert rise['source_blend_sha256']==before
radius=rise['diameter_mm']/2
plane_groups=[g for g in seed['groups'] if g['status']=='PASS']

def pair_bound(p1,p2,e1,e2):
    # Every point of first polyline lies within half its longest segment of a
    # sampled vertex. All points of the other polyline are searched exactly.
    vv=np.diff(p2,axis=0);ww=p1[:,None,:]-p2[:-1][None,:,:]
    tt=np.clip(np.sum(ww*vv[None,:,:],axis=2)/np.sum(vv*vv,axis=1)[None,:],0,1)
    distance=np.linalg.norm(ww-tt[:,:,None]*vv[None,:,:],axis=2)
    return float(distance.min()-np.linalg.norm(np.diff(p1,axis=0),axis=1).max()/2-e1-e2)

cases=[];chosen=None
for i,candidate in enumerate(rise['selected']):
    failures=[];pairs=[];poses_tested=0
    for pose in candidate['poses']:
        points=np.asarray(pose['curve_mm']);yaw=pose['yaw_deg'];err=pose['second_derivative_chord_error_bound_mm']
        fh=fixed_clear(points,radius,err)
        if fh:failures.append(dict(kind='fixed_wire',yaw_deg=yaw,**fh));break
        for other in plane_groups:
            op=next(p for p in other['selected']['poses'] if p['yaw_deg']==yaw)
            # A vertical bound avoids an expensive curve-to-curve query when
            # the full rising route is already above the other entire plane.
            bound=min(abs(points[:,2]-other['plane_z_mm']))
            if points[:,2].min()<=other['plane_z_mm']<=points[:,2].max():bound=0.
            needed=radius+other['diameter_mm']/2+.3
            method='vertical slab bound'
            if bound<needed:
                bound=pair_bound(points,np.asarray(op['curve_mm']),err,op['second_derivative_chord_error_bound_mm'])
                method='curve-to-segment with sample and chord-error coverage'
            gap=bound-radius-other['diameter_mm']/2
            pairs.append(dict(other=other['id'],yaw_deg=yaw,surface_gap_lower_bound_mm=float(gap),method=method))
            if gap<.3:failures.append(dict(kind='other_loop',yaw_deg=yaw,other=other['id'],gap_bound_mm=float(gap)))
        if failures:break
        for pitch in range(-20,26,5):
            poses_tested+=1
            for name,s in ss.items():
                if s.group in ['yaw','pitch']:
                    inv=np.linalg.inv(np.asarray(rigidtr(yaw,pitch if s.group=='pitch' else 0)))
                    local=points@inv[:3,:3].T+inv[:3,3]
                else:local=points
                hit=sample_clear(local,radius,err,[name])
                if hit:failures.append(dict(kind='source_solid',yaw_deg=yaw,pitch_deg=pitch,**hit));break
            if failures:break
        if failures:break
    result=dict(candidate_index=i,status='FAIL' if failures else 'PASS',source_poses_tested=poses_tested,
                failures=failures,inter_group_checks=pairs)
    cases.append(result)
    print('RISING_SOURCE_CANDIDATE',i,result['status'],failures,time.time()-start,flush=True)
    if not failures:
        chosen=dict(candidate_index=i,geometry=candidate,source_solid_130_poses='PASS',
                    fourteen_fixed_wire_clearance='PASS',inter_group_clearance='PASS',inter_group_checks=pairs)
        break

out=dict(status='PASS' if chosen else 'BLOCKED',scope='Three independent yaw-loop group allocations only; no complete head harness',
         source_blend_sha256=before,source_rising_candidates_sha256=hashlib.sha256(rise_path.read_bytes()).hexdigest(),
         source_plane_candidates_sha256=hashlib.sha256(seed_path.read_bytes()).hexdigest(),
         source_fixed_wires_sha256=hashlib.sha256(fixed_path.read_bytes()).hexdigest(),
         cases=cases,selected=chosen,diameter_mm=rise['diameter_mm'],project_gap_mm=.3,
         member_count=4,total_functional_conductors_in_three_groups=11,main_geometry_changed=False,
         real_anchors='NOT_TESTED',individual_lengths='NOT_TESTED',neck_rise_to_yaw_support='NOT_TESTED',
         pitch_service_loop='NOT_TESTED',connector_approaches='NOT_TESTED',installation_sequence='NOT_TESTED',
         classification='PLACEHOLDER / ASSUMED unselected cable envelopes',elapsed_s=time.time()-start,
         limits=['All source-solid clearance checks refer to unchanged current meshes and declared validation proxies.',
                 '13 yaw × 10 pitch samples do not establish continuous motion, wire torsion or fatigue.',
                 'Group-centreline lengths are constant; individual wire lengths and sliding remain unqualified.',
                 'Staging points have no real clamps, ties, splice supports or connector interfaces.',
                 'The loops alone do not solve the passage to the head or pitch movement.'])
(HERE/('rising_loop_source_refined.json' if REFINE else 'rising_loop_source.json')).write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
print('RISING_SOURCE_COMPLETE',out['status'],time.time()-start,flush=True)

"""A coherent four-wire entry study, not a manufacturing harness.

Preserve the 32 mm central law and move it down 3 mm, join it tangentially
to R8 lower quarters and R8 upper S bends. Endpoints remain staging datums.
Read-only source check; no source geometry is replaced or saved.
"""
from pathlib import Path
SCRIPT=Path(__file__).resolve()
HELPER=SCRIPT.parent.parent/'head_harness/check_loop_source_solids.py'
__file__=str(HELPER)
exec(compile(HELPER.read_text().split('\ngroups=[]')[0],str(HELPER),'exec'),globals())
__file__=str(SCRIPT);OUT=SCRIPT.parent
assert len(ss)==209
central_path=OUT/'central_uart_curves.json'
central=json.loads(central_path.read_text())
assert central['source_blend_sha256']==before
angles=[45,135,225,315]
wire_radius=.3302;R=8.;r0=6.8;dz=-3.

def rotate(points,angle):
    a=math.radians(angle);cs,sn=math.cos(a),math.sin(a)
    return points@np.array([[cs,-sn,0],[sn,cs,0],[0,0,1]]).T

def lower():
    # Order follows the wire from the body staging endpoint toward the loop.
    rr=np.linspace(32,r0+R,345);zz=np.full(len(rr),147-R)
    t=np.linspace(math.pi/2,0,201)[1:]
    rr=np.r_[rr,r0+R*(1-np.cos(t))]
    zz=np.r_[zz,147-R*np.sin(t)]
    return np.column_stack([rr,np.zeros(len(rr)),zz])

def upper():
    alpha=math.acos(.5);t=np.linspace(0,alpha,161)
    q=np.linspace(alpha,0,161)[1:]
    rr=np.r_[r0+R*(1-np.cos(t)),r0+8-R*(1-np.cos(q))]
    zz=np.r_[179+R*np.sin(t),179+2*R*math.sin(alpha)-R*np.sin(q)]
    ztail=np.linspace(float(zz[-1]),206,265)[1:]
    return np.column_stack([np.r_[rr,np.full(len(ztail),r0+8)],
                            np.zeros(len(rr)+len(ztail)),np.r_[zz,ztail]])

lo=lower();up=upper()
local_length=(32-r0-R)+R*math.pi/2+33.2+2*R*math.acos(.5)+206-(179+2*R*math.sin(math.acos(.5)))
rows=[];all_hits=[];fixed_hits=[]
for pose in central['selected']['poses']:
    yaw=pose['yaw_deg'];middle=np.array(pose['first_wire_curve_mm']);middle[:,2]+=dz
    err=max(pose['second_derivative_chord_error_bound_mm'],R*(1-math.cos(math.pi/800)))
    for angle in angles:
        lp=rotate(lo,angle);mp=rotate(middle,angle);up0=rotate(up,angle)
        upw=rotate(up,angle+yaw)
        assert np.linalg.norm(lp[-1]-mp[0])<1e-9
        assert np.linalg.norm(mp[-1]-upw[0])<1e-9
        pts=np.vstack([lp,mp[1:],upw[1:]])
        hits=[]
        for name,s in ss.items():
            pitches=list(range(-20,26,5)) if s.group=='pitch' else [0]
            for pitch in pitches:
                if s.group in ['yaw','pitch']:
                    inv=np.linalg.inv(np.asarray(rigidtr(yaw,pitch if s.group=='pitch' else 0)))
                    local=pts@inv[:3,:3].T+inv[:3,3]
                else:local=pts
                h=sample_clear(local,wire_radius,err,[name])
                if h:hits.append(dict(yaw_deg=yaw,pitch_deg=pitch,azimuth_deg=angle,**h));break
        fh=fixed_clear(pts,wire_radius,err)
        if fh:fixed_hits.append(dict(yaw_deg=yaw,azimuth_deg=angle,**fh))
        all_hits.extend(hits)
        rows.append(dict(yaw_deg=yaw,azimuth_deg=angle,curve_mm=pts.tolist(),
                         lower_curve_body_mm=lp.tolist(),upper_curve_yaw_mm=up0.tolist(),
                         central_curve_world_mm=mp.tolist(),error_bound_mm=err,
                         analytic_total_staging_length_mm=local_length,
                         minimum_sampled_central_bend_mm=pose['sampled_minimum_bend_radius_mm'],
                         analytic_approach_bend_radius_mm=R,source_hits=hits))
    print('JOINED_ENTRY_YAW',yaw,'objects',sorted(set(h['object'] for h in all_hits)),
          'fixed_hits',len(fixed_hits),'seconds',round(time.time()-start,1),flush=True)

out=dict(status='PASS' if not all_hits and not fixed_hits else 'BLOCKED',
    scope='Joined lower/central/upper staging route; endpoints are not ports or anchors',
    source_blend_sha256=before,source_script_sha256=hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
    source_central_curve_sha256=hashlib.sha256(central_path.read_bytes()).hexdigest(),
    wire_od_mm=2*wire_radius,wire_azimuths_deg=angles,head_pose_count=130,
    wire_pose_instances=520,source_objects=209,central_z_mm=[147,179],
    required_bend_screen_mm=central['applied_bend_screen_mm'],
    analytic_staging_length_mm=local_length,rows=rows,
    source_obstacle_ids=sorted(set(h['object'] for h in all_hits)),
    source_hits=all_hits,fixed_wire_hits=fixed_hits,
    joined_tangent_continuity='PASS',tangent_method='Matching analytic vertical tangents at both joins',
    individual_wire_fixed_length='PASS',length_scope='13 sampled yaw poses, analytic approach lengths and solved central law',
    four_wire_mutual_clearance='NOT_TESTED',physical_retention='NOT_TESTED',
    connector_approaches='NOT_TESTED',main_model_changed=False,
    full_eleven_wire_harness='BLOCKED',supplier_cut_length='BLOCKED')
(OUT/'joined_entry_screen.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
print('JOINED_ENTRY_COMPLETE',out['source_obstacle_ids'],len(fixed_hits),flush=True)

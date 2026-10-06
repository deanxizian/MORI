"""Explicit S-bends around the reaction flange, never arbitrary graph corners.

The curves live on the yaw frame. Report every source obstacle before proposing
a local yoke edit. The end is a staging datum, not a connector or anchor.
"""
from pathlib import Path
SCRIPT=Path(__file__).resolve()
HELPER=SCRIPT.parent.parent/'head_harness/check_loop_source_solids.py'
__file__=str(HELPER)
exec(compile(HELPER.read_text().split('\ngroups=[]')[0],str(HELPER),'exec'),globals())
__file__=str(SCRIPT);OUT=SCRIPT.parent
assert len(ss)==209
def bend(R,delta,z0,angle):
    alpha=math.acos(1-delta/(2*R))
    t=np.linspace(0,alpha,121)
    q=np.linspace(alpha,0,121)[1:]
    r1=6.8+R*(1-np.cos(t));z1=z0+R*np.sin(t)
    r2=6.8+delta-R*(1-np.cos(q));z2=z0+2*R*math.sin(alpha)-R*np.sin(q)
    lead_z=np.linspace(178,z0,max(2,round((z0-178)*20)+1))[:-1]
    end_z=z0+2*R*math.sin(alpha)
    tail_z=np.linspace(end_z,206,max(2,round((206-end_z)*20)+1))[1:]
    rr=np.r_[np.full(len(lead_z),6.8),r1,r2,np.full(len(tail_z),6.8+delta)]
    zz=np.r_[lead_z,z1,z2,tail_z]
    a=math.radians(angle)
    pts=np.column_stack([rr*math.cos(a),rr*math.sin(a),zz])
    return pts,R*(1-math.cos(alpha/240)),dict(alpha_rad=alpha,arc_start_z_mm=z0,arc_end_z_mm=end_z,
        terminal_radius_mm=6.8+delta,analytic_minimum_bend_radius_mm=R,
        analytic_length_mm=z0-178+2*R*alpha+206-end_z)
rows=[]
# A bounded family chosen from the source sections: early outward motion is
# needed to clear the flange. Start below182 changes the last local-loop segment
# and is explicitly NOT compatible with the existing33.2mm loop as-is.
for R,delta,z0 in itertools.product([7.,8.,9.],[7.,8.,9.],[178.,179.,180.,181.]):
    family=[]
    for angle in [45,135,225,315]:
        pts,err,details=bend(R,delta,z0,angle);hits={}
        # Zero pose first, then every actual relative source pose. Sources are
        # tested independently to retain all blockers, not merely the first.
        for name,s in ss.items():
            if s.group=='yaw':poses=[(0,0)]
            elif s.group=='pitch':poses=[(0,p) for p in range(-20,26,5)]
            else:poses=[(y,0) for y in range(-60,61,10)]
            for yaw,pitch in poses:
                if s.group=='pitch':inv=np.linalg.inv(np.asarray(rigidtr(0,pitch)))
                elif s.group=='yaw':inv=np.eye(4)
                else:inv=np.asarray(rigidtr(yaw,0))
                local=pts@inv[:3,:3].T+inv[:3,3]
                hit=sample_clear(local,.3302,err,[name])
                if hit:hits[name]=dict(yaw_deg=yaw,pitch_deg=pitch,**hit);break
        fh=[]
        for yaw in range(-60,61,10):
            tr=np.asarray(rigidtr(yaw,0));world=pts@tr[:3,:3].T+tr[:3,3]
            h=fixed_clear(world,.3302,err)
            if h:fh.append(dict(yaw_deg=yaw,**h));break
        row=dict(radius_mm=R,radial_shift_mm=delta,start_z_mm=z0,azimuth_deg=angle,
            source_obstacles=list(hits.values()),fixed_wire_hits=fh,
            can_repair_yoke_only=(set(hits)<= {'Pitch_Yoke'} and not fh),
            current_source_clear=not hits and not fh,
            curve_mm=pts.tolist(),arc_chord_error_bound_mm=err,**details)
        family.append(row)
    rows.extend(family)
    print('UPPER_S_BEND',R,delta,z0,[list({x['object'] for x in r['source_obstacles']}) for r in family],
          'YOKE_ONLY',all(r['can_repair_yoke_only'] for r in family),round(time.time()-start,1),flush=True)
out=dict(status='PASS' if any(r['current_source_clear'] for r in rows) else 'BLOCKED',
    scope='Upper approach screening only; local-loop join, retention, pitch segment and supplier lengths unresolved',
    source_blend_sha256=before,source_script_sha256=hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
    wire_od_mm=.6604,external_gap_mm=.3,required_bend_screen_mm=6.9342,curves=rows,
    physical_source_objects=len(ss),head_poses=130,main_geometry_changed=False,
    old_local_loop_unchanged_compatibility='NOT_TESTED',complete_UART_harness='BLOCKED')
(OUT/'upper_entry_bends.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==before

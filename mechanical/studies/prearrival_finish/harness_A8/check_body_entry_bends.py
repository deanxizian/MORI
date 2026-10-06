"""Locate source obstacles on explicit quarter-circle lower wire approaches.

This does not cut a hole, establish retention or claim a complete connector route.
"""
from pathlib import Path
SCRIPT=Path(__file__).resolve()
HELPER=SCRIPT.parent.parent/'head_harness/check_loop_source_solids.py'
__file__=str(HELPER)
exec(compile(HELPER.read_text().split('\ngroups=[]')[0],str(HELPER),'exec'),globals())
__file__=str(SCRIPT);OUT=SCRIPT.parent
assert len(ss)==209
rows=[]
for R in [7.,8.,9.,10.]:
    a=np.linspace(0,math.pi/2,201)
    curve=np.column_stack([6.8+R*(1-np.cos(a)),np.zeros(len(a)),150-R*np.sin(a)])
    tail=np.column_stack([np.linspace(6.8+R,32.,201)[1:],np.zeros(200),np.full(200,150-R)])
    curve=np.vstack([curve,tail])
    error=R*(1-math.cos(math.pi/800))
    for angle in range(0,360,45):
        phi=math.radians(angle)
        rot=np.array([[math.cos(phi),-math.sin(phi),0],[math.sin(phi),math.cos(phi),0],[0,0,1]])
        points=curve@rot.T;hits={}
        for yaw in range(-60,61,10):
            for pitch in range(-20,26,5):
                for name,s in ss.items():
                    if name in hits:continue
                    if s.group not in ['yaw','pitch'] and (yaw,pitch)!=(-60,-20):continue
                    if s.group=='yaw' and pitch!=-20:continue
                    if s.group in ['yaw','pitch']:
                        inv=np.linalg.inv(np.asarray(rigidtr(yaw,pitch if s.group=='pitch' else 0)))
                        local=points@inv[:3,:3].T+inv[:3,3]
                    else:local=points
                    hit=sample_clear(local,.6604/2,error,[name])
                    if hit:hits[name]=dict(yaw_deg=yaw,pitch_deg=pitch,**hit)
        fixed_hit=fixed_clear(points,.6604/2,error)
        row=dict(radius_mm=R,azimuth_deg=angle,status='PASS' if not hits and not fixed_hit else 'BLOCKED',
            current_source_obstacles=list(hits.values()),fixed_wire_hit=fixed_hit,
            curve_mm=points.tolist(),length_mm=R*math.pi/2+32-(6.8+R),
            analytic_minimum_bend_radius_mm=R,maximum_chord_mm=float(np.linalg.norm(np.diff(points,axis=0),axis=1).max()),
            arc_chord_error_bound_mm=error)
        rows.append(row)
        print('BODY_ENTRY_BEND',R,angle,list(hits),bool(fixed_hit),round(time.time()-start,1),flush=True)
out=dict(status='PASS' if any(r['status']=='PASS' for r in rows) else 'BLOCKED',
    scope='Finite source obstacles on simple lower-body approach curves only; no solid changes',
    source_blend_sha256=before,source_script_sha256=hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
    wire_od_mm=.6604,external_gap_mm=.3,required_bend_screen_mm=6.9342,
    physical_source_objects=len(ss),head_poses=130,curves=rows,
    complete_UART_harness='BLOCKED',main_geometry_changed=False,
    limits=['Staging endpoint at radius32 is not the motion-board connector.',
            'No printed channel, clips, complete wiring or supplier drawing is created.',
            'Absence of a sampled collision is not continuous motion or physical bend-life qualification.'])
(OUT/'body_entry_bends.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==before

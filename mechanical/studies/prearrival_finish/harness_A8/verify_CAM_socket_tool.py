"""Continuous conservative key work volumes and current head-motion checks."""
from pathlib import Path
SV_SCRIPT=Path(__file__).resolve();SV_ROOT=SV_SCRIPT.parent
SV_HELPER=SV_ROOT/'check_CAM_socket_tool.py';__file__=str(SV_HELPER)
exec(compile(SV_HELPER.read_text().split("\nif __name__=='__main__':",1)[0],str(SV_HELPER),'exec'),globals())
__file__=str(SV_SCRIPT)
sv_screen=json.loads((SK_OUT/'screen.json').read_text());assert sv_screen['status']=='PASS'

def sv_hull2(points):
    points=sorted(set(map(tuple,points)))
    def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    a=[];b=[]
    for p in points:
        while len(a)>1 and cross(a[-2],a[-1],p)<=0:a.pop()
        a.append(p)
    for p in reversed(points):
        while len(b)>1 and cross(b[-2],b[-1],p)<=0:b.pop()
        b.append(p)
    return a[:-1]+b[:-1]

def sv_sector(face,angle_min=-30.,angle_max=30.,axial=8.,rad=1.5/math.sqrt(3)+.01,R=90.):
    p=np.array(face)+[0,-.8,0]
    # Circumscribed polygon, not an inscribed approximation of the arc.
    theta=np.radians(np.arange(angle_min,angle_max+.01,2.))
    arc=np.c_[np.sin(theta),np.cos(theta)]*(R/math.cos(math.radians(1.)))
    poly=np.vstack([np.zeros((1,2)),arc])
    off=np.arange(12)*2*math.pi/12.
    disk=np.c_[np.cos(off),np.sin(off)]*rad/math.cos(math.pi/12.)
    poly=sv_hull2((poly[:,None,:]+disk[None,:,:]).reshape(-1,2))
    # Local XY is global XZ; extrusion is toward negative global Y.
    m=manifold.CrossSection([poly]).extrude(2*rad+axial).rotate([90,0,0])
    m=m.translate((p+[0,4.5+rad+axial,0]).tolist())
    m+=axial_cylinder(p,axial,rad)
    return m

def axial_cylinder(p,travel,rad):
    return axial(rad,4.5+travel,p+[0,(4.5+travel)/2,0],[0,1,0])+axial(rad*math.sqrt(2),2*rad+travel,p+[0,4.5+travel/2,0],[0,1,0])

def sv_test(label,m,targets):
    hs=sk_hits(m,targets);ws=sk_wire_hits(m)
    gaps=[]
    if not hs:
        for n,q in targets.items():
            if overlap_boxes(m,q,3.):gaps.append({'object':n,'nominal_gap_mm':float(m.min_gap(q,3.))})
    return {'id':label,'status':'PASS' if not hs and not ws else 'BLOCKED','solid_hits':hs,'wire_hits':ws,
            'nearby_rigid_gaps':sorted(gaps,key=lambda r:r['nominal_gap_mm'])[:5]}

if __name__=='__main__':
    work=[];entry=[];grip=[];screw_arrival=[];started=time.time()
    for r in sk_rows:
        n=r['screw'];targets={k:m for k,m in sk_stage.items() if k!=n}
        m=sv_sector(sk_faces[n]);cache(SK_OUT/(n+'_work_sweep.npz'),m)
        row=sv_test(n,m,targets);work.append(row)
        cache(SK_OUT/(n+'_key.npz'),sk_tool(sk_faces[n],0.))
        # Enter from above at8mm stand-off, then translate to the hole.
        # The screw itself must fit this arrival, not just an empty key.
        pieces=sk_tool_parts(sk_faces[n],0.,8.)
        sweep=manifold.Manifold.batch_boolean([manifold.Manifold.batch_hull([q,q.translate([0,0,90])]) for q in pieces],manifold.OpType.Add)
        cache(SK_OUT/(n+'_entry_sweep.npz'),sweep)
        entry.append(sv_test(n,sweep,targets))
        b=np.array(r['screw_head_bearing_mm']);a=np.array(r['outward'])
        screw_parts=[axial(1.9,2.,b+a*9.,a),axial(1.,5.01,b+a*5.505,a)]
        arrival=manifold.Manifold.batch_boolean([manifold.Manifold.batch_hull([q,q.translate([0,0,90])]) for q in screw_parts],manifold.OpType.Add)
        arrival+=axial(1.9,10.,b+a*5.,a)+axial(1.,13.01,b+a*1.505,a)
        cache(SK_OUT/(n+'_arrival_sweep.npz'),arrival)
        screw_targets={k:m for k,m in targets.items() if k!=r['id']}
        vertical=sv_test(n,arrival,screw_targets)
        trials=[{'path':'above_then_axial','status':vertical['status'],'solid_hits':vertical['solid_hits'],'wire_hits':vertical['wire_hits']}]
        selected='above_then_axial'
        if vertical['status']!='PASS':
            straight=axial(1.9,42.,b+a*21.,a)+axial(1.,45.01,b+a*17.505,a)
            forward=sv_test(n,straight,screw_targets)
            trials.append({'path':'40mm_axial_from_front','status':forward['status'],'solid_hits':forward['solid_hits'],'wire_hits':forward['wire_hits']})
            selected='40mm_axial_from_front' if forward['status']=='PASS' else None
            screw_arrival.append(forward|{'selected_path':selected,'trials':trials})
            if selected:cache(SK_OUT/(n+'_arrival_sweep.npz'),straight)
        else:screw_arrival.append(vertical|{'selected_path':selected,'trials':trials})
        # Optional hand-clearance allocation around the top25mm of the key.
        # It is deliberately a cylinder, not a validated hand/force model.
        p=sk_faces[n]+[0,3.7+8.,0]
        g=axial(9.,25.,p+[0,0,77.5],[0,0,1]);grip.append(sv_test(n,g,targets))
        print('SOCKET_CONTINUOUS',n,row['status'],entry[-1]['status'],grip[-1]['status'],screw_arrival[-1]['status'],screw_arrival[-1]['solid_hits'],flush=True)
    # Check the installed larger screw heads against every stored physical
    # part, preserving current candidate print replacements where applicable.
    full={n:s.m for n,s in ss.items()}
    for n in ['Pitch_Yoke','Yaw_Base','Pitch_Cradle']:full[n]=sk_stage[n]
    full.update(sk_screws)
    motion=[]
    for yaw in range(-60,61,10):
        for pitch in range(-20,26,5):
            T=np.asarray(rigidtr(yaw,pitch));Y=np.asarray(rigidtr(yaw,0));hits=[]
            for r in sk_rows:
                n=r['screw'];m=sk_screws[n]
                for k,q in full.items():
                    if k in [n,r['id']]:continue
                    g=ss[k].group
                    placed=m if g=='pitch' else m.transform((np.linalg.inv(Y)@T)[:3,:4]) if g=='yaw' else m.transform(T[:3,:4])
                    hs=sk_hits(placed,{k:q})
                    hits.extend({'screw':n,**hit} for hit in hs)
            motion.append({'yaw_deg':yaw,'pitch_deg':pitch,'status':'PASS' if not hits else 'BLOCKED','hits':hits})
    result={'status':'PASS' if all(r['status']=='PASS' for r in work+entry+grip+screw_arrival+motion) else 'BLOCKED',
        'source_main_sha256':source_hash,'script_sha256':sha(SV_SCRIPT),'helper_sha256':sha(SV_HELPER),
        'screen_sha256':sha(SK_OUT/'screen.json'),'continuous_key_sweeps':work,'entry_paths':entry,'grip_allocations':grip,'screw_arrival_paths':screw_arrival,
        'head_motion':motion,'continuous_key_angle_range_deg':[-30,30],'continuous_key_axial_travel_mm':8.,
        'screw_translation_mm':8.,'disengagement_mm':1.,'nominal_socket_engagement_mm':.8,
        'entry_vertical_travel_mm':90.,'hand_clearance_allocation_mm':[18,25],
        'method':'Circumscribed convex2D sector contains all long-arm angles; its extrusion covers continuous axial travel. Separate short-arm cylinder avoids filling the entire L-shaped tool.',
        'screw_source_fields':'Bossard BN6101420569, nominal dimension construction; full thread fit NOT_TESTED',
        'head_motion_scope':'130 finite poses of four proposed screws against all209 physical objects; own four thread mates excluded individually',
        'whole_harness':'BLOCKED','initial_wire_threading_and_forming':'NOT_TESTED','main_applied':False,'approval':'NOT_REQUESTED',
        'tightening_torque_and_physical_tool':'NOT_TESTED','manufacturing_release':False,'elapsed_s':time.time()-started}
    (SK_OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    assert sha(source)==source_hash
    print('SOCKET_VERIFY_DONE',result['status'],len(motion),round(time.time()-started,1),flush=True)

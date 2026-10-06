"""M1.22 adopted bridge joint: actual solids, contact surfaces and finite service paths."""
from common import *
from yaw_bridge_mount import S,crossbolt_datums,crossbolt_enabled
from export import topology

def validate_crossbolt_joint(solids,Solid,iv,check):
    if not crossbolt_enabled():return None
    from validate import rigidtr
    d=crossbolt_datums();base=solids['Yaw_Base'];frame=solids['Load_Frame']
    changed={n:a for n,a in solids.items() if n in ['Yaw_Base','Load_Frame'] or n.startswith('Yaw_Base_')}
    def hits(movers,obstacles,tol=.01):
        rows=[]
        for n,a in movers.items():
            for k,b in obstacles.items():
                if a.o==b.o:continue
                v=iv(a,b)
                if v>tol:rows.append(dict(a=n,b=k,overlap_mm3=round(v,5)))
        return rows
    routes={o.name.removeprefix(PREFIX):Solid(o) for o in bpy.context.scene.objects if o.type=='MESH' and o.get('role')=='routing'}
    static=hits(changed,solids);wire=hits(changed,routes,.1)
    wheel_names={n for n in solids if n.startswith(('Tire_','Wheel_Hub_','Wheel_End_Screw_','Wheel_End_Washer_'))}
    removed={'Body_Upper','Body_Lower'}|wheel_names
    rows=[];toolhits=[];wheel_access=[];nuts=[]
    for sign in [-1,1]:
        name='Yaw_Base_'+str(sign)+'_Screw';a=solids[name];nut=solids['Yaw_Base_'+str(sign)+'_Nut']
        obstacles={n:s for n,s in solids.items() if n not in removed and n!=name}
        insertion=[]
        for travel in np.arange(0,S['screw_insertion_travel_mm']+.001,S['sample_step_mm']):
            mover=Solid(a.o,a,Matrix.Translation((sign*float(travel),0,0)))
            insertion += [dict(distance_mm=float(travel),**h) for h in hits({name:mover},obstacles)]
        t=cyl('crossbolt_driver_test',(sign*(d['headseat']+16),S['bolt_y_mm'],d['bolt_z']),S['tool_diameter_mm']/2,S['tool_length_mm'],'X')
        ts=Solid(t)
        toolhits += hits({'tool_'+str(sign):ts},{n:s for n,s in obstacles.items() if n!=name})
        wheel_access += hits({'tool_'+str(sign):ts},{n:s for n,s in solids.items() if n in wheel_names})
        bpy.data.objects.remove(t,do_unlink=True)
        # Smooth bore model validates axial overlap only, not the thread helix.
        nl=sorted([sign*float(nut.lo[0]),sign*float(nut.hi[0])]);tip=d['headseat']-S['screw_length_mm']
        rows.append(dict(id=name,axis='X',sign=sign,screw_insertion_failures=insertion,
            head_recess_margin_mm=d['outer']-max(sign*float(a.lo[0]),sign*float(a.hi[0])),
            thread_axial_overlap_mm=max(0,min(d['headseat'],nl[1])-max(tip,nl[0]))))
        nn='Yaw_Base_'+str(sign)+'_Nut'
        for travel in np.arange(0,S['nut_insertion_travel_mm']+.001,S['sample_step_mm']):
            mover=Solid(nut.o,nut,Matrix.Translation((-sign*float(travel),0,0)))
            nuts += [dict(distance_mm=float(travel),**h) for h in hits({nn:mover},{'Yaw_Base':base})]
    # Bare bridge extraction, nuts seated; head/reaction assembly is released first.
    bridge_movers={n:a for n,a in changed.items() if n=='Yaw_Base' or n.endswith('_Nut')}
    body_obstacles={n:a for n,a in solids.items() if a.group=='body' and n not in bridge_movers
        and not n.startswith(('Yaw_','Head_')) and n not in ['Body_Upper','Body_Lower']}
    withdraw=[]
    for travel in np.arange(0,S['bridge_insertion_travel_mm']+.001,S['sample_step_mm']):
        moving={n:Solid(a.o,a,Matrix.Translation((0,0,float(travel)))) for n,a in bridge_movers.items()}
        withdraw += [dict(distance_mm=float(travel),**h) for h in hits(moving,body_obstacles)]
    ys=list(range(-60,61,15));ps=list(range(-20,26,5));motion=[]
    for yaw in ys:
        for pitch in ps:
            moving={n:Solid(a.o,a,rigidtr(yaw,pitch if a.group=='pitch' else 0)) for n,a in solids.items() if a.group in ['yaw','pitch']}
            motion += [dict(yaw_deg=yaw,pitch_deg=pitch,**h) for h in hits(changed,moving)]
    contacts=[]
    for sign in [-1,1]:
        for y in [-19,19]:
            x=sign*(d['half']-d['thick']/2)
            foot=base.m.ray_cast([x,y,d['deck_top']-5],[x,y,d['deck_top']+5])
            seat=frame.m.ray_cast([x,y,d['deck_top']+5],[x,y,d['deck_top']-5])
            contacts.append(dict(x_mm=x,y_mm=y,foot_z_mm=float(foot[0].position[2]) if foot else None,
                deck_z_mm=float(seat[0].position[2]) if seat else None))
    side_rays=[]
    for sign in [-1,1]:
        for y in [-12,0,12]:
            for z in [116,122,134,143]:
                r=base.m.ray_cast([sign*80,y,z],[0,y,z]);x=float(r[0].position[0]) if r else None
                side_rays.append(dict(side=sign,y_mm=y,z_mm=z,outer_x_mm=x))
    topology_rows={}
    for n,a in changed.items():
        t=topology(a.v.tolist(),a.f.tolist());t['positive_solid_components']=sum(m.volume()>1e-6 for m in a.m.decompose());topology_rows[n]=t
    gap={n:round(base.m.min_gap(solids[n].m,30),3) for n in ['Battery','Battery_Tray','Power_Module','MCU_Carrier','Body_IMU']}
    ok=(not any([static,wire,withdraw,toolhits,nuts,motion]) and not any(r['screw_insertion_failures'] for r in rows)
        and all(r['head_recess_margin_mm']>=.14 and r['thread_axial_overlap_mm']>=S['nut_thickness_mm']-.01 for r in rows)
        and all(t['nonmanifold_edges']==t['inconsistent_edges']==t['degenerate_triangles']==0 and t['positive_solid_components']==1 for t in topology_rows.values())
        and all(r['foot_z_mm'] is not None and r['deck_z_mm'] is not None and abs(r['foot_z_mm']-r['deck_z_mm'])<.01 for r in contacts)
        and all(r['outer_x_mm'] is not None and abs(abs(r['outer_x_mm'])-d['half'])<.01 for r in side_rays)
        and not any(n.endswith('_Insert') for n in changed))
    report=dict(revision=P['revision'],status='PASS_GEOMETRY_ONLY' if ok else 'FAIL',geometry_source='config/geometry.json#/yaw_bridge_mount',datums_mm=d,
        changed_static_intersections=static,routing_intersections=wire,bridge_insertion_0_to_30_mm_each_1_mm=withdraw,
        mounts=rows,driver_diameter_4_2_mm_hits=toolhits,wheel_blocks_driver_before_removal=wheel_access,
        removed_for_side_access=sorted(removed),nut_bench_insertion_each_1_mm=nuts,
        combined_motion=dict(yaw_deg=ys,pitch_deg=ps,poses=len(ys)*len(ps),failures=motion),
        shoulder_contacts=contacts,side_face_rays=side_rays,bridge_to_components_minimum_gap_mm=gap,topology=topology_rows,
        overlap_below_deck_bottom_mm=d['deck_bottom']-d['tongue_bottom'],
        residual_cheek_under_head_mm=P['structure']['simple_modules']['side_plate_thickness_mm']-S['head_recess_depth_mm'],
        nut_pocket_backing_in_leg_mm=d['thick']-S['nut_pocket_depth_mm'],
        assembly=S['prerequisites'],print_fit='NOT_TESTED',strength='NOT_TESTED',fatigue='NOT_TESTED',creep='NOT_TESTED',
        thread_torque='NOT_TESTED',independent_exact_self_intersection='NOT_TESTED',global_wall_thickness='NOT_TESTED',
        complete_real_electronics_fit='BLOCKED: P5 complete populated/mated geometry not integrated; existing allocation retained',
        method='Manifold triangle-solid intersections including containment, tolerance0.01mm3; routing tolerance0.1mm3. 1mm translations and90 joint poses are finite samples, not continuous proofs. Existing vendor proxies retained. Local material dimensions do not certify strength.')
    save_json(ROOT/'reports/yaw_bridge_joint_validation.json',report)
    check('crossbolt_yaw_bridge_mount','PASS' if ok else 'FAIL','承重桥插接与横向M3穿栓；肩面承托，侧向装配及头部运动复核',
        dict(report='yaw_bridge_joint_validation.json',datums_mm=d,mounts=rows,shoulder_contacts=contacts,minimum_gaps_mm=gap),report['method'])
    return report

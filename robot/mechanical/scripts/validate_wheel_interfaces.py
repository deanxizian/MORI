"""Finite solid checks for the designed wheel connection and bench sequence."""
from common import *


def validate_wheel_interfaces(solids,Solid,iv,check):
    w=P.get('wheel_interface',{})
    if not w.get('enabled'):return
    tol=.01;report=json.loads((ROOT/'reports/wheel_interface_design.json').read_text());checks=[]
    def emit(id,status,summary,data,method):
        checks.append({'id':id,'status':status,'measurement':data,'method':method});check(id,status,summary,data,method)
    def axis_tr(sign,angle):
        c=Vector((sign*D['wheel_x'],0,D['wheel_z']))
        return Matrix.Translation(c)@Matrix.Rotation(math.radians(angle),4,'X')@Matrix.Translation(-c)
    # Unlike the old visual parenting, this verifies that mismatched relative
    # rotation meets actual D-flat material and that axial stops exist.
    locks=[]
    for side,sign in [('L',-1),('R',1)]:
        shaft=solids['Wheel_Axle_'+side];hub=solids['Wheel_Hub_'+side];bear=solids['Wheel_Bearing_'+side+'_Inner']
        contact_angles=[]
        for direction in [-1,1]:
            first=None
            for tenths in range(1,31):
                a=direction*tenths/10
                v=iv(shaft,Solid(hub.o,hub,axis_tr(sign,a)))
                if v>.002:first=a;break
            contact_angles.append(first)
        shoulder_witness=iv(shaft,Solid(bear.o,bear,Matrix.Translation((-sign*.2,0,0))))
        locks.append({'side':side,'key_length_mm':w['shaft_end_abs_x_mm']-w['hub_key_start_abs_x_mm'],'neutral_overlap_mm3':iv(shaft,hub),'first_relative_D_contact_deg':contact_angles,'inner_bearing_into_shoulder_0_2mm_witness_volume_mm3':shoulder_witness,'shaft_tip_below_washer_seat_mm':w['hub_washer_seat_abs_x_mm']-w['shaft_end_abs_x_mm']})
    ok=all(r['neutral_overlap_mm3']<tol and all(a is not None and abs(a)<=1.5 for a in r['first_relative_D_contact_deg']) and r['inner_bearing_into_shoulder_0_2mm_witness_volume_mm3']>.01 and r['key_length_mm']>=12 and r['shaft_tip_below_washer_seat_mm']>=.15 for r in locks)
    emit('wheel_positive_drive_and_axial_stack','PASS' if ok else 'FAIL','双扁位实体止转、轴肩止挡与端部锁紧座',locks,'Actual shaft/hub intersection under relative0.1deg increments; positive interference is an intentional stop witness, not an assembled collision. This bounds nominal geometric take-up only; elastic twist, thread forces, creep and purchased tolerances are NOT_TESTED.')
    fast=[];toolbad=[]
    for row in report['output_fasteners']:
        side=row['side'];sign=-1 if side=='L' else 1;y,z=row['yz_mm'];xf=w['output_face_abs_x_mm']+w['flange_thickness_mm']
        # The flange screws must be installed BEFORE the bearings obscure the
        # small bolt circle. Include the entire one-piece shoulder in the test.
        bench=[n for n in solids if n in ['Drive_Motor_'+side,'Wheel_Axle_'+side] or n.startswith('S288_Output_'+side) or n.startswith('Wheel_Output_Screw_'+side)]
        start=row['head_face_abs_x_mm']+.05
        o=cyl('flange_tool',(sign*(start+15),y,z),w['output_tool_diameter_mm']/2,30,'X');t=Solid(o)
        hits=[{'part':n,'volume_mm3':iv(t,solids[n])} for n in bench if n!=row['id'] and iv(t,solids[n])>tol]
        bpy.data.objects.remove(o,do_unlink=True)
        approach=[];screw=solids[row['id']]
        for distance in range(0,36):
            moving=Solid(screw.o,screw,Matrix.Translation((sign*distance,0,0)))
            for n in bench:
                if n==row['id']:continue
                v=iv(moving,solids[n])
                if v>tol:approach.append({'distance_mm':distance,'part':n,'volume_mm3':v})
        item={**row,'tool_hits':hits,'screw_insertion_hits':approach};fast.append(item)
        if hits or approach:toolbad.append(item)
    engagement=w['output_screw_length_mm']-w['flange_thickness_mm']
    emit('s288_six_hole_flange_installation','PASS' if not toolbad and 2<=engagement<=w['output_pilot_depth_max_mm']-.3 else 'FAIL','两侧六孔连接、螺钉伸入量及装轴承前的工具通道',{'screws':len(fast),'engagement_mm':engagement,'maximum_vendor_depth_mm':3,'failed_fasteners':len(toolbad),'details':'wheel_interface_validation.json'},'Actual root/head envelope translated each1mm over35mm and2.5mm x30mm tool shank; use only the documented S288 M2 self-tapping family. Head/thread/tip geometry still a procurement requirement; no tightening or pull-out qualification.')
    sweeps=[];bad=[];minimum=None
    selected_fixed=['Drive_Bridge','Motor_Retainer','Body_Lower','Body_Upper','Load_Frame']+[n for n in solids if n.startswith('Wheel_Cap_Clamp_')]
    for side,sign in [('L',-1),('R',1)]:
        moving=[n for n,a in solids.items() if a.group=='wheel_'+side]
        for deg in range(0,361,w['sweep_step_deg']):
            for n in moving:
                a=Solid(solids[n].o,solids[n],axis_tr(sign,deg))
                for k in selected_fixed:
                    target=solids[k]
                    if np.any(a.hi<target.lo-2) or np.any(target.hi<a.lo-2):continue
                    v=iv(a,target);gap=a.m.min_gap(target.m,2)
                    if v>tol:bad.append({'side':side,'deg':deg,'moving':n,'fixed':k,'volume_mm3':v})
                    row={'deg':deg,'moving':n,'fixed':k,'gap_mm_capped2':gap}
                    if minimum is None or gap<minimum['gap_mm_capped2']:minimum=row
            sweeps.append({'side':side,'angle_deg':deg})
    emit('complete_wheel_drive_sweep','FAIL' if bad else 'PASS','法兰、螺钉、整轴、隔套和轮毂共同旋转一周',{'poses_each':len(sweeps)//2,'step_deg':w['sweep_step_deg'],'failed_pairs':len(bad),'minimum_nonbearing_gap':minimum,'details':'wheel_interface_validation.json'},'Closed-solid intersections and distances against fixed drive/frame/shell/cap bolts each5deg. Bearings are intended journal contacts and checked separately. Finite samples are not a continuous proof or tolerance/deflection simulation.')
    # Each procedure is tested against only the stated, physically possible
    # assembly stage; parts are not silently removed to hide a collision.
    shell_removed={n for n in solids if n.startswith(('Shell_Screw','Shell_Insert'))}
    wheel_removed={n for n in solids if n.startswith(('Tire_','Wheel_Hub_','Wheel_End_')) or n in ['Wheel_Spacer_L_1','Wheel_Spacer_R_1']}
    cap_screws={n for n in solids if n.startswith('Wheel_Cap_Clamp_Screw')}
    cases=[('Body_lower_open_axle_slots',['Body_Lower'],(0,0,-1),90,shell_removed|wheel_removed)]
    cap_moving=['Motor_Retainer','Motor_Retainer_Pad_-1','Motor_Retainer_Pad_1']
    cases.append(('Common_motor_bearing_cap',cap_moving,(0,0,-1),45,shell_removed|wheel_removed|{'Body_Lower'}|cap_screws))
    for side,sign in [('L',-1),('R',1)]:
        names=['Drive_Motor_'+side,'Wheel_Axle_'+side,'Wheel_Bearing_'+side+'_Inner','Wheel_Bearing_'+side+'_Outer','Wheel_Spacer_'+side+'_0']+[n for n in solids if n.startswith(('S288_Output_'+side,'Wheel_Output_Screw_'+side))]
        cases.append(('Motor_shaft_bearing_cartridge_'+side,names,(0,0,-1),60,shell_removed|wheel_removed|{'Body_Lower'}|set(cap_moving)|cap_screws))
    services=[]
    for label,names,direction,travel,removed in cases:
        errors=[]
        for distance in range(0,travel+1):
            tr=Matrix.Translation(Vector(direction)*distance)
            for n in names:
                a=Solid(solids[n].o,solids[n],tr)
                for k,t in solids.items():
                    if k in removed or k in names:continue
                    v=iv(a,t)
                    if v>tol:errors.append({'distance_mm':distance,'moving':n,'fixed':k,'overlap_mm3':v})
        services.append({'case':label,'moving':names,'removed_first':sorted(removed),'direction':direction,'travel_mm':travel,'step_mm':1,'failures':errors})
    emit('wheel_drive_service_sequence','FAIL' if any(r['failures'] for r in services) else 'PASS','下壳、共用底盖与两套电机/轴承组件的顺序拆装',{'cases':len(services),'failed_cases':sum(bool(r['failures']) for r in services),'details':'wheel_interface_validation.json'},'Actual solid translation each1mm after explicit preceding removals. Motors disabled and chassis supported. Disconnect real motor leads first; human grip and cable plugs remain NOT_TESTED.')
    captools=[]
    for i,(x,y) in enumerate(w['clamp_bolt_xy_mm']):
        end=w['clamp_plate_bottom_z_mm']-3-.05
        o=cyl('cap_tool',(x,y,end-15),2.5,30);t=Solid(o)
        removed={'Body_Lower','Wheel_Cap_Clamp_Screw_'+str(i)}|shell_removed
        hits=[{'part':n,'volume_mm3':iv(t,a)} for n,a in solids.items() if n not in removed and iv(t,a)>tol]
        bpy.data.objects.remove(o,do_unlink=True);captools.append({'index':i,'hits':hits})
    emit('wheel_cap_tools','FAIL' if any(r['hits'] for r in captools) else 'PASS','共用底盖四枚螺钉的下方工具通道',captools,'5mm x30mm straight tool shank with lower shell removed; tool handles and exact drive recess are not modeled.')
    wall=[];body=solids['Body_Lower'];tri=body.v[body.f];u=tri[:,1,1:]-tri[:,0,1:];vv=tri[:,2,1:]-tri[:,0,1:];den=u[:,0]*vv[:,1]-u[:,1]*vv[:,0];mask=np.abs(den)>1e-10
    for sx in [-1,1]:
        for sy in [-1,1]:
            for yy in [50,51]:
                hits=body.m.ray_cast([sx*120,sy*yy,88],[-sx*120,sy*yy,88])
                first=next((h for h in hits if h.normal[0]*sx>0),None)
                second=next((h for h in hits if first and h.distance>first.distance+1e-7 and h.normal[0]*sx<0),None)
                thick=abs(second.position[0]-first.position[0]) if second else None
                # Independent float64 barycentric triangle/line intersections.
                delta=np.array([sy*yy,88])-tri[:,0,1:];aa=np.zeros(len(tri));bb=np.zeros(len(tri))
                aa[mask]=(delta[mask,0]*vv[mask,1]-delta[mask,1]*vv[mask,0])/den[mask]
                bb[mask]=(u[mask,0]*delta[mask,1]-u[mask,1]*delta[mask,0])/den[mask]
                inside=mask&(aa>=-1e-8)&(bb>=-1e-8)&(aa+bb<=1+1e-8)
                xx=tri[:,0,0]+aa*(tri[:,1,0]-tri[:,0,0])+bb*(tri[:,2,0]-tri[:,0,0])
                exact=sorted(set(round(float(x),5) for x in xx[inside]),reverse=sx>0)
                mismatch=max(min(abs(float(h.position[0])-x) for x in exact) for h in hits) if exact else 999
                wall.append({'side':sx,'y_mm':sy*yy,'z_mm':88,'ray_wall_mm':thick,'independent_triangle_error_mm':mismatch})
    emit('wheel_shell_local_walls','PASS' if all(r['ray_wall_mm'] is not None and r['ray_wall_mm']>=2.2 and r['independent_triangle_error_mm']<.001 for r in wall) else 'FAIL','轮窝指定区域的真实壁厚与独立算法交叉核对',wall,'Float64 Manifold ray entry/exit, cross-checked with independent barycentric triangle intersections at8 stations. Blender BVH near-edge repeated-hit false positives excluded by this independent evidence, not by lowering a thickness threshold. No global minimum-wall or FDM strength claim.')
    # Transparent load screening, deliberately no strength PASS.
    force=w['screening_total_mass_kg']*9.81*w['screening_dynamic_load_factor']/2
    a,b=w['bearing_centers_abs_x_mm'];overhang=D['wheel_x']-b;span=b-a;T=w['screening_peak_torque_Nm'];dia=w['shaft_journal_diameter_model_mm']/1000
    moment=force*overhang/1000;sigma=32*moment/(math.pi*dia**3)/1e6;tau=16*T/(math.pi*dia**3)/1e6
    load={'assumed_mass_kg':w['screening_total_mass_kg'],'assumed_dynamic_factor':w['screening_dynamic_load_factor'],'wheel_radial_load_N':round(force,1),'bearing_span_mm':span,'wheel_overhang_mm':overhang,'inner_bearing_reaction_magnitude_N':round(force*overhang/span,1),'outer_bearing_reaction_magnitude_N':round(force*(1+overhang/span),1),'screening_torque_Nm':T,'output_screw_tangential_force_each_N':round(T/(6*w['output_hole_pcd_mm']/2000),1),'smooth_6mm_shaft_bending_MPa':round(sigma),'smooth_6mm_shaft_torsion_MPa':round(tau),'nominal_von_Mises_MPa':round(math.sqrt(sigma*sigma+3*tau*tau)),'qualification':'NOT_TESTED; static equilibrium and smooth-shaft screening only. Excludes impact direction, thread/flat/scallop stress concentration, fatigue, plastic flange pull-out, FDM anisotropy, clamp creep, bearing preload and S288 life.0.6Nm is a peak screening case, not continuous rating.'}
    emit('wheel_drive_strength_and_fit','NOT_TESTED','轮驱载荷粗算与试配边界',load,load['qualification'])
    out={'revision':P['revision'],'status':'FAIL' if any(c['status']=='FAIL' for c in checks) else 'PASS_GEOMETRY_ONLY','checks':checks,'output_screw_tools':fast,'sweep_failures':bad,'sweep_minimum':minimum,'service_cases':services,'cap_tools':captools,'load_screening':load,'sources':[w['vendor_source'],w['bearing_source']],'physical_qualification':False}
    save_json(ROOT/'reports/wheel_interface_validation.json',out)
    report['status']=out['status'];report['validation_report']='mechanical/reports/wheel_interface_validation.json';save_json(ROOT/'reports/wheel_interface_design.json',report)

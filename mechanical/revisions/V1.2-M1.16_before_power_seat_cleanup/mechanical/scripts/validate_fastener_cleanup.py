"""Actual solid checks for recessed mounting and the printed-part feature audit."""
from common import *
from yaw_bridge_mount import sites,datums

def validate_fastener_cleanup(solids,Solid,iv,check):
    s=P.get('yaw_bridge_mount',{});f=P.get('fastener_cleanup',{})
    if not s.get('enabled'):return
    base=solids['Yaw_Base'];half=P['belly_relayout']['yaw_bridge_half_width_mm'];samples=[]
    for sign in [-1,1]:
        for y in [-12,0,12]:
            for z in [116,122,134,143]:
                hits=base.m.ray_cast([sign*80,y,z],[0,y,z])
                x=float(hits[0].position[0]) if hits else None
                samples.append({'side':sign,'y_mm':y,'z_mm':z,'outer_x_mm':x})
    wall_ok=all(a['outer_x_mm'] is not None and abs(abs(a['outer_x_mm'])-half)<.01 for a in samples)
    top,bottom,head=datums();rows=[];removed={'Body_Upper','Body_Lower','Battery','Battery_Tray'}|{n for n in solids if n.startswith('Battery_Retainer')}
    for sign,x,y in sites():
        name='Yaw_Base_'+str(sign)+'_Screw';bolt=solids[name];insert=solids['Yaw_Base_'+str(sign)+'_Insert'];bad=[]
        for d in range(0,int(s['screw_insertion_travel_mm'])+1,int(s['sample_step_mm'])):
            a=Solid(bolt.o,bolt,Matrix.Translation((0,0,-d)))
            for n,b in solids.items():
                if n in removed or n==name:continue
                v=iv(a,b)
                if v>.01:bad.append({'distance_mm':d,'part':n,'overlap_mm3':v})
        rows.append({'id':name,'xy_mm':[x,y],'head_recess_below_deck_margin_mm':float(bolt.lo[2])-bottom,'insert_engagement_mm':min(float(bolt.hi[2]),float(insert.hi[2]))-max(head,float(insert.lo[2])),'screw_insertion_failures':bad})
    ok=wall_ok and max(abs(float(base.lo[0])),abs(float(base.hi[0])))<=half+.01 and not any(a['screw_insertion_failures'] for a in rows) and all(a['head_recess_below_deck_margin_mm']>=.19 and a['insert_engagement_mm']>=3.9 for a in rows)
    check('flush_yaw_bridge_mount','PASS' if ok else 'FAIL','承重桥无外伸耳或竖槽；底面螺钉装入与嵌件名义啮合',{'outer_width_mm':float(base.hi[0]-base.lo[0]),'side_face_rays':samples,'mounts':rows,'removed_first':sorted(removed),'minimum_nominal_insert_side_wall_mm':(P['belly_relayout']['yaw_bridge_leg_thickness_mm']-s['insert_pilot_diameter_mm'])/2},'Actual mesh side rays; complete screw solids translated each1mm,20mm approach; screw heads within deck lower surface. Smooth thread envelope only; insert pull-out/creep/printing unqualified.')
    if not f.get('enabled'):return
    sm=f['speaker'];tr=Matrix(json.loads((ROOT/'reports/speaker_mount.json').read_text())['world_transform']);inv=np.array(tr.inverted());cup=solids['Speaker_Mount'];local=(np.c_[cup.v,np.ones(len(cup.v))]@inv.T)[:,:3]
    ellipse=(local[:,0]/sm['outer_half_width_x_mm'])**2+(local[:,2]/sm['outer_half_height_z_mm'])**2
    bench=['Body_Upper','Speaker','Speaker_Mount','Speaker_Gasket','Speaker_Insert_-1','Speaker_Insert_1','Speaker_Screw_-1','Speaker_Screw_1'];speaker_rows=[]
    for side in [-1,1]:
        name='Speaker_Screw_'+str(side);bolt=solids[name];bad=[]
        for d in range(31):
            shift=tr.to_3x3()@Vector((0,-d,0));a=Solid(bolt.o,bolt,Matrix.Translation(shift))
            for n in bench:
                if n==name:continue
                v=iv(a,solids[n])
                if v>.01:bad.append({'distance_mm':d,'part':n,'overlap_mm3':v})
        speaker_rows.append({'side':side,'screw_insertion_failures':bad})
    cap=solids['Motor_Retainer'];w=P['wheel_interface'];cap_floor=w['clamp_plate_bottom_z_mm']-w['cap_head_recess_depth_mm']
    cap_rows=[{'id':n,'head_above_plate_bottom_mm':float(a.lo[2])-cap_floor} for n,a in solids.items() if n.startswith('Wheel_Cap_Clamp_Screw_')]
    rc=f['reaction_clamp'];radial={n:float(np.linalg.norm(solids[n].v[:,:2],axis=1).max()) for n in ['Yaw_Reaction_Link','Yaw_Reaction_Clamp_Screw','Yaw_Reaction_Clamp_Nut']}
    reasons={'Yaw_Base':'Changed: straight legs; underside recessed screws and blind inserts','Load_Frame':'Changed: underside head pockets within plate; existing inside drive feet carry wheel loads','Speaker_Mount':'Changed: continuous oval outline; rear recessed screws, no side ears/tool grooves','Body_Upper':'Changed: matching speaker blind bosses inside shell; exterior remains closed','Motor_Retainer':'Changed: simple rectangular central plate; inset screw positions and recessed heads','Drive_Bridge':'Changed: bolt seats move to existing cage corners; bearing wings retained for radial load','Yaw_Reaction_Link':'Changed: round collar; clamp screw/nut recessed within it','Display_Frame':'Retained: exact vendor rear-post seats and local optical-angle seats; side joints inside head outline','Pitch_Cradle':'Retained: bearing/optical support faces and short shell locating tabs; no exterior screwdriver grooves','Pitch_Yoke':'Retained: bilateral bearing seats, real servo-ear seats and cable strain relief; required different functions','Battery_Tray':'Retained: continuous slide rails and direct side retention, no added external screw ear','Body_Lower':'Retained: enclosed shell-seam seats and vertical axle removal slots; slots serve wheel service, not screwdriver relief','Head_Front':'Retained: local internal shell and camera seats; no external screw bosses','Head_Rear':'Retained: inside seam seats, no exterior tabs','Mic_Duct_L':'Retained: independent acoustic tube, no fastener features','Mic_Duct_R':'Retained: independent acoustic tube, no fastener features','Wheel_Hub_L':'Retained: wheel shaft and washer recess inside hub silhouette','Wheel_Hub_R':'Retained: wheel shaft and washer recess inside hub silhouette'}
    reasons['Load_Frame']='Changed: underside bridge head pockets; M1.16 battery side recesses moved inward to close the edge. Dedicated ring/backing checks required.'
    reasons['Battery_Tray']='Changed: both insert and screw pilot sites move with side recesses; existing continuous rails and extraction direction retained.'
    ids=sorted(n for n,a in solids.items() if a.o.get('category')=='PRINTABLE' and a.group!='dock');audit=[{'id':n,'review':reasons.get(n,'UNREVIEWED'),'scope':'Visual/source feature review; not an automatic semantics proof'} for n in ids]
    good=float(ellipse.max())<=1.001 and not any(r['screw_insertion_failures'] for r in speaker_rows) and all(r['head_above_plate_bottom_mm']>=.19 for r in cap_rows) and max(radial.values())<=rc['collar_outer_radius_mm']+.01 and set(ids)==set(reasons)
    data={'speaker_max_outer_ellipse_value':float(ellipse.max()),'speaker_insertion':speaker_rows,'cap_recesses':cap_rows,'reaction_clamp_max_radius_mm':radial,'printed_part_feature_audit':audit,'limits':'No claim that every functional boss should disappear: vendor post seats, bearing housings, shell-inside attachments and separate cable/acoustic features remain. Fits, preload, FDM fatigue, acoustic sealing and global walls are not qualified.'}
    check('other_fastener_feature_cleanup','PASS' if good else 'FAIL','其余打印件安装特征巡检；喇叭、底盖与夹口收进主体轮廓',data,'Actual speaker local-frame silhouette,30mm screw insertion each1mm, cap head heights and radial clamp silhouette; all robot hard printed parts explicitly reviewed.')
    save_json(ROOT/'reports/fastener_cleanup_validation.json',{'revision':P['revision'],'status':'PASS_GEOMETRY_ONLY' if good and ok else 'FAIL','yaw_mounts':rows,**data})

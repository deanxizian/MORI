"""Actual-solid checks for the drawing-based enclosed speaker and shell mounts."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from speaker_geometry import speaker_transform, mount_datums, speaker_envelope
from belly_relayout import relocate


def validate_enclosed_speaker(solids, Solid, iv, check):
    s,m=P['detail_fit']['speaker'],P['speaker_mount'];d=mount_datums();tr=speaker_transform()
    sp,shell,frame=solids['Speaker'],solids['Body_Upper'],solids['Load_Frame']
    local=(np.c_[sp.v,np.ones(len(sp.v))] @ np.array(tr.inverted()).T)[:,:3]
    size=local.max(axis=0)-local.min(axis=0)
    expected=[s['overall_ear_span_mm'],s['depth_mm'],s['box_height_mm']]
    nominal={'local_size_xyz_mm':size.tolist(),'expected_xyz_mm':expected,
             'hole_pitch_mm':s['mount_hole_pitch_mm'],'hole_diameter_mm':s['mount_hole_diameter_mm'],
             'mass_g':s['mass_g'],'mass_tolerance_g':s['mass_tolerance_g'],'source':s['source']}
    check('enclosed_speaker_nominals','PASS' if max(abs(size-np.array(expected)))<.02 else 'FAIL',
          'SP3040箱体42×30×9、总长56与孔距49按图；未标耳厚等按批准估算',nominal,
          'Rigid inverse transform of actual mesh. Documented envelope mixed with explicitly estimated ear/radius details; not measured.')
    attachment={'shell_contact_gap_mm':sp.m.min_gap(shell.m,50),'frame_gap_mm':sp.m.min_gap(frame.m,50),
       'shell_overlap_mm3':iv(sp,shell),'frame_overlap_mm3':iv(sp,frame),'fasteners':2,
       'retired_print_absent':'Speaker_Mount' not in solids,'nominal_front_gasket_mm':m['gasket_thickness_mm']}
    check('speaker_shell_attachment','PASS' if attachment['shell_contact_gap_mm']<.02 and attachment['frame_gap_mm']>1
          and attachment['shell_overlap_mm3']<.01 and attachment['frame_overlap_mm3']<.01 and attachment['retired_print_absent'] else 'FAIL',
          '喇叭原厂耳直锁上壳一体座；取消打印后盖、与内框架无连接',attachment,
          'Actual solid contact, gap and intersection; trial gasket/preload/ear strength not qualified.')
    bench=['Body_Upper','Speaker','Speaker_Gasket','Speaker_Insert_-1','Speaker_Insert_1','Speaker_Screw_-1','Speaker_Screw_1']
    tools=[];insertion=[];caps=[];ear_seats=[]
    for side in [-1,1]:
        x=side*d['mount_abs_x']
        tool=cyl('speaker_driver_probe',(x,d['screw_head_base_y']-m['screw_head_height_mm']-.1-m['tool_length_mm']/2,0),m['tool_diameter_mm']/2,m['tool_length_mm'],'Y')
        relocate(tool,tr);a=Solid(tool)
        bad=[{'part':n,'volume_mm3':v} for n in bench if (v:=iv(a,solids[n]))>.01]
        tools.append({'side':side,'failures':bad});bpy.data.objects.remove(tool,do_unlink=True)
        bolt=solids['Speaker_Screw_'+str(side)];hits=[]
        for distance in range(31):
            move=tr.to_3x3()@Vector((0,-distance,0));a=Solid(bolt.o,bolt,Matrix.Translation(move))
            for n in bench:
                if n==bolt.name:continue
                v=iv(a,solids[n])
                if v>.01:hits.append({'distance_mm':distance,'part':n,'volume_mm3':v})
        insertion.append({'side':side,'screw_insertion_failures':hits})
        start=max(d['pilot_front_y'],d['screw_tip_y']+.5)+.1
        cap=cyl('speaker_blind_cap',(x,start+.6,0),m['insert_pilot_diameter_mm']/2,1.2,'Y');relocate(cap,tr);a=Solid(cap)
        caps.append({'side':side,'missing_mm3':float((a.m-shell.m).volume()),'checked_cap_thickness_mm':1.2})
        bpy.data.objects.remove(cap,do_unlink=True)
        for z in [-3,3]:
            hit=shell.m.ray_cast(list(tr@Vector((x,d['ear_front_y']-.01,z))),list(tr@Vector((x,d['ear_front_y']+1,z))))
            ear_seats.append({'side':side,'local_z_mm':z,'support_gap_mm':float((Vector(hit[0].position)-(tr@Vector((x,d['ear_front_y'],z)))).length) if hit else None})
    check('speaker_shell_tool_access','PASS' if not any(r['failures'] for r in tools) and not any(r['screw_insertion_failures'] for r in insertion) else 'FAIL',
          '上壳拆出后喇叭两枚螺钉可装入并有工具路径',{'tools':tools,'insertion':insertion,'driver_diameter_mm':m['tool_diameter_mm']},
          '30mm smooth screw translation each1mm and straight driver solid; upper shell on bench, handle/fingers not tested.')
    check('speaker_blind_boss_skin','PASS' if all(r['missing_mm3']<.001 for r in caps) and all(r['support_gap_mm'] is not None and r['support_gap_mm']<.02 for r in ear_seats) else 'FAIL',
          '原厂耳有实际支承面，壳内盲孔末端有材料',{'caps':caps,'ear_seat_rays':ear_seats},
          'Actual solid containment behind holes and contact rays; not heat-insert pullout or print-strength qualification.')
    worst=speaker_envelope('speaker_max_tolerance',True);relocate(worst,tr);a=Solid(worst)
    targets={n:b for n,b in solids.items() if n not in ['Speaker','Speaker_Gasket'] and not n.startswith(('Speaker_Screw','Speaker_Insert'))}
    tolerance_hits=[{'part':n,'volume_mm3':v} for n,b in targets.items() if (v:=iv(a,b))>.01]
    bpy.data.objects.remove(worst,do_unlink=True)
    check('speaker_max_box_envelope','PASS' if not tolerance_hits else 'FAIL','箱体最大标注外形公差与周边实体',
          {'maximum_box_xyz_mm':[s['box_width_mm']+s['box_xy_tolerance_mm'],s['depth_mm']+s['depth_tolerance_mm'],s['box_height_mm']+s['box_xy_tolerance_mm']],
           'overall_ear_span_mm':s['overall_ear_span_mm']+s['ear_span_tolerance_mm'],'failures':tolerance_hits},
          'Fixed estimated front/ear datum; increased box dimensions/span. Ear thickness/front-depth and +/-0.5mm hole pitch variation NOT covered; not a complete tolerance fit.')
    vent=box('speaker_rear_vent_keepout',(0,-s['depth_mm']-m['breather_keepout_depth_mm']/2,0),
             (s['box_width_mm'],m['breather_keepout_depth_mm'],s['box_height_mm']))
    relocate(vent,tr);a=Solid(vent)
    vent_hits=[{'part':n,'volume_mm3':v} for n,b in targets.items() if (v:=iv(a,b))>.01]
    bpy.data.objects.remove(vent,do_unlink=True)
    check('speaker_rear_vent_reserve','PASS' if not vent_hits else 'FAIL','未定坐标泄气孔：整个后表面保留2mm开放空间',
          {'rear_face_keepout_depth_mm':m['breather_keepout_depth_mm'],'failures':vent_hits},
          'Conservative full rear-face box; exact hole/gas-flow acoustic requirements not supplied.')
    extraction=[]
    for distance in range(41):
        a=Solid(sp.o,sp,Matrix.Translation(tr.to_3x3()@Vector((0,-distance,0))))
        for n in ['Body_Upper','Speaker_Gasket','Speaker_Insert_-1','Speaker_Insert_1']:
            v=iv(a,solids[n])
            if v>.01:extraction.append({'travel_mm':distance,'part':n,'volume_mm3':v})
    check('speaker_removal_path','PASS' if not extraction else 'FAIL','上壳台面状态下喇叭沿背面40mm抽出路径',
          {'step_mm':1,'travel_mm':40,'failures':extraction},
          'Actual speaker solid, remove both screws and disconnect lead first. Upper shell already removed from robot; no claim for in-body replacement.')
    holes=[];angle=math.radians(s['radial_pitch_deg']);origin=tr@Vector((0,0,0))
    for x in m['grille']['x_mm']:
        for z in [body_z_mm(v) for v in m['grille']['z_from_body_mm']]:
            y=origin.y-(z-origin.z)*math.tan(angle)+.02
            local_point=tr.inverted()@Vector((x,y,z))
            probe=cyl('speaker_grille_air_probe',(x,(y+92)/2,z),.3,92-y,'Y');a=Solid(probe)
            hits=[{'part':n,'volume_mm3':v} for n in ['Body_Upper','Speaker_Gasket'] if (v:=iv(a,solids[n]))>.001]
            long,short=s['diaphragm_outline_xz_mm'];distance=math.hypot(max(abs(local_point.x)-(long-short)/2,0),local_point.z)
            holes.append({'x_mm':x,'z_mm':z,'capsule_distance_mm':distance,'within_assumed_diaphragm':distance<short/2,'failures':hits})
            bpy.data.objects.remove(probe,do_unlink=True)
    check('speaker_front_grille_paths','PASS' if all(not h['failures'] and h['within_assumed_diaphragm'] for h in holes) else 'FAIL',
          '原有15个外壳声孔通路开放，落在图示比例估算的椭圆振膜内',{'probe_diameter_mm':.6,'holes':holes},
          'Actual cylinder-solid intersections through unchanged shell holes; diaphragm perimeter ASSUMED, not acoustic/excursion qualification.')
    check('speaker_physical_audio_fit','BLOCKED','喇叭实物、耳厚/孔距公差配合、线长接头、振膜行程与实际声音待核',
          {'power_rating_W':s['rated_power_W'],'amplifier_output_W':'NOT_VERIFIED','price_CNY':None,
           'hole_radial_clearance_nominal_mm':(s['mount_hole_diameter_mm']-m['screw_diameter_mm'])/2,
           'hole_pitch_tolerance_mm':s['pitch_tolerance_mm'],'ear_estimates':s['field_evidence']['ASSUMED']},
          'M2 in interpreted2mm holes has zero nominal radial clearance; +/-0.5mm hole pitch is not qualified by centered nominal geometry. User authorized estimates, not manufacturing release.')
    data={'revision':P['revision'],'nominal':nominal,'attachment':attachment,'tools':tools,'insertion':insertion,'caps':caps,
          'ear_seats':ear_seats,'max_tolerance_failures':tolerance_hits,'vent_keepout_failures':vent_hits,
          'extraction_failures':extraction,'grille_paths':holes,
          'missing_printed_back_cup':attachment['retired_print_absent']}
    save_json(ROOT/'reports/speaker_replacement_validation.json',data)
    validate_speaker_update_scope(solids,Solid,iv,check)
    return attachment,tools,caps


def validate_speaker_update_scope(solids,Solid,iv,check):
    """Protect other parts and shell features; verify real ear holes/backing."""
    q=P.get('speaker_update',{})
    if not q.get('enabled'):return
    from validate_head_cleanup import geometry_record
    import hashlib
    base=json.loads((PROJECT/q['baseline_geometry']).read_text())
    now={o.name.removeprefix(PREFIX):geometry_record(o) for o in parts()}
    changed=sorted(n for n in now if now[n]!=base['parts'].get(n))
    retired=sorted(set(base['parts'])-set(now));extra=sorted(set(changed)-set(q['changed_existing_ids'])-declared_readiness_changes())
    s,m=P['detail_fit']['speaker'],P['speaker_mount'];tr=speaker_transform();d=mount_datums()
    r=base['Body_Upper'];old=manifold.Manifold(manifold.Mesh64(np.array(r['vertices_mm']),np.array(r['triangles'],dtype=np.uint64)))
    shell=solids['Body_Upper'];delta=(old-shell.m)+(shell.m-old)
    region=box('speaker_only_scope',(0,-.5,0),(64,25,46));relocate(region,tr)
    allowed=Solid(region).m
    if P.get('readiness_completion',{}).get('rear_switch',{}).get('remove_shell_opening'):
        rz=json.loads((ROOT/'reports/rear_interface_geometry.json').read_text())['switch_actuator_axis_z_mm']
        allowed+=manifold.Manifold.cube([6.1,30.1,3.3],True).translate([0,-76,rz])
    outside=max(0,(delta-allowed).volume());bpy.data.objects.remove(region,do_unlink=True)
    ear_rows=[]
    for sign in [-1,1]:
        x=sign*d['mount_abs_x'];cy=(d['ear_front_y']+d['ear_rear_y'])/2
        probe=cyl('speaker_bore_probe',(x,cy,0),.95,s['ear_thickness_mm']+1,'Y');relocate(probe,tr)
        hole=iv(Solid(probe),solids['Speaker']);bpy.data.objects.remove(probe,do_unlink=True)
        patch=ring('speaker_ear_head_backing',(x,d['ear_rear_y']+.12,0),1.8,1.1,.2,'Y');relocate(patch,tr)
        missing=max(0,(Solid(patch).m-solids['Speaker'].m).volume());bpy.data.objects.remove(patch,do_unlink=True)
        ear_rows.append({'side':sign,'hole_obstructed_mm3':hole,'head_backing_missing_mm3':missing})
    single=sum(v.volume()>.01 for v in shell.m.decompose())==1
    source_ok=hashlib.sha256((PROJECT/s['source']).read_bytes()).hexdigest()==q['source_sha256']
    # Solid-volume tests can miss coplanar zero-volume Boolean remnants.
    # Inspect actual render triangles across the gasket's clear aperture too.
    gasket=solids['Speaker_Gasket']
    local_gasket=(np.c_[gasket.v,np.ones(len(gasket.v))] @ np.array(tr.inverted()).T)[:,:3]
    centers=local_gasket[gasket.f].mean(axis=1)
    length,height=m['gasket_inner_xz_mm'];r=height/2
    distances=np.hypot(np.maximum(np.abs(centers[:,0])-(length-height)/2,0),centers[:,2])
    remnants=int(np.sum(distances<r-.05))
    ok=not extra and not (set(retired)-declared_readiness_retirements()) and len(now)==len(base['parts'])+len(P.get('readiness_completion',{}).get('new_ids',[]))-len(declared_readiness_retirements()) and outside<.01 and single and source_ok and remnants==0 and all(r['hole_obstructed_mm3']<.001 and r['head_backing_missing_mm3']<.001 for r in ear_rows)
    result={'revision':P['revision'],'status':'PASS' if ok else 'FAIL','baseline_revision':base['revision'],
            'changed_parts':changed,'unexpected_changes':extra,'retired':retired,'part_count_delta':len(now)-len(base['parts']),
            'shell_change_outside_speaker_region_mm3':outside,'shell_connected':single,'source_hash_matches':source_ok,
            'ear_holes_and_head_backing':ear_rows,'new_prints':0,'new_fasteners':0,'physical_fit':'BLOCKED','strength':'NOT_TESTED',
            'gasket_triangles_inside_clear_aperture':remnants,'aperture_edge_exclusion_mm':.05,
            'preserved':'All non-speaker part geometry/matrices, shell exterior away from the local internal speaker seats, existing grille and electronics positions.'}
    save_json(ROOT/'reports/speaker_SP3040_scope.json',result)
    check('speaker_SP3040_scope',result['status'],'仅替换喇叭及其壳内安装接口；无新增打印件或五金',result,
          'All-part geometry/matrix fingerprints vs immutableM1.36, local shell solid difference, actual ear bore and annular screw-head backing probes.')


if __name__ == '__main__':
    from validate import Solid, intersect_volume, check, CHECKS
    bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections();assembled()
    solids={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.get('group')!='dock'}
    validate_enclosed_speaker(solids,Solid,intersect_volume,check)
    save_json(ROOT/'reports/speaker_local_checks.json',CHECKS)

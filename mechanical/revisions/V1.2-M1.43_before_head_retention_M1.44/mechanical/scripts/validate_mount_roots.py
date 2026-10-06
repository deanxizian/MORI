"""M1.40: actual CAM mounting roots and exact local-change scope."""
from common import *
from validate_head_cleanup import geometry_record

def cam_change_region():
    q=P['assembly_completion']['cam_mount'];c=P['waveshare_detail']['cam'];h=P['head_print_cleanup']
    _,y,z=P['layout']['cam_board_center_from_head_mm'];z+=D['head_z']
    lo=np.array([-q['rear_plate_width_mm']/2-.01,h['cradle_rear_y_mm']-.01,D['head_z']+h['cradle_bottom_from_head_mm']-.01])
    hi=np.array([q['rear_plate_width_mm']/2+.01,y-c['pcb_thickness_mm']/2-q['pad_surface_extra_mm']+.01,z+c['hole_grid_mm']/2+q['top_margin_mm']+.01])
    return manifold.Manifold.cube((hi-lo).tolist()).translate(lo.tolist())

def validate_mount_roots(solids,Solid,iv,check):
    s=P.get('mount_root_cleanup',{})
    if not s.get('enabled'):return
    base=json.loads((PROJECT/s['baseline_geometry']).read_text());now={o.name.removeprefix(PREFIX):geometry_record(o) for o in parts()}
    changed=sorted(n for n in now if n in base['parts'] and now[n]!=base['parts'][n]);added=sorted(set(now)-set(base['parts']));retired=sorted(set(base['parts'])-set(now));rows=[];failed=[]
    def emit(n,ok,summary,data):
        if not ok:failed.append(n)
        check('mount_roots_'+n,'PASS' if ok else 'FAIL',summary,data,'Actual current closed meshes vs immutable M1.39; no print/strength qualification.')
    expected=set(s['changed_existing_ids'])|declared_display_frame_changes()
    scope=dict(changed=changed,added=added,retired=retired,expected=sorted(expected),later_changes_checked_separately=sorted(declared_display_frame_changes()))
    emit('scope',set(changed)==expected and not added and not retired,'CAM固定座头托范围核对；后续显示架简化另做精确检查，硬件保持',scope)
    q=P['assembly_completion']['cam_mount'];c=P['waveshare_detail']['cam'];h=P['head_print_cleanup'];x,y,z=P['layout']['cam_board_center_from_head_mm'];z+=D['head_z'];rear=h['cradle_rear_y_mm'];wall=h['cradle_wall_mm'];front=y-c['pcb_thickness_mm']/2-q['pad_surface_extra_mm'];side=q['support_side_mm'];old=base['Pitch_Cradle'];old=manifold.Manifold(manifold.Mesh64(np.array(old['vertices_mm']),np.array(old['triangles'],dtype=np.uint64)));new=solids['Pitch_Cradle'].m
    def block(lo,hi):return manifold.Manifold.cube((np.array(hi)-lo).tolist()).translate(lo)
    region=cam_change_region()
    if P.get('interface_completion',{}).get('enabled'):
        from interface_completion import change_regions
        region+=change_regions()['Pitch_Cradle']
    plus=new-old;minus=old-new
    changes=dict(added_mm3=max(0,plus.volume()),removed_mm3=max(0,minus.volume()),outside_region_mm3=max(0,(plus-region).volume())+max(0,(minus-region).volume()),positive_components=sum(m.volume()>.001 for m in new.decompose()))
    emit('local_solid',changes['outside_region_mm3']<.02 and changes['positive_components']==1,'改动局限于原CAM背板/座范围，头托仍为单一连续实体',changes)
    for i,(u,v) in enumerate(((u,v) for u in [-1,1] for v in [-1,1])):
        xx=x+u*c['hole_grid_mm']/2;zz=z+v*c['hole_grid_mm']/2
        # Complete seat footprint, including the root centre: the blind pilot
        # stops before this structural backing plane.
        p=block([xx-side/2,rear+wall-.45,zz-side/2],[xx+side/2,rear+wall-.3,zz+side/2]);missing=max(0,(p-new).volume())
        rows.append(dict(id='CAM_'+str(i),root_footprint_mm2=side*side,root_plane_y_mm=rear+wall,missing_root_mm3=missing,material_fraction=max(0,1-missing/p.volume())))
    emit('full_backing',all(r['missing_root_mm3']<.005 for r in rows),'CAM四座根部整个矩形截面均有后板承接',rows)
    # Existing positional and fastener hashes are included in the exact scope;
    # these distances additionally expose the small photo-dependent clearances.
    near=[]
    for n in ['CAM_Mainboard','Onboard_MIC_L','Onboard_MIC_R','Head_Rear','Head_Front']:
        near.append(dict(id=n,intersection_mm3=iv(solids['Pitch_Cradle'],solids[n]),gap_search_capped5mm=new.min_gap(solids[n].m,5)))
    emit('local_fit',all(r['intersection_mm3']<.01 for r in near),'加宽背板及方座与板载器件、双麦、头壳未检出穿插',near)
    report=dict(revision=P['revision'],status='FAIL' if failed else 'PASS',failed=failed,scope=scope,solid_difference=changes,full_root_rows=rows,local_interfaces=near,option=s['selected_option'],new_prints=0,new_fasteners=0,physical_fit='NOT_TESTED',strength='NOT_TESTED',acoustic_performance='NOT_TESTED',mic_paths_report='microphone_open_path.json',assembly_report='assembly_completion_validation.json',motion_report='head_motion.json',manufacturing_release=False)
    save_json(ROOT/'reports/mount_root_validation.json',report)

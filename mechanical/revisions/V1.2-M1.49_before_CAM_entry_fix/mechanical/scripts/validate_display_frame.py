"""Exact M1.40 scope, accepted-candidate match and flush support geometry."""
from common import *
from validate_head_cleanup import geometry_record
from display_frame_simplification import dimensions,change_region,block,cylinder

def validate_display_frame(solids,Solid,iv,check):
    s=P.get('display_frame_simplification',{})
    if not s.get('enabled'):return
    base=json.loads((PROJECT/s['baseline_geometry']).read_text())
    accepted=json.loads((PROJECT/s['approved_geometry']).read_text())
    now={o.name.removeprefix(PREFIX):geometry_record(o) for o in parts()};failed=[];report={}
    def emit(key,ok,label,data):
        report[key]=data
        if not ok:failed.append(key)
        check('display_frame_'+key,'PASS' if ok else 'FAIL',label,data,
              'Current actual closed geometry compared with immutable M1.40 and the user-approved candidate. No physical fit/strength claim.')
    changed=sorted(n for n in now if n in base['parts'] and now[n]!=base['parts'][n])
    added=sorted(set(now)-set(base['parts']));retired=sorted(set(base['parts'])-set(now))
    emit('scope',set(changed)==(set(s['changed_existing_ids'])|declared_interface_changes())-declared_retention_additions() and set(added)==declared_retention_additions() and not retired,
         '只修改Display Frame，所有硬件、中央立柱基准和其他零件保持',
         dict(changed=changed,subsequent_interface_changes=sorted(declared_interface_changes()),added=added,retired=retired,baseline=base['revision']))
    def shape(r):return manifold.Manifold(manifold.Mesh64(np.array(r['vertices_mm']),np.array(r['triangles'],dtype=np.uint64)))
    from validate_camera_cam import prior_solid
    old=shape(base['Display_Frame']);target=shape(accepted['Display_Frame']);m=prior_solid('Display_Frame',solids['Display_Frame'].m)
    plus=m-old;minus=old-m;region=change_region();later=manifold.Manifold()
    if P.get('assembly_issue_fixes',{}).get('enabled'):
        from assembly_issue_fixes import change_regions
        later=change_regions()['Display_Frame'];region+=later
    # The visual study redundantly re-cut the old64-segment bores with96
    # segments. Production preserves the original interfaces instead. Match
    # the accepted exterior AND independently require those source bore/seat
    # regions to remain unchanged within the existing Boolean tolerance.
    mask=manifold.Manifold();q=P['readiness_completion']['lcd']
    for row in json.loads((ROOT/'reports/readiness_geometry.json').read_text())['LCD']:
        axis=np.array(row['axis']);p=np.array(row['post_face_mm']);f=np.array(row['head_bearing_mm'])
        mask+=cylinder(p-axis*15,axis,q['clearance_radius_mm']+.01,60)
        mask+=cylinder(f-axis*20,axis,q['spotface_radius_mm']+.01,20.01)
    delta=dict(added_mm3=max(0,plus.volume()),removed_mm3=max(0,minus.volume()),
        outside_approved_region_mm3=max(0,(plus-region).volume())+max(0,(minus-region).volume()),
        difference_from_accepted_mm3=max(0,(m-target).volume())+max(0,(target-m).volume()),
        difference_from_accepted_outside_lcd_cutters_mm3=max(0,((m-target)-mask-later).volume())+max(0,((target-m)-mask-later).volume()),
        original_LCD_interface_difference_mm3=max(0,(plus^mask).volume())+max(0,(minus^mask).volume()),
        mesh_cleanup_tolerance_mm=P['mesh']['boolean_simplify_tolerance_mm'],
        positive_components=sum(x.volume()>.001 for x in solids['Display_Frame'].m.decompose()))
    emit('accepted_solid',delta['outside_approved_region_mm3']<.02 and delta['difference_from_accepted_outside_lcd_cutters_mm3']<.02 and delta['original_LCD_interface_difference_mm3']<.02 and delta['positive_components']==1,
         '平直U形外轮廓匹配确认方案，原LCD孔面保留，变化局限于下方连接',delta)
    d=dimensions();planes=[]
    for sign in [-1,1]:
        x0,x1=sorted([sign*d['earinner'],sign*d['outer']])
        for name,probe in [('front',block([x0+.05,d['front']-.2,d['bot']+.05],[x1-.05,d['front']-.05,d['join1']-.05])),
                           ('bottom',block([x0+.05,d['earback']+.05,d['bot']+.05],[x1-.05,d['front']-.05,d['bot']+.2]))]:
            planes.append(dict(side=sign,plane=name,missing_material_mm3=max(0,(probe-m).volume())))
    film=[]
    for sign in [-1,1]:
        x0,x1=sorted([sign*(d['mast_half']+.1),sign*(d['inner']-.1)])
        probe=block([x0,d['oldrear']+.1,d['top']-.009],[x1,d['rear']-.1,d['top']+.009])
        film.append(dict(side=sign,remaining_mm3=max(0,(probe^m).volume())))
    emit('flush_faces',all(r['missing_material_mm3']<.005 for r in planes) and all(r['remaining_mm3']<.001 for r in film),
         '侧耳前面和底边完整齐平，旧横梁数值薄片已清除',dict(plane_probes=planes,old_film=film,front_y_mm=d['front'],bottom_z_mm=d['bot']))
    report.update(revision=P['revision'],status='FAIL' if failed else 'PASS',failed=failed,
        new_prints=0,new_fasteners=0,central_mast='M1.43 legacy cavity filled; optical datums unchanged' if P.get('assembly_issue_fixes',{}).get('enabled') else 'UNCHANGED',hardware_poses='UNCHANGED',
        motion_evidence='head_motion.json',LCD_fastening_evidence='readiness_validation.json',
        side_nut_evidence='head_cleanup_validation.json',strength='NOT_TESTED',manufacturing_release=False)
    save_json(ROOT/'reports/display_frame_validation.json',report)

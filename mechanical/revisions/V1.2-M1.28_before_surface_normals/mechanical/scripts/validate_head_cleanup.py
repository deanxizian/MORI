"""Current head print solids, retained datums and lateral nut installation."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
import hashlib

IDS = ['Pitch_Cradle','Display_Frame','Pitch_Yoke']


def geometry_record(o):
    o.data.calc_loop_triangles()
    v=np.array([tuple(o.matrix_world@p.co) for p in o.data.vertices],dtype=np.float64)
    f=np.array([tuple(t.vertices) for t in o.data.loop_triangles],dtype=np.int32)
    v=v.round(5);v[v==0]=0
    h=hashlib.sha256();h.update(v.tobytes());h.update(f.tobytes())
    local=np.array([tuple(p.co) for p in o.data.vertices],dtype=np.float64).round(5);local[local==0]=0
    lh=hashlib.sha256();lh.update(local.tobytes());lh.update(f.tobytes())
    return {'geometry_sha256':h.hexdigest(),'local_mesh_sha256':lh.hexdigest(),
            'world_matrix':list(map(list,o.matrix_world)),
            'group':o.get('group'),'category':o.get('category')}


def validate_head_cleanup(solids,Solid,iv,check):
    if not P.get('head_print_cleanup',{}).get('enabled'):return
    config=P['head_print_cleanup'];report=json.loads((ROOT/'reports/head_print_cleanup.json').read_text())
    before=json.loads((ROOT/'studies/head_cleanup/baseline_geometry.json').read_text())
    now={o.name.removeprefix(PREFIX):geometry_record(o) for o in parts()}
    changed=[n for n in now if n not in before['parts'] or now[n]!=before['parts'][n]]
    allowed_nuts=[f'Face_Joint_{sign}_{rel:.1f}_Nut' for sign in [-1,1] for rel in config['face_joint_z_from_head_mm']]
    subsequent_body_changes=set(P.get('drive_print_cleanup',{}).get('changed_print_ids',[]))
    retired=sorted(set(before['parts'])-set(now));unexpected=sorted(set(changed)-set(report['changed_prints'])-set(allowed_nuts)-subsequent_body_changes)
    nut_rigid=[]
    for sign in [-1,1]:
        for rel in config['face_joint_z_from_head_mm']:
            n=f'Face_Joint_{sign}_{rel:.1f}_Nut';diff=np.array(now[n]['world_matrix'])-np.array(before['parts'][n]['world_matrix'])
            expected=np.zeros((4,4));expected[0,3]=sign*(config['face_nut_abs_x_mm']-config['face_nut_previous_abs_x_mm'])
            nut_rigid.append(bool(now[n]['local_mesh_sha256']==before['parts'][n]['local_mesh_sha256'] and np.max(np.abs(diff-expected))<.001))
    preserved=not unexpected and not retired and all(nut_rigid)
    check('head_cleanup_preserved_hardware','PASS' if preserved else 'FAIL',
          '两件打印支架平面化，四枚现有螺母仅内移；光学、舵机、PCB及U托保持不变',
          {'geometry_changed':changed,'unexpected_changed':unexpected,'removed':retired,
           'nut_geometry_unchanged_only_declared_translation':nut_rigid,
           'later_body_cleanup_checked_against_M1_25_separately':sorted(subsequent_body_changes),
           'method':'Per-object world vertices rounded1e-5mm plus triangle-index SHA256; includes every unchanged purchased/placeholder/printed part.'})
    connected=[]
    for n in IDS:
        a=solids[n];pieces=[m for m in a.m.decompose() if abs(m.volume())>.01]
        connected.append({'id':n,'positive_components':sum(m.volume()>0 for m in pieces),
                          'cavity_components':sum(m.volume()<0 for m in pieces),
                          'volume_mm3':a.m.volume(),'minimum_gap_to_shells_mm':min(a.m.min_gap(solids[k].m,10) for k in ['Head_Front','Head_Rear'])})
    check('head_cleanup_single_solids','PASS' if all(r['positive_components']==1 and r['cavity_components']==0 for r in connected) else 'FAIL',
          '三个大件各为连续封闭实体，无悬空碎片',connected,'Triangle-solid decomposition; not structural certification.')
    # Inspect both real mesh surfaces through the former raised-pad area.
    # These rays must see the same outer/inner planes away from functional holes.
    tree=solids['Pitch_Cradle'].bvh();wall_rows=[];wall_bad=[]
    outer=config['cradle_outer_half_width_mm'];inner=outer-config['cradle_wall_mm']
    for sign in [-1,1]:
        for y in [-18,-12,-6,0,6,12,18]:
            for rel in [-8,-4,4,10,12]:
                z=D['head_z']+rel
                a=tree.ray_cast(Vector((sign*60,y,z)),Vector((-sign,0,0)),40)[0]
                b=tree.ray_cast(Vector((sign*30,y,z)),Vector((sign,0,0)),30)[0]
                row={'side':sign,'y_mm':y,'z_relative_mm':rel,
                     'outer_x_mm':None if a is None else float(a.x),
                     'inner_x_mm':None if b is None else float(b.x)}
                wall_rows.append(row)
                if a is None or b is None or abs(a.x-sign*outer)>.002 or abs(b.x-sign*inner)>.002:wall_bad.append(row)
    support=[]
    for sign in [-1,1]:
        probe=ring('shaft_wall_probe',(sign*(inner+outer)/2,0,D['head_z']),6,2.8,config['cradle_wall_mm']-.2,'X')
        a=Solid(probe);missing=max(0,(a.m-solids['Pitch_Cradle'].m).volume())
        support.append({'side':sign,'probe_thickness_mm':config['cradle_wall_mm']-.2,'missing_mm3':missing})
        SOLIDS.pop(probe.name,None);bpy.data.objects.remove(probe,do_unlink=True)
    mast=[]
    for sign in [-1,1]:
        # Continuous material near both outer edges; stops below the real
        # camera package pocket. LCD screw bores are on the centre/other rails.
        probe=box('mast_edge_probe',(sign*(config['face_mast_width_mm']/2-.5),config['face_mast_y_mm'],D['head_z']+15),(.6,2.6,40))
        a=Solid(probe);missing=max(0,(a.m-solids['Display_Frame'].m).volume())
        mast.append({'side':sign,'z_range_from_head_mm':[-5,35],'missing_mm3':missing})
        SOLIDS.pop(probe.name,None);bpy.data.objects.remove(probe,do_unlink=True)
    planar_ok=not wall_bad and all(r['missing_mm3']<.005 for r in support+mast)
    check('head_planar_walls','PASS' if planar_ok else 'FAIL','头托两面平齐、轴孔承压环连续；相机立柱两侧等宽',
          {'surface_rays':wall_rows,'surface_failures':wall_bad,'shaft_wall_probes':support,'mast_edge_probes':mast},
          'Actual mesh ray casts and solid material subtraction. Nominal4.5mm walls; shell lugs, mounting holes and camera pocket excluded. No load or print-strength qualification.')
    # Nut travels from the open inner side of the face return before fitting
    # the fork to the cradle. Screws and all optical electronics absent on bench.
    failures=[];minimum_web=[]
    for sign in [-1,1]:
        for rel in config['face_joint_z_from_head_mm']:
            n=f'Face_Joint_{sign}_{rel:.1f}_Nut';nut=solids[n]
            for travel in np.arange(0,10.01,.5):
                a=Solid(nut.o,nut,Matrix.Translation((-sign*float(travel),0,0)))
                vol=iv(a,solids['Display_Frame'])
                if vol>.01:failures.append({'nut':n,'inward_travel_mm':float(travel),'overlap_mm3':vol})
            outer=config['face_nut_abs_x_mm']+config['face_nut_pocket_depth_mm']/2
            # Verify1.8mm inside the nominal2mm nut-bearing wall, not a surface.
            thick=config['face_nut_backing_probe_mm']
            probe=ring('head_joint_web_probe',(sign*(outer+.1+thick/2),config['face_joint_y_mm'],D['head_z']+rel),1.9,1.25,thick,'X')
            a=Solid(probe);missing=max(0,(a.m-solids['Display_Frame'].m).volume())
            minimum_web.append({'side':sign,'z_from_head_mm':rel,'tested_backing_mm':thick,'missing_material_mm3':missing})
            SOLIDS.pop(probe.name,None);bpy.data.objects.remove(probe,do_unlink=True)
    ok=not failures and all(r['missing_material_mm3']<.005 for r in minimum_web)
    check('head_face_nut_insertion','PASS' if ok else 'FAIL','屏幕叉架螺母从内侧装入；孔后实际承压材料仍连续',
          {'failures':failures,'webs':minimum_web,'travel_mm':10,'step_mm':.5,
           'prerequisites':'Fork alone on bench, no screws/electronics; install nuts before lateral face joints.'},
          'Actual metal-nut versus printed-solid intersections,0.5mm finite samples; local material probe. No hand/preload/print-strength qualification.')
    report.update(status='PASS' if preserved and ok and planar_ok and all(r['positive_components']==1 and r['cavity_components']==0 for r in connected) else 'FAIL',
                  changed_geometry=changed,connected_solids=connected,nut_insertion_failures=failures,nut_backing=minimum_web,
                  planar_checks={'surface_failures':wall_bad,'shaft_wall_probes':support,'mast_edge_probes':mast},
                  global_checks='reports/validation.json; full motion, wires, FOV, shell fit and service paths are validated separately')
    save_json(ROOT/'reports/head_cleanup_validation.json',report)
    if config.get('cradle_rear_corner_chamfer_mm',0) or config.get('cradle_rear_profile')=='folded_u':
        validate_rear_corners(solids,check)


def validate_rear_corners(solids,check):
    """Check the two edited physical corners, keeping all other parts fixed."""
    s=P['head_print_cleanup'];base=json.loads((PROJECT/s['corner_baseline_geometry']).read_text())
    now={o.name.removeprefix(PREFIX):geometry_record(o) for o in parts()}
    changed=sorted(n for n in now if now[n]!=base['parts'].get(n))
    removed=sorted(set(base['parts'])-set(now))
    only_cradle=changed==['Pitch_Cradle'] and not removed
    shape=solids['Pitch_Cradle'].m;x=s['cradle_outer_half_width_mm'];rear=s['cradle_rear_y_mm'];c=s.get('cradle_rear_corner_chamfer_mm',0)
    folded=s.get('cradle_rear_profile')=='folded_u'
    if folded:
        xr=s['cradle_fold_rear_abs_x_mm'];ys=s['cradle_side_rear_y_mm']
        run=x-xr;rise=ys-rear;length=math.hypot(run,rise)
    rows=[];bad=[]
    for sign in [-1,1]:
        normal=np.array([sign*rise,-run,0],float)/length if folded else np.array([sign,-1,0],float)/math.sqrt(2)
        tangent=np.array([sign*run,rise,0],float)/length if folded else np.array([sign,1,0],float)/math.sqrt(2)
        for rel in [-8,0,12]:
            for along in ([-length*.3,-length*.15,0,length*.15,length*.3] if folded else [-.5,0,.5]):
                center=np.array([sign*(x+xr)/2,(rear+ys)/2,D['head_z']+rel]) if folded else np.array([sign*(x-c/2),rear+c/2,D['head_z']+rel])
                center+=tangent*along
                hits=shape.ray_cast((center+normal*10).tolist(),(center-normal*12).tolist())
                unique=[]
                for h in hits:
                    a=np.array(h.position)
                    if not unique or np.linalg.norm(a-unique[-1])>1e-4:unique.append(a)
                thickness=float(np.linalg.norm(unique[1]-unique[0])) if len(unique)>=2 else None
                plane_error=abs(float(np.dot(unique[0]-center,normal))) if unique else None
                row={'side':sign,'z_from_head_mm':rel,'along_face_mm':along,'normal_wall_mm':thickness,'outer_plane_error_mm':plane_error};rows.append(row)
                if thickness is None or thickness<s['cradle_wall_mm']-.002 or plane_error>.002:bad.append(row)
    result={'revision':P['revision'],'baseline_revision':s['corner_baseline_revision'],
            'changed_geometry':changed,'unexpected_changes':sorted(set(changed)-{'Pitch_Cradle'}),'removed':removed,
            'profile':s.get('cradle_rear_profile','small_outer_chamfers'),'nominal_adjacent_wall_mm':s['cradle_wall_mm'],
            'corner_rays':rows,'ray_failures':bad,'minimum_sampled_corner_normal_wall_mm':min(r['normal_wall_mm'] for r in rows if r['normal_wall_mm'] is not None),
            'method':'World vertex/triangle hashes against the declared immutable baseline for all parts; actual solid intersections along diagonal wall normals at3heights and distributed face stations per corner. Existing side-wall, shaft-backing and connectivity tests also apply.',
            'physical_strength':'NOT_TESTED','status':'PASS' if only_cradle and not bad else 'FAIL'}
    if folded:
        reference_path=s['fold_profile_reference'].split('#')[0]
        reference=json.loads((PROJECT/reference_path).read_text())['structure']['simple_modules']['head_flat']
        matches=all(abs(actual-reference[key])<1e-9 for key,actual in [('outer_half_width_mm',x),('rear_chamfer_x_mm',xr),('rear_y_mm',rear),('side_rear_y_mm',ys),('front_y_mm',s['cradle_front_y_mm'])])
        result.update(outer_diagonal_length_mm=length,fold_xy_run_rise_mm=[run,rise],rear_straight_width_mm=2*xr,
                      outer_profile_matches_M1_24=matches,reference=s['fold_profile_reference'],
                      outer_fold_endpoints_xy_mm=[[[sign*xr,rear],[sign*x,ys]] for sign in [-1,1]])
        if not matches:result['status']='FAIL'
    else:result.update(chamfer_leg_mm=c,chamfer_angle_deg=45)
    title='头托恢复双侧大折角，斜壁等厚及其余零件原位核对' if folded else f'头托后侧双角{c:g}mm倒角，实际角部壁厚及其他部件原位核对'
    check('head_rear_corner_profile',result['status'],title,result,
          'Local nominal mesh checks, not a global minimum-wall or print-strength certificate.')
    save_json(ROOT/'reports/head_corner_validation.json',result)


if __name__=='__main__':
    import sys
    load_collections()
    # Saved hidden collections otherwise retain unevaluated parent transforms.
    # Match the normal validator and deterministic-rebuild inspection context.
    for n in ['DOCK','COUPONS','DATUMS','KEEP_OUT']:COLS[n].hide_viewport=False
    assembled();bpy.context.view_layer.update()
    target=Path(sys.argv[sys.argv.index('--')+1])
    save_json(target,{'source_blend':bpy.data.filepath,'source_sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),
                      'parts':{o.name.removeprefix(PREFIX):geometry_record(o) for o in parts()}})

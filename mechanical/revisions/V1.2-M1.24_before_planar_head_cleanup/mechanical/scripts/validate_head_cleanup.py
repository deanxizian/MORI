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
    retired=sorted(set(before['parts'])-set(now));unexpected=sorted(set(changed)-set(IDS)-set(allowed_nuts))
    nut_rigid=[]
    for sign in [-1,1]:
        for rel in config['face_joint_z_from_head_mm']:
            n=f'Face_Joint_{sign}_{rel:.1f}_Nut';diff=np.array(now[n]['world_matrix'])-np.array(before['parts'][n]['world_matrix'])
            expected=np.zeros((4,4));expected[0,3]=sign*(config['face_nut_abs_x_mm']-config['face_nut_previous_abs_x_mm'])
            nut_rigid.append(bool(now[n]['local_mesh_sha256']==before['parts'][n]['local_mesh_sha256'] and np.max(np.abs(diff-expected))<.001))
    preserved=not unexpected and not retired and all(nut_rigid)
    check('head_cleanup_preserved_hardware','PASS' if preserved else 'FAIL',
          '三件打印支架简化，四枚现有螺母仅内移；光学、舵机、PCB及其他实体不变',
          {'geometry_changed':changed,'unexpected_changed':unexpected,'removed':retired,
           'nut_geometry_unchanged_only_declared_translation':nut_rigid,
           'method':'Per-object world vertices rounded1e-5mm plus triangle-index SHA256; includes every unchanged purchased/placeholder/printed part.'})
    connected=[]
    for n in IDS:
        a=solids[n];pieces=[m for m in a.m.decompose() if abs(m.volume())>.01]
        connected.append({'id':n,'positive_components':sum(m.volume()>0 for m in pieces),
                          'cavity_components':sum(m.volume()<0 for m in pieces),
                          'volume_mm3':a.m.volume(),'minimum_gap_to_shells_mm':min(a.m.min_gap(solids[k].m,10) for k in ['Head_Front','Head_Rear'])})
    check('head_cleanup_single_solids','PASS' if all(r['positive_components']==1 and r['cavity_components']==0 for r in connected) else 'FAIL',
          '三个大件各为连续封闭实体，无悬空碎片',connected,'Triangle-solid decomposition; not structural certification.')
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
    report.update(status='PASS' if preserved and ok and all(r['positive_components']==1 and r['cavity_components']==0 for r in connected) else 'FAIL',
                  changed_geometry=changed,connected_solids=connected,nut_insertion_failures=failures,nut_backing=minimum_web,
                  global_checks='reports/validation.json; full motion, wires, FOV, shell fit and service paths are validated separately')
    save_json(ROOT/'reports/head_cleanup_validation.json',report)


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

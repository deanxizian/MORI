"""Fresh core checks after removal of four bounded Head_Front remnants.

Historical tests are linked separately, never relabeled as executed in this run.
The current core needs no unpublished historical .blend file.
"""
from common import *
import hashlib,time
from review_geometry_fingerprint import record

def run_current():
    import validate as v
    start=time.time();bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections()
    for name in ['DATUMS','DOCK','KEEP_OUT','COUPONS']:COLS[name].hide_viewport=False
    assembled();bpy.context.view_layer.update();v.CHECKS.clear()
    ss={o.name.removeprefix(PREFIX):v.Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']}
    path=ROOT/'input_assets/M1_52_review_baseline.json';baseline=json.loads(path.read_text())
    now={n:record(s.v,s.f.tolist()) for n,s in ss.items()}
    if set(now)!=set(baseline['parts']):raise RuntimeError('Review repair changed the assembly inventory')
    changed=[]
    for name,row in now.items():
        before=baseline['parts'][name]
        if row['exact_sha256']==before['exact_sha256']:continue
        if name=='Head_Front':
            assert row['components']==1 and row['triangles']==before['main_triangles'] and row['exact_sha256']==before['main_exact_sha256']
        elif name=='Display_Frame':
            # Recorded rebuild roundoff at one vertex (~0.000002 mm), no design change.
            assert row['triangles']==before['triangles'] and row['rounded_0p0001mm_sha256']==before['rounded_0p0001mm_sha256']
        elif name=='Display_PCB':
            receipt=json.loads((ROOT/'input_assets/display_rebuild_receipt.json').read_text())
            assert before['exact_sha256']==receipt['original_world_triangles_sha256'] and row['exact_sha256']==receipt['rebuilt_world_triangles_sha256']
            assert receipt['bounds_identical'] and receipt['same_transform'] and receipt['added_volume_mm3']+receipt['removed_volume_mm3']<0.00001
        else:raise RuntimeError('Unreviewed geometry change: '+name)
        changed.append(name)
    v.check('review_repair_scope','PASS','仅清理头前壳的4个极小游离碎片；其余设计几何保持',{'changed':changed,'parts':len(now),'baseline':str(path.relative_to(PROJECT)),'baseline_sha256':hashlib.sha256(path.read_bytes()).hexdigest()},'Canonical world triangles; Head_Front main component exact, Display_Frame has documented float rounding; Display_PCB is the exact reviewed re-triangulation with <0.00001 mm3 symmetric difference. No dimensions or hardware transforms changed.')
    v.actual_checks(ss);v.geometry_checks(ss);v.camera_checks(ss)
    v.access_checks(ss,core_only=True);v.mass_checks(ss);v.v12_checks(ss)
    v.check('historical_extended_checks','NOT_TESTED','历史完整装配、走线与局部试件检查本次未重跑；保留原始日期和输入边界',baseline['historical_validation'],'Current full-body collisions, motion, topology, optics and core access above are fresh. Historical tests are not counted as current PASS.')
    result={'revision':P['revision'],'review_revision':'2026-10-07-R1','source_blend_sha256':hashlib.sha256((ROOT/'mori_v1_2.blend').read_bytes()).hexdigest(),'checks':v.CHECKS,'counts':{s:sum(c['status']==s for c in v.CHECKS) for s in ['PASS','FAIL','NOT_TESTED','BLOCKED','NOT_APPLICABLE']},'elapsed_s':time.time()-start,'historical_superseded_checks':[],'physical_validation':'NOT_TESTED','manufacturing_release':False}
    save_json(ROOT/'reports/validation.json',result);print('REVIEW_VALIDATION_COMPLETE',result['counts'],flush=True)
    if result['counts']['FAIL']:raise RuntimeError('Current geometry checks failed')
    return result

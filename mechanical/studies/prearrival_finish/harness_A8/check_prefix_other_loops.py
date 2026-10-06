"""Check coexistence with the two earlier yaw-group allocations only."""
from pathlib import Path
import json,hashlib,math
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree
HERE=Path(__file__).resolve().parent;OUT=HERE/'body_prefix_v2';ROOT=HERE.parents[3]
motion=json.loads((OUT/'body_to_yaw_motion.json').read_text());curves=np.load(OUT/'body_to_yaw_curves.npz')
loops_file=HERE.parent/'head_harness/split_planar_loops_refined.json'
loops=json.loads(loops_file.read_text());assert motion['status']=='PASS' and motion['source_blend_sha256']==loops['source_blend_sha256']
rows=[]
for group in loops['groups']:
    if group['status']!='PASS':continue
    for pose in group['selected']['poses']:
        p=np.array(pose['curve_mm']);tree=KDTree(len(p))
        for i,x in enumerate(p):tree.insert(Vector(x),i)
        tree.balance();ds=float(np.linalg.norm(np.diff(p,axis=0),axis=1).max())
        for r in motion['rows']:
            if r['yaw_deg']!=pose['yaw_deg']:continue
            q=curves[r['array_key']];minimum=min(float(tree.find(Vector(v))[2]) for v in q)
            allowance=(ds+float(np.linalg.norm(np.diff(q,axis=0),axis=1).max()))/2+pose['second_derivative_chord_error_bound_mm']+r['curve_error_bound_mm']+1e-5
            gap=minimum-allowance-group['diameter_mm']/2-.3302
            rows.append({'pin':r['pin'],'other_group':group['id'],'yaw_deg':r['yaw_deg'],
                'status':'PASS' if gap>=.3 else 'BLOCKED','surface_gap_lower_bound_mm':gap})
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out={'status':'PASS' if all(r['status']=='PASS' for r in rows) else 'BLOCKED',
    'scope':'Four body-to-yaw UART lines versus two existing local group envelopes; other seven individual moving wires remain undesigned',
    'source_blend_sha256':motion['source_blend_sha256'],'source_script_sha256':sha(Path(__file__)),
    'source_motion_sha256':sha(OUT/'body_to_yaw_motion.json'),'source_curves_sha256':sha(OUT/'body_to_yaw_curves.npz'),
    'source_other_loops_sha256':sha(loops_file),'checks':rows,
    'minimum_surface_gap_lower_bound_mm':min(r['surface_gap_lower_bound_mm'] for r in rows),
    'main_model_applied':False,'full_eleven_wire_harness':'BLOCKED','other_individual_wire_lengths':'NOT_TESTED'}
(OUT/'other_loop_coexistence.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('BODY_PREFIX_OTHER_LOOPS',out['status'],len(rows),out['minimum_surface_gap_lower_bound_mm'],flush=True)

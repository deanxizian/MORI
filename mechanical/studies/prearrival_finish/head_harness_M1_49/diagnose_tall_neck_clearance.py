"""Find the full sampled nearest-surface witness for the late-entry conflict."""
from pathlib import Path
import json,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];OUT=HERE/'remaining_routes'
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from mathutils import Vector
from validate import rigidtr
ctx=Context();rows=[];inputs=[];inv=np.linalg.inv(np.asarray(rigidtr(60,0)))
target=ctx.targets['Pitch_Yoke']
for name in ['left_tall_entry','left_tall_entry_clear','left_tall_entry_dip']:
    base=OUT/name;r=json.loads((base/'neck_screen.json').read_text());case=r['results'][0]
    for f,h in {**r['sources'],**r['inputs']}.items():assert sha(ROOT/f)==h,f
    path=base/'neck_candidates.npz';assert sha(path)==r['curve_sha256'];inputs.extend([base/'neck_screen.json',path])
    p=np.load(path)[f'z149.0_dip{case["dip_mm"]}_wire6_y60'];p=p@inv[:3,:3].T+inv[:3,3]
    all_hits=[target['tree'].find_nearest(Vector(v)) for v in p]
    i=min(range(len(all_hits)),key=lambda i:all_hits[i][3]);co,normal,face,distance=all_hits[i]
    error=np.linalg.norm(np.diff(p,axis=0),axis=1).max()/2+case['chord_error_mm']+1e-4
    rows.append(dict(case=name,phase_deg=case['angles_deg'][6],sampled_nearest_surface_mm=float(distance),
                     conservative_surface_gap_bound_mm=float(distance-.4445-error),wire_point_mm=p[i].tolist(),
                     nearest_surface_mm=list(co),surface_normal=list(normal),face_index=int(face),
                     sampled_points=len(p),surface_only_not_signed_inside_proof=True))
ctx.assert_unchanged()
result=dict(status='PASS',sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},rows=rows,
            scope='Diagnostic full nearest-surface samples, only slot6/yaw60/Pitch_Yoke; no route approval',
            main_changed=False,full_harness='BLOCKED',script_sha256=sha(Path(__file__)))
(OUT/'tall_neck_clearance_diagnosis.json').write_text(json.dumps(result,indent=2)+'\n')
for row in rows:print('TALL_GLOBAL_NEAREST',row,flush=True)

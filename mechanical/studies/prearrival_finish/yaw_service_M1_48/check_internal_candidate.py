"""Explicit current-main replay of the unadopted internal-channel alternative.

Only two recorded trial print solids are substituted in the check, explicitly
listed below. No Blender object or source file is replaced. The four assembled
CAM curves retain body pin numbers, source joins, and the existing bend limits.
"""
from pathlib import Path
import sys,json,math,itertools,time,hashlib
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent/'outer_harness_M1_48'))
from native_context import Context,sha,np,manifold
from validate import rigidtr
ctx=Context();started=time.time();A8=HERE.parent/'harness_A8'
candidate=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/larger_neck_candidate/cleaned'
candidate_parts={};changes=[]
for name in ['Yaw_Base','Pitch_Yoke']:
    path=candidate/(name+'.npz');data=np.load(path)
    m=manifold.Manifold(manifold.Mesh64(data['vertices_mm'],data['triangles'].astype(np.uint64)))
    assert m.status()==manifold.Error.NoError
    original=ctx.ss[name].m
    removed=original-m;added=m-original
    changes.append(dict(name=name,source=str(path.relative_to(PROJECT)),source_sha256=sha(path),
        candidate_volume_mm3=float(m.volume()),original_volume_mm3=float(original.volume()),
        removed_mm3=float(removed.volume()),added_mm3=float(added.volume()),
        removed_bounds_mm=list(removed.bounding_box()),components=len(m.decompose()),
        status='PASS' if len(m.decompose())==1 and added.volume()<.01 else 'BLOCKED',
        exact_vertices=len(data['vertices_mm']),exact_triangles=len(data['triangles'])))
    candidate_parts[name]=m

body_path=A8/'cam_pitch_port/lower_staging/body_partial_curves.npz'
body=np.load(body_path)
fan_path=A8/'cam_fan_in/four_bend_transition/curves.npz';fan=np.load(fan_path)
core_path=A8/'cam_fan_in/short_tail_v2/curves.npz';core=np.load(core_path)
tail_path=A8/'cam_fan_in/short_tail_v2/tails.npz';tails=np.load(tail_path)
body_report=A8/'body_prefix_v2/body_to_yaw_motion.json'
bm=json.loads(body_report.read_text())
join_path=A8/'cam_fan_in/joins.json';joins=json.loads(join_path.read_text())
assert joins['fan_assignment']==[0,0,0,0]
for p in [body_path,fan_path,core_path,tail_path]:assert joins['files'][str(p.relative_to(PROJECT))]==sha(p)
paths={};curve_rows=[];join_rows=[]
for yaw,pitch in itertools.product(range(-60,61,10),range(-20,26,5)):
    ty=np.asarray(rigidtr(yaw,0));tp=np.asarray(rigidtr(yaw,pitch))
    for pin in range(1,5):
        slot=pin-1
        pieces=[body[f'pin{pin}_yaw{yaw}'],
                fan[f'pin{pin}_candidate0']@ty[:3,:3].T+ty[:3,3],
                core[f'candidate0_slot{slot}_pitch{pitch}']@ty[:3,:3].T+ty[:3,3],
                tails[f'slot{slot}'][::-1]@tp[:3,:3].T+tp[:3,3]]
        errors=[float(np.linalg.norm(a[-1]-b[0])) for a,b in zip(pieces,pieces[1:])]
        assert max(errors)<1e-5,(pin,yaw,pitch,errors)
        p=np.vstack([pieces[0]]+[q[1:] for q in pieces[1:]])
        # Only discard repeated numerical seam vertices; never scale or move a point.
        keep=np.r_[True,np.linalg.norm(np.diff(p,axis=0),axis=1)>1e-9];p=p[keep]
        key=f'pin{pin}_y{yaw}_p{pitch}'
        ds=np.linalg.norm(np.diff(p,axis=0),axis=1)
        # Common original source chord-error bound, deliberately rounded upward.
        error=max(.0003,next(r['curve_error_bound_mm'] for r in bm['rows'] if r['array_key']==f'pin{pin}_yaw{yaw}'))
        assert ds.max()<.2,(key,ds.max())
        paths[key]=p
        curve_rows.append(dict(key=key,pin=pin,yaw_deg=yaw,pitch_deg=pitch,
             polygon_length_mm=float(ds.sum()),maximum_step_mm=float(ds.max()),error_bound_mm=error))
        join_rows.append(dict(key=key,join_errors_mm=errors))

native=ctx.targets.copy();moving={n:s for n,s in ctx.ss.items() if s.group in ['yaw','pitch']}
fixed={n:t for n,t in native.items() if n not in moving}
fixed['Yaw_Base']=ctx.target(candidate_parts['Yaw_Base'])
poses=[]
for yaw in range(-60,61,10):
    for pitch in range(-20,26,5):
        ctx.targets=fixed.copy()
        for name,s in moving.items():
            m=candidate_parts.get(name,s.m)
            mat=np.asarray(rigidtr(yaw,pitch if s.group=='pitch' else 0))
            ctx.targets[name]=ctx.target(m.transform(mat[:3,:]))
        hits=[]
        for row in [r for r in curve_rows if r['yaw_deg']==yaw and r['pitch_deg']==pitch]:
            p=paths[row['key']]
            e=ctx.port_pins['motion_J5']['pins'][str(row['pin'])]
            root_end=e+[0.,0.,5.]
            ix=np.flatnonzero(np.linalg.norm(p-root_end,axis=1)<1e-7)
            assert len(ix)==1 and np.linalg.norm(p[0]-e)<1e-7
            root=ctx.clear(p[:ix[0]+1],ignore={'Plug_motion_J5'})
            remainder=ctx.clear(p[ix[0]:],row['error_bound_mm'])
            if root or remainder:hits.append(dict(pin=row['pin'],root_hit=root,remainder_hit=remainder))
        poses.append(dict(yaw_deg=yaw,pitch_deg=pitch,status='BLOCKED' if hits else 'PASS',hits=hits))
    print('INTERNAL_CURRENT_YAW',yaw,'failed_poses',sum(r['status']=='BLOCKED' for r in poses),flush=True)

lengths=[]
for pin in range(1,5):
    values=[r['polygon_length_mm'] for r in curve_rows if r['pin']==pin]
    lengths.append(dict(pin=pin,minimum_polygon_mm=min(values),maximum_polygon_mm=max(values),
                        variation_mm=max(values)-min(values),scope='Numerical routed length; not a cut length or production tolerance'))
ctx.assert_unchanged()
np.savez_compressed(HERE/'internal_full_curves.npz',**paths)
evidence=ctx.evidence();evidence['substituted_prints']=changes
report=dict(status='BLOCKED' if any(r['status']=='BLOCKED' for r in poses+changes) else 'PASS',
    scope='Four joined current-body to CAM-allocation curves with two explicitly unadopted print alternatives',
    **evidence,script_sha256=sha(__file__),curve_inputs={str(p.relative_to(PROJECT)):sha(p) for p in [body_path,fan_path,core_path,tail_path,body_report,join_path]},
    joins=join_rows,curve_rows=curve_rows,poses=poses,lengths=lengths,
    wire_OD_mm=.6604,surface_gap_mm=.3,head_poses=130,
    four_wire_self_and_mutual='NOT_TESTED',radius_proof='NOT_TESTED',
    actual_CAM_mating_view='BLOCKED',retention='NOT_TESTED',complete_assembly='NOT_TESTED',
    other_seven_head_wires_and_FFC='NOT_TESTED',main_applied=False,
    whole_harness='BLOCKED',supplier_cut_lengths_released=False,elapsed_s=time.time()-started)
(HERE/'internal_candidate.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('INTERNAL_CURRENT_DONE',report['status'],lengths,flush=True)

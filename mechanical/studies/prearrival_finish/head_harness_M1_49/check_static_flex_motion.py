"""Check one explicitly assumed LCD central packing span at 130 poses."""
from pathlib import Path
import json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes';OUT=BASE/'static_flex/motion'
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from common import manifold,Vector
from validate import rigidtr
from static_flex_geometry import core
from upper_pack_geometry import refined

ctx=Context();started=time.time();geom=core(radius=7.5,width=10.5,z=238.)
m=manifold.Manifold(manifold.Mesh64(geom['vertices_mm'],geom['triangles']))
assert m.status()==manifold.Error.NoError
tree=ctx.target(m)['tree'];error=geom['metadata']['chord_error_bound_mm']
path=BASE/'cam_side_fans/c6_join/candidate_curves.npz';curves=np.load(path)
report_path=BASE/'cam_side_fans/c6_join/join_review.json'
received=json.loads(report_path.read_text());assert received['status']=='PASS'
assert received['source_main_sha256']==ctx.source_hash if 'source_main_sha256' in received else received['sources']['mechanical/mori_v1_2.blend']==ctx.source_hash
poses=[(y,p) for y in range(-60,61,10) for p in range(-20,26,5)]
rows=[];fail=[];wfail=[];wiremin=None
for yaw,pitch in poses:
    tr=np.array(rigidtr(yaw,pitch));tm=m.transform(tr[:3,:]);v=geom['vertices_mm']@tr[:3,:3].T+tr[:3,3]
    lo=v.min(0);hi=v.max(0);near=[]
    for name,s in ctx.ss.items():
        if s.group=='pitch':
            target=s.m.transform(tr[:3,:]);tv=s.v@tr[:3,:3].T+tr[:3,3]
        elif s.group=='yaw':
            ty=np.array(rigidtr(yaw,0));target=s.m.transform(ty[:3,:]);tv=s.v@ty[:3,:3].T+ty[:3,3]
        else:target=s.m;tv=s.v
        if np.any(lo>tv.max(0)+1) or np.any(hi<tv.min(0)-1):continue
        overlap=float((tm^target).volume());gap=float(tm.min_gap(target,1.))
        near.append(dict(target=name,gap_mm=gap,gap_search_cap_mm=1.,overlap_mm3=overlap))
        if overlap>1e-7 or gap<.3+error:fail.append(dict(yaw=yaw,pitch=pitch,**near[-1]))
    names=[(f'CAM_{i}_y{yaw}_p{pitch}',.6604) for i in range(1,5)]
    names += [(f'P_J9_{i}_y{yaw}',1.1684) for i in range(1,4)]
    names += [(f'P_J18_{i}_y{yaw}',1.1684) for i in range(1,3)]
    names += [(f'SPK_reservation_{i}_y{yaw}',.889) for i in [3,6]]
    for key,diameter in names:
        a=refined(curves[key],.1);a=(a-tr[:3,3])@tr[:3,:3]
        bound=diameter/2+.3+.05+error
        good=np.flatnonzero(np.all(a>=geom['vertices_mm'].min(0)-bound,axis=1)&
                            np.all(a<=geom['vertices_mm'].max(0)+bound,axis=1))
        minimum=None
        for i in good:
            dist=float(tree.find_nearest(Vector(a[i]))[3])
            if minimum is None or dist<minimum[0]:minimum=(dist,i)
        if minimum is not None:
            distance,i=minimum;record=dict(yaw=yaw,pitch=pitch,wire=key,
                center_to_ribbon_distance_mm=distance,surface_gap_lower_bound_mm=distance-diameter/2-.05-error,
                wire_point_pitch_zero_mm=a[i].tolist())
            if wiremin is None or record['surface_gap_lower_bound_mm']<wiremin['surface_gap_lower_bound_mm']:wiremin=record
            if distance<bound:wfail.append(record)
    rows.append(dict(yaw=yaw,pitch=pitch,rigid_candidates_checked=len(near),nearby=near,wire_candidates_checked=len(names)))
    if pitch==25:print('STATIC_FLEX_MOTION',yaw,'rigid_fail',len(fail),'wire_fail',len(wfail),flush=True)
ctx.assert_unchanged()
report=dict(status='FAIL' if fail or wfail else 'PASS',sources=ctx.sources,
    inputs={str(p.relative_to(ROOT)):sha(p) for p in [path,report_path,HERE/'static_flex_geometry.py',HERE/'upper_pack_geometry.py']},
    poses=len(rows),rows=rows,rigid_failures=fail,wire_failures=wfail,closest_candidate_wire=wiremin,
    geometric_parameters=geom['metadata'],wire_checks=130*11,
    scope='Central 170 mm storage allocation only; current main rigid parts plus 11 candidate conductor paths per pose',
    limitations=['FFC width, thickness and allowed radius are assumed, not selected or measured.',
        'Two 15 mm end approaches are not modeled; insertion, pin1/contact orientation and anchoring are not verified.',
        'Wire paths are unadopted candidates; speaker remote endpoints and other head connections are absent.',
        '0.3 mm is a geometric planning threshold; 130 poses are not a continuous or physical test.',
        'Rigid min_gap search is capped at 1 mm; values of 1 mean at least 1 mm, not the actual minimum.'],
    main_changed=False,adopted=False,full_flex_fit='BLOCKED',full_harness='BLOCKED',physical_validation='NOT_TESTED',
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('STATIC_FLEX_MOTION_DONE',report['status'],flush=True)

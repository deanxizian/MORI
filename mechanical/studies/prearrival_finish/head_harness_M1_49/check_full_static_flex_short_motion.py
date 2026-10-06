"""Current-main motion and candidate-wire screening for a full free span."""
from pathlib import Path
import json, sys, time
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes'; FULL=BASE/'static_flex/full_route'; OUT=FULL/'short_motion'
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts')); sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from common import manifold,Vector
from validate import rigidtr
from upper_pack_geometry import refined
ctx=Context(); started=time.time(); label='L2_W10.5'
source=FULL/'short_lead/review.json'; previous=json.loads(source.read_text())
row=next(r for r in previous['rows'] if r['id']==label); assert row['status']=='PASS'
path=FULL/'short_lead'/(label+'.npz'); geom=np.load(path)
m=manifold.Manifold(manifold.Mesh64(geom['vertices_mm'],geom['triangles']))
assert m.status()==manifold.Error.NoError
tree=ctx.target(m)['tree']; error=row['parameters']['polygonal_chord_error_bound_mm']
curve_path=BASE/'cam_side_fans/c6_join/candidate_curves.npz'; curves=np.load(curve_path)
wire_report=BASE/'cam_side_fans/c6_join/join_review.json'; received=json.loads(wire_report.read_text())
assert received['status']=='PASS' and received['sources']['mechanical/mori_v1_2.blend']==ctx.source_hash
rows=[]; failures=[]; wire_failures=[]; wire_min=None
for yaw in range(-60,61,10):
    for pitch in range(-20,26,5):
        tr=np.array(rigidtr(yaw,pitch)); ty=np.array(rigidtr(yaw,0))
        tm=m.transform(tr[:3,:]); v=geom['vertices_mm']@tr[:3,:3].T+tr[:3,3]
        lo=v.min(0); hi=v.max(0); near=[]
        for name,s in ctx.targets.items():
            group=ctx.ss[name].group if name in ctx.ss else 'body'
            move=tr if group=='pitch' else ty if group=='yaw' else None
            target=s['m'] if move is None else s['m'].transform(move[:3,:])
            # Transform eight bound corners conservatively; no imported body targets are moved.
            box=np.array([[x,y,z] for x in [s['lo'][0],s['hi'][0]] for y in [s['lo'][1],s['hi'][1]] for z in [s['lo'][2],s['hi'][2]]])
            if move is not None: box=box@move[:3,:3].T+move[:3,3]
            if np.any(lo>box.max(0)+1) or np.any(hi<box.min(0)-1): continue
            overlap=float((tm^target).volume()); gap=float(tm.min_gap(target,1.))
            item=dict(target=name,gap_mm=gap,gap_search_cap_mm=1.,overlap_mm3=overlap)
            near.append(item)
            if overlap>1e-7 or gap<.3+error: failures.append(dict(yaw=yaw,pitch=pitch,**item))
        names=[(f'CAM_{i}_y{yaw}_p{pitch}',.6604) for i in range(1,5)]
        names += [(f'P_J9_{i}_y{yaw}',1.1684) for i in range(1,4)]
        names += [(f'P_J18_{i}_y{yaw}',1.1684) for i in range(1,3)]
        names += [(f'SPK_reservation_{i}_y{yaw}',.889) for i in [3,6]]
        for key,diameter in names:
            points=refined(curves[key],.1); points=(points-tr[:3,3])@tr[:3,:3]
            bound=diameter/2+.3+.05+error
            ids=np.flatnonzero(np.all(points>=geom['vertices_mm'].min(0)-bound,axis=1)&np.all(points<=geom['vertices_mm'].max(0)+bound,axis=1))
            minimum=None
            for i in ids:
                distance=float(tree.find_nearest(Vector(points[i]))[3])
                if minimum is None or distance<minimum[0]: minimum=(distance,i)
            if minimum is not None:
                distance,i=minimum
                item=dict(yaw=yaw,pitch=pitch,wire=key,center_to_ribbon_distance_mm=distance,
                    surface_gap_lower_bound_mm=distance-diameter/2-.05-error,
                    wire_point_pitch_zero_mm=points[i].tolist())
                if wire_min is None or item['surface_gap_lower_bound_mm']<wire_min['surface_gap_lower_bound_mm']: wire_min=item
                if distance<bound: wire_failures.append(item)
        rows.append(dict(yaw=yaw,pitch=pitch,rigid_candidates_checked=len(near),nearby=near,wire_candidates_checked=len(names)))
    print('FULL_FFC_SHORT_MOTION',yaw,'rigid_fail',len(failures),'wire_fail',len(wire_failures),flush=True)
ctx.assert_unchanged()
report=dict(status='FAIL' if failures or wire_failures else 'PASS',sources=ctx.sources,
    inputs={str(p.relative_to(ROOT)):sha(p) for p in [source,path,curve_path,wire_report,HERE/'upper_pack_geometry.py']},
    candidate=label,poses=len(rows),rows=rows,rigid_failures=failures,wire_failures=wire_failures,
    closest_candidate_wire=wire_min,geometric_parameters=row['parameters'],wire_checks=len(rows)*11,
    scope='194 mm free-span capacity, actual current native solids, body plug/wire allocations and 11 candidate conductors per pose',
    limitations=['Endpoint centers and cable geometry are assumptions, no actual insertion/stiffener or anchor modeled.',
        'Imported plug/fixed-wire targets are body allocations; all native pitch and yaw objects follow their actual groups.',
        'Wire paths depend on unapproved C6 and are not an installed harness.',
        '0.3 mm is a planning gap; 130 samples are not continuous motion or physical validation.',
        'min_gap=1 is a lower bound at the search cap, not an exact minimum.'],
    main_changed=False,adopted=False,full_flex_fit='BLOCKED',full_harness='BLOCKED',
    physical_validation='NOT_TESTED',script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('FULL_FFC_SHORT_MOTION_DONE',report['status'],flush=True)

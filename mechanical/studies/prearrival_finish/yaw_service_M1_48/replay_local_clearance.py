"""Recheck joined curves on M1.48 with explicitly identified trial cut solids.

The 'cuts' trial retains only subtraction from current printed parts; historical
added cable anchors are excluded and remain a separate unresolved design task.
Nothing in the saved assembly, geometry config or hardware files is modified.
"""
from pathlib import Path
import sys, json, itertools, time
HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(HERE.parent/'outer_harness_M1_48'))
from native_context import Context,sha,np,manifold
from validate import rigidtr
from local_clearance import clear,adaptive_clear

args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
mode='historical' if '--historical' in args else 'cuts'
if '--refined' in args: mode='refined'
full='--all' in args
adaptive='--adaptive' in args
diagnostic='--ignore-prints' in args
if adaptive: clear=adaptive_clear
tag=mode+('_adaptive' if adaptive else '')+('_ignore_prints' if diagnostic else '')+('_all' if full else '_screen')
ctx=Context(); started=time.time()
previous=json.loads((HERE/'internal_candidate.json').read_text())
assert previous['source_main_sha256']==ctx.source_hash
source_path=HERE/'internal_full_curves.npz'
curves=np.load(source_path)
candidate_parts={};changes=[]
candidate_rows=previous['substituted_prints']
if mode=='refined':
    construction=json.loads((HERE/'refined_construction.json').read_text())
    assert construction['source_main_sha256']==ctx.source_hash
    candidate_rows=construction['parts']
for row in candidate_rows:
    name=row['name']; path=PROJECT/row['source']
    assert sha(path)==row['source_sha256']
    data=np.load(path)
    historic=manifold.Manifold(manifold.Mesh64(data['vertices_mm'],data['triangles'].astype(np.uint64)))
    native=ctx.ss[name].m
    cut=native-historic
    added=historic-native
    selected=native-cut if mode=='cuts' else historic
    assert selected.status()==manifold.Error.NoError
    candidate_parts[name]=selected
    components=selected.decompose()
    # Retain actual geometry and disclose even numerical disconnected pieces.
    changes.append(dict(name=name,source=row['source'],source_sha256=sha(path),
        removed_mm3=float((native-selected).volume()),added_mm3=float((selected-native).volume()),
        excluded_historical_additions_mm3=float(added.volume()) if mode=='cuts' else 0.,
        historical_added_bounds_mm=list(added.bounding_box()),
        components_mm3=[float(m.volume()) for m in components],
        mesh_kernel=str(selected.status()),main_applied=False))
    for label,m in [('trial',selected),('removed',native-selected),('historical_added',added)]:
        mesh=m.to_mesh64()
        np.savez_compressed(HERE/f'{mode}_{name}_{label}.npz',vertices_mm=np.asarray(mesh.vert_properties[:,:3]),triangles=np.asarray(mesh.tri_verts))

native_targets=ctx.targets.copy()
moving={n:s for n,s in ctx.ss.items() if s.group in ['yaw','pitch']}
fixed={n:t for n,t in native_targets.items() if n not in moving}
fixed['Yaw_Base']=ctx.target(candidate_parts['Yaw_Base'])
yaws=list(range(-60,61,10)) if full else [0,-60,60]
pitches=list(range(-20,26,5)) if full else [0,-20,25]
poses=[]
for yaw,pitch in itertools.product(yaws,pitches):
    ctx.targets=fixed.copy()
    for name,s in moving.items():
        m=candidate_parts.get(name,s.m)
        transform=np.asarray(rigidtr(yaw,pitch if s.group=='pitch' else 0))
        ctx.targets[name]=ctx.target(m.transform(transform[:3,:]))
    if diagnostic:
        ctx.targets={n:t for n,t in ctx.targets.items() if n not in ['Yaw_Base','Pitch_Yoke']}
    hits=[]
    for pin in range(1,5):
        key=f'pin{pin}_y{yaw}_p{pitch}'; p=curves[key]
        e=ctx.port_pins['motion_J5']['pins'][str(pin)]
        root_end=e+[0.,0.,5.]
        ix=np.flatnonzero(np.linalg.norm(p-root_end,axis=1)<1e-7)
        assert len(ix)==1 and np.linalg.norm(p[0]-e)<1e-7
        root=clear(ctx,p[:ix[0]+1],ignore={'Plug_motion_J5'})
        remainder=clear(ctx,p[ix[0]:],.0003)
        if root or remainder:
            hits.append(dict(pin=pin,root_hit=root,remainder_hit=remainder))
    poses.append(dict(yaw_deg=yaw,pitch_deg=pitch,status='FAIL' if hits else 'PASS',hits=hits))
    print('LOCAL_CLEARANCE',tag,yaw,pitch,'hits',hits,flush=True)
ctx.assert_unchanged()
report=dict(**ctx.evidence())
report.update(status='FAIL' if any(r['hits'] for r in poses) else 'PASS',
    scope='Wire clearance at stated finite poses, with explicitly unadopted print candidates',
    mode=mode,substituted_prints=changes,poses=poses,head_poses=len(poses),
    script_sha256=sha(__file__),clearance_helper_sha256=sha(HERE/'local_clearance.py'),
    curve_source_sha256=sha(source_path),original_replay_sha256=sha(HERE/'internal_candidate.json'),
    wire_OD_mm=.6604,surface_gap_mm=.3,curve_error_bound_mm=.0003,
    numerical_bound='Per-point maximum adjacent chord span / 2 plus declared chord error and 0.0001 mm',
    adaptive_chord_refinement=adaptive,
    excluded_for_diagnosis=['Yaw_Base','Pitch_Yoke'] if diagnostic else [],
    retained_main_objects=209,main_applied=False,retention='NOT_TESTED',
    full_assembly='NOT_TESTED',whole_harness='BLOCKED',elapsed_s=time.time()-started)
(HERE/f'{tag}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('LOCAL_CLEARANCE_DONE',tag,report['status'],flush=True)

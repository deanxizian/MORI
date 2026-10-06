"""Re-route only the unfinished power upper tail around a fixed CAM restraint."""
from pathlib import Path
import itertools,json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=HERE/'remaining_routes'
OUT=BASE/'cam_restraints/power_clearance_v2';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from common import manifold
from validate import rigidtr
from rear_power_bump_geometry import build
from route_family import family
from sliding_cam_guide_v4_geometry import build as guide_build
from curve_clearance import prepared
from curve_self_partition import self_clear
from bounded_curve_checks import pair_threshold
from upper_pack_geometry import refined
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text())
J=BASE/'cam_side_fans/c6_join';L=BASE/'left_tall_balanced';N=BASE/'rear_power_bump';C=BASE/'cam_restraints/connector'
jr=read(J/'join_review.json');nr=read(N/'neck_screen.json');lr=read(L/'neck_screen.json')
for r in [jr,nr,lr]:
    assert r['status']=='PASS'
    for f,h in {**r['sources'],**r['inputs']}.items():assert sha(ROOT/f)==h,f
assert sha(J/'candidate_curves.npz')==jr['curve_sha256'];allcurves=np.load(J/'candidate_curves.npz')
assert sha(N/'curves.npz')==nr['curve_sha256'];neck=np.load(N/'curves.npz')
assert sha(L/'neck_candidates.npz')==lr['curve_sha256'];old=np.load(L/'neck_candidates.npz')
lane=next(r for r in lr['results'] if r['status']=='PASS');params=next(r['params'] for r in nr['results'] if r['status']=='PASS')
def stored(path):
    a=np.load(path);return manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles'].astype(np.uint64)))
pieces={n:stored(C/(n+'.npz')).translate([.03 if n!='addition' else 0,0,0]) for n in ['addition','band','head']}
guide,_=guide_build();original=ctx.targets
native=dict(original);native['Yaw_Base']=ctx.target(stored(BASE/'c6_left_slot_entry/Yaw_Base_candidate.npz'))
groups={n:s.group if s.group in ['yaw','pitch'] else 'body' for n,s in ctx.ss.items()}
targets={g:{n:t for n,t in native.items() if groups.get(n,'body')==g} for g in ['body','yaw','pitch']}
targets['yaw']['Sliding_guide']=ctx.target(guide)
targets['pitch'].update({f'CAM_clamp_{n}':ctx.target(m) for n,m in pieces.items()})
yaws=list(range(-60,61,10));pitches=list(range(-20,26,5));rows={r['yaw_deg']:r for r in family(z0=149.,dip=.6,samples=7201)}
others={}
for name in ['CAM_1','CAM_2','CAM_3','CAM_4','P_J9_1','P_J9_2','P_J9_3','P_J18_2','SPK_reservation_3','SPK_reservation_6']:
    for yaw in yaws:
        for pitch in (pitches if name.startswith('CAM_') else [0]):
            key=f'{name}_y{yaw}'+(f'_p{pitch}' if name.startswith('CAM_') else '')
            radius=.3302 if name.startswith('CAM_') else .4445 if name.startswith('SPK_') else .5842
            others[name,yaw,pitch]=prepared(refined(allcurves[key],.01),radius,.0003)
results=[];saved=None
for offset_x in [1.4,1.8,2.2]:
    trial={**params,'offset':(offset_x,params['offset'][1])};curves={};meta={};hits=[];checks=0;pairs=[];selves=[]
    for yaw,row in rows.items():
        base,_=build(row,old[f'z149.0_dip0.6_wire5_y{yaw}'],lane['angles_deg'][5],**params)
        assert np.array_equal(base,neck[f'wire5_y{yaw}'])
        new,m=build(row,old[f'z149.0_dip0.6_wire5_y{yaw}'],lane['angles_deg'][5],**trial)
        lower=allcurves[f'P_J18_1_y{yaw}'];mask=base[:,2]>=149.;fmask=lower[:,2]>=149.
        assert np.array_equal(base[mask],lower[fmask])
        p=np.vstack([lower[~fmask],new[mask]])
        assert np.array_equal(p[p[:,2]<=191.],lower[lower[:,2]<=191.])
        curves[yaw]=p;meta[yaw]=m
    bend=min(m['minimum_sampled_bend_mm'] for m in meta.values());stage='bend';ok=False
    if bend>=7.:
        stage='native_and_restraints'
        for yaw in yaws:
            for group,tg in targets.items():
                ctx.targets=tg
                for pitch in (pitches if group=='pitch' else [0]):
                    inv=np.eye(4) if group=='body' else np.linalg.inv(np.asarray(rigidtr(yaw,pitch if group=='pitch' else 0)))
                    p=curves[yaw][curves[yaw][:,2]>=191.]@inv[:3,:3].T+inv[:3,3]
                    hit=ctx.clear(p,chord_error=max(.0003,meta[yaw]['chord_error_mm']),radius=.5842);checks+=1
                    if hit:hits.append(dict(yaw=yaw,pitch=pitch,group=group,**hit));break
                if hits:break
            if hits:break
        if not hits:
            assert checks==156;stage='full_path_pairs'
            pack={y:prepared(refined(p,.01),.5842,max(.0003,meta[y]['chord_error_mm'])) for y,p in curves.items()}
            for (name,yaw,pitch),q in others.items():
                rr=pair_threshold(pack[yaw],q);pairs.append(dict(other=name,yaw=yaw,pitch=pitch,**rr))
                if rr['status']!='PASS':break
            if all(r['status']=='PASS' for r in pairs):
                assert len(pairs)==598;stage='full_path_self'
                selves=[dict(yaw=y,**self_clear(p)) for y,p in pack.items()];ok=all(r['status']=='PASS' for r in selves)
    r=dict(status='PASS' if ok else 'BLOCKED',params=trial,stage=stage,minimum_sampled_bend_mm=bend,native_checks=checks,native_hits=hits,pair_checks=pairs,self_checks=selves,
           curvature=[dict(yaw=y,**m) for y,m in meta.items()]);results.append(r)
    print('POWER_CLAMP',offset_x,r['status'],stage,bend,hits[:1],[q for q in pairs if q['status']!='PASS'][:1],flush=True)
    if ok:
        saved={k:allcurves[k] for k in allcurves.files};saved.update({f'P_J18_1_y{y}':p for y,p in curves.items()});break
ctx.targets=original;ctx.assert_unchanged()
if saved:np.savez_compressed(OUT/'candidate_curves.npz',**saved)
inputs=[J/'join_review.json',J/'candidate_curves.npz',N/'neck_screen.json',N/'curves.npz',L/'neck_screen.json',L/'neck_candidates.npz',C/'review.json',*[C/(n+'.npz') for n in pieces],
        BASE/'c6_left_slot_entry/Yaw_Base_candidate.npz',HERE/'rear_power_bump_geometry.py',HERE/'route_family.py',HERE/'sliding_cam_guide_v4_geometry.py',HERE/'sliding_cam_guide_geometry.py',
        HERE/'curve_clearance.py',HERE/'curve_self_partition.py',HERE/'bounded_curve_checks.py',HERE/'upper_pack_geometry.py']
r=dict(status='PASS' if saved else 'BLOCKED',scope='One partial power tail changed aboveZ191; all complete CAM curves and other routes retained byte-identical',sources=ctx.sources,
       inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},results=results,changed_route='P_J18_1',CAM_routes_changed=False,
       unchanged_lower_native_proof='byte-identical below Z191; original conditional C6 join and lower-nine endpoint-specific checks retained',
       curve_sha256=sha(OUT/'candidate_curves.npz') if saved else None,main_changed=False,approved=False,C6_main_applied=False,
       tie_translation_x_mm=.03,guide_version=4,full_harness='BLOCKED',script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(r,indent=2)+'\n');print('POWER_CLAMP_DONE',r['status'],r['elapsed_s'],flush=True)

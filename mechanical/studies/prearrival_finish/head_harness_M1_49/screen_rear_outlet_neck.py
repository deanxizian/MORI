"""Equal-length rear outlet study in current native neck solids, no new holes."""
from pathlib import Path
import itertools,json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
OLD=HERE/'remaining_routes/left_tall_balanced';OUT=HERE/'remaining_routes/rear_outlet_neck';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from neck_turn_geometry import family,rotate
from route_family import family as baseline_family
from curve_clearance import prepared,pair,self_clear
from validate import rigidtr
ctx=Context();started=time.time();nr=json.loads((OLD/'neck_screen.json').read_text())
for f,h in {**nr['sources'],**nr['inputs']}.items():assert sha(ROOT/f)==h,f
assert nr['status']=='PASS' and sha(OLD/'neck_candidates.npz')==nr['curve_sha256']
old=np.load(OLD/'neck_candidates.npz');lane=next(r for r in nr['results'] if r['status']=='PASS');angles=lane['angles_deg'];changed=[4,5,7,8,9,10]
a=family(z0=149.,dip=.6,samples=7201);b=baseline_family(z0=149.,dip=.6,samples=7201)
replay=max(float(np.max(np.linalg.norm(x['points']-y['points'],axis=1))) for x,y in zip(a,b));assert replay<1e-8
native=ctx.targets;groups={n:s.group if s.group in ['yaw','pitch'] else 'body' for n,s in ctx.ss.items()}
targets={g:{n:t for n,t in native.items() if groups.get(n,'body')==g} for g in ['body','yaw','pitch']}
results=[];arrays={}
plans=[('uniform220',220.,dict.fromkeys(changed,90.)),('spread220',220.,{4:87.,5:80.,7:90.,8:90.,9:85.,10:90.}),
       ('spread230',230.,{4:87.,5:80.,7:90.,8:90.,9:85.,10:90.})]
for ident,z1,turns in plans:
    families={turn:family(z0=149.,z1=z1,dip=.6,samples=7201,nominal_turn_deg=turn) for turn in set(turns.values())}
    curves={};meta=[];errors={}
    for slot,yaw in itertools.product(range(11),range(-60,61,10)):
        if slot not in changed:
            curves[slot,yaw]=old[f'z149.0_dip0.6_wire{slot}_y{yaw}'];errors[slot,yaw]=lane['chord_error_mm'];continue
        row=next(r for r in families[turns[slot]] if r['yaw_deg']==yaw)
        p=rotate(row['points'],angles[slot]);start=p[0].copy();start[2]=142.
        lead=np.linspace(start,p[0],int(np.ceil(7./.03))+1);q=np.vstack([lead,p[1:]])
        original=old[f'z149.0_dip0.6_wire{slot}_y{yaw}'];assert np.max(np.linalg.norm(q[:len(lead)]-original[:len(lead)],axis=1))<1e-8
        curves[slot,yaw]=q;errors[slot,yaw]=row['chord_error_mm']
        meta.append(dict(slot=slot,yaw=yaw,nominal_turn_deg=turns[slot],length_mm=row['length_mm']+7.,minimum_sampled_bend_mm=row['minimum_sampled_bend_mm'],chord_error_mm=row['chord_error_mm']))
    hits=[];checks=0;self_rows=[];pairs=[]
    for slot,yaw in itertools.product(changed,range(-60,61,10)):
        p=curves[slot,yaw];err=errors[slot,yaw];radius=nr['OD_mm'][slot]/2
        self_rows.append(dict(slot=slot,yaw=yaw,**self_clear(prepared(p,radius,err))))
        for group,tg in targets.items():
            ctx.targets=tg
            for pitch in (range(-20,26,5) if group=='pitch' else [0]):
                tr=np.eye(4) if group=='body' else np.linalg.inv(np.asarray(rigidtr(yaw,pitch if group=='pitch' else 0)))
                hit=ctx.clear(p@tr[:3,:3].T+tr[:3,3],chord_error=err,radius=radius);checks+=1
                if hit:hits.append(dict(slot=slot,yaw=yaw,pitch=pitch,group=group,**hit))
    for yaw in range(-60,61,10):
        items={s:prepared(curves[s,yaw],nr['OD_mm'][s]/2,errors[s,yaw]) for s in range(11)}
        for a,b in itertools.combinations(items,2):pairs.append(dict(yaw=yaw,a=a,b=b,**pair(items[a],items[b])))
    bend=min(r['minimum_sampled_bend_mm'] for r in meta)
    success=not hits and all(r['status']=='PASS' for r in self_rows+pairs) and bend>=7.
    result=dict(id=ident,status='PASS' if success else 'BLOCKED',end_z_mm=z1,turns_deg=turns,
        native_checks=checks,hits=hits,self_checks=self_rows,pair_checks=pairs,curves=meta,minimum_sampled_bend_mm=bend,
        chord_error_mm=max(errors.values()),entry_z_mm=142.,twist_start_z_mm=149.,angles_deg=angles)
    results.append(result);print('REAR_OUTLET',ident,result['status'],len(hits),bend,flush=True)
    if success:arrays={f'wire{s}_y{y}':p for (s,y),p in curves.items()};break
ctx.targets=native;ctx.assert_unchanged()
if arrays:np.savez_compressed(OUT/'neck_candidates.npz',**arrays)
inputs=[OLD/'neck_screen.json',OLD/'neck_candidates.npz',HERE/'route_family.py',HERE/'neck_turn_geometry.py',ROOT/'mechanical/scripts/neck_curve_geometry.py',HERE/'curve_clearance.py']
r=dict(status='PASS' if arrays else 'BLOCKED',sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},results=results,
    baseline_replay_max_delta_mm=replay,curve_sha256=sha(OUT/'neck_candidates.npz') if arrays else None,OD_mm=nr['OD_mm'],unchanged_native_slots=[0,1,2,3,6],
    scope='Local equal-length neck shapes only. Six existing lines turn toward the rear outlet; all eleven local pair sets checked. Lower straight entries and all native solids unchanged.',
    body_prefixes='NOT_TESTED',upper_endpoints='NOT_TESTED',full_harness='BLOCKED',main_changed=False,C6_main_applied=False,
    supplier_cut_lengths_released=False,script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'neck_screen.json').write_text(json.dumps(r,indent=2)+'\n');print('REAR_OUTLET_DONE',r['status'],r['elapsed_s'],flush=True)

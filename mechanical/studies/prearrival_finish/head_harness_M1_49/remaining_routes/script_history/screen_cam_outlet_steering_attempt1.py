"""Steer only CAM3/4 above the neck, preserving every lower entry sample.

No printed/hardware change. This is a local shape screen, not a constant-length
whole-harness claim: any extra yaw-dependent path length must be compensated
in the upper service loop before that route can be accepted.
"""
from pathlib import Path
import itertools,json,math,sys,time
from numpy.polynomial import polynomial as poly
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
OLD=HERE/'remaining_routes/left_tall_balanced';OUT=HERE/'remaining_routes/neck_outlet_steering';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from route_family import family,profile,rotate
from curve_clearance import prepared,pair,self_clear
from validate import rigidtr
ctx=Context();started=time.time();nr=json.loads((OLD/'neck_screen.json').read_text())
for f,h in {**nr['sources'],**nr['inputs']}.items():assert sha(ROOT/f)==h,f
assert nr['status']=='PASS' and sha(OLD/'neck_candidates.npz')==nr['curve_sha256']
old=np.load(OLD/'neck_candidates.npz');lane=next(r for r in nr['results'] if r['status']=='PASS');angles=lane['angles_deg']
source_rows=family(z0=149.,dip=.6,samples=7201)
native=ctx.targets;groups={n:s.group if s.group in ['yaw','pitch'] else 'body' for n,s in ctx.ss.items()}
targets={g:{n:t for n,t in native.items() if groups.get(n,'body')==g} for g in ['body','yaw','pitch']}
results=[];arrays={};replay=[]
for start in [185.,181.,188.]:
    delta=-15.;curves={};errors={};curvature_rows=[];lengths=[]
    for slot,row in itertools.product(range(11),source_rows):
        yaw=row['yaw_deg'];original=old[f'z149.0_dip0.6_wire{slot}_y{yaw}']
        if slot not in [7,10]:curves[slot,yaw]=original;errors[slot,yaw]=lane['chord_error_mm'];continue
        p=row['points'];z=p[:,2];base=rotate(p,angles[slot]);j=int(np.searchsorted(original[:,2],149.))
        replay_delta=float(np.max(np.linalg.norm(original[j:]-base,axis=1)));assert replay_delta<1e-8;replay.append(replay_delta)
        u=np.clip((z-start)/(200.-start),0.,1.);active=(z>start)&(z<200.)
        w=10*u**3-15*u**4+6*u**5
        wd=np.where(active,(30*u**2-60*u**3+30*u**4)/(200.-start),0.)
        wdd=np.where(active,(60*u-180*u**2+120*u**3)/(200.-start)**2,0.)
        gamma=math.radians(delta);t=(z-149.)/51.;co=np.array(row['coefficients'])
        theta=poly.polyval(t,co)+math.radians(angles[slot])+gamma*w
        td=poly.polyval(t,poly.polyder(co))/51.+gamma*wd
        tdd=poly.polyval(t,poly.polyder(co,2))/51.**2+gamma*wdd
        r,rd,rdd=profile(z,10.6,15.2,173.,30.,.6)
        cs,sn=np.cos(theta),np.sin(theta);q=np.c_[r*cs,r*sn,z]
        vel=np.c_[rd*cs-r*sn*td,rd*sn+r*cs*td,np.ones(len(z))]
        acc=np.c_[(rdd-r*td**2)*cs-(2*rd*td+r*tdd)*sn,(rdd-r*td**2)*sn+(2*rd*td+r*tdd)*cs,np.zeros(len(z))]
        k=np.linalg.norm(np.cross(vel,acc),axis=1)/np.linalg.norm(vel,axis=1)**3;bend=float(1/k.max())
        # Conservative extra second derivative from the bounded smooth rotation.
        g1=abs(gamma)*1.875/(200.-start);g2=abs(gamma)*5.774/(200.-start)**2
        old_v=float(np.max(np.sqrt(rd**2+(r*(td-gamma*wd))**2)))
        extra=(2*g1*old_v+(g1*g1+g2)*15.2)*float(np.diff(z).max())**2/8
        error=lane['chord_error_mm']+extra
        combined=np.vstack([original[:j],q]);assert np.max(np.linalg.norm(combined[combined[:,2]<=start]-original[original[:,2]<=start],axis=1))<1e-8
        curves[slot,yaw]=combined;errors[slot,yaw]=error
        curvature_rows.append(dict(slot=slot,yaw=yaw,minimum_sampled_bend_mm=bend,chord_error_mm=error))
        lengths.append(dict(slot=slot,yaw=yaw,polygon_length_mm=float(np.linalg.norm(np.diff(combined,axis=0),axis=1).sum()),
            delta_from_original_mm=float(np.linalg.norm(np.diff(combined,axis=0),axis=1).sum()-np.linalg.norm(np.diff(original,axis=0),axis=1).sum())))
    hits=[];checks=0;self_rows=[];pairs=[]
    for slot,yaw in itertools.product([7,10],range(-60,61,10)):
        p=curves[slot,yaw];err=errors[slot,yaw]
        self_rows.append(dict(slot=slot,yaw=yaw,**self_clear(prepared(p,.3302,err))))
        for group,tg in targets.items():
            ctx.targets=tg
            for pitch in (range(-20,26,5) if group=='pitch' else [0]):
                tr=np.eye(4) if group=='body' else np.linalg.inv(np.asarray(rigidtr(yaw,pitch if group=='pitch' else 0)))
                hit=ctx.clear(p@tr[:3,:3].T+tr[:3,3],chord_error=err,radius=.3302);checks+=1
                if hit:hits.append(dict(slot=slot,yaw=yaw,pitch=pitch,group=group,**hit))
    for yaw in range(-60,61,10):
        items={s:prepared(curves[s,yaw],nr['OD_mm'][s]/2,errors[s,yaw]) for s in range(11)}
        for a,b in itertools.combinations(items,2):
            if not ({a,b}&{7,10}):continue
            pairs.append(dict(yaw=yaw,a=a,b=b,**pair(items[a],items[b])))
    success=not hits and all(r['status']=='PASS' for r in self_rows+pairs) and min(r['minimum_sampled_bend_mm'] for r in curvature_rows)>=7.
    result=dict(status='PASS' if success else 'BLOCKED',start_z_mm=start,angular_delta_deg=delta,modified_slots=[7,10],
        native_checks=checks,hits=hits,self_checks=self_rows,pair_checks=pairs,curvature=curvature_rows,lengths=lengths,
        needs_constant_length_compensation=True,upper_transitions='NOT_TESTED')
    results.append(result);print('OUTLET_STEERING',start,result['status'],len(hits),min(r['minimum_sampled_bend_mm'] for r in curvature_rows),flush=True)
    if success:
        arrays={f'wire{s}_y{y}':p for (s,y),p in curves.items()};break
ctx.targets=native;ctx.assert_unchanged()
if arrays:np.savez_compressed(OUT/'neck_candidates.npz',**arrays)
inputs=[OLD/'neck_screen.json',OLD/'neck_candidates.npz',HERE/'route_family.py',HERE/'neck_curve_geometry.py',HERE/'curve_clearance.py']
r=dict(status='PASS' if arrays else 'BLOCKED',sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},
    results=results,maximum_baseline_replay_delta_mm=max(replay),curve_sha256=sha(OUT/'neck_candidates.npz') if arrays else None,
    OD_mm=nr['OD_mm'],unchanged_neck_pairs_reused=468,
    scope='Local geometric screening only, two upper neck paths steered above the recorded start height; lower samples and all solids unchanged. Variable path length must be compensated before full dynamic route acceptance.',
    main_changed=False,full_harness='BLOCKED',constant_length='BLOCKED',supplier_cut_lengths_released=False,
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'neck_screen.json').write_text(json.dumps(r,indent=2)+'\n');print('OUTLET_STEERING_DONE',r['status'],r['elapsed_s'],flush=True)

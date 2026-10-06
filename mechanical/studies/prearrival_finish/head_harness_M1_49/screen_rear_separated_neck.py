"""Separate the two thicker power paths within the late rear outlet study, preserving every lower entry sample.

No printed/hardware change. This is a local shape screen, not a constant-length
whole-harness claim: any extra yaw-dependent path length must be compensated
in the upper service loop before that route can be accepted.
"""
from pathlib import Path
import itertools,json,math,sys,time
from numpy.polynomial import polynomial as poly
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
OLD=HERE/'remaining_routes/left_tall_balanced';OUT=HERE/'remaining_routes/rear_separated_neck';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from route_family import family,profile,rotate
from neck_curve_geometry import absmax
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
changed=[4,5,7,8,9,10];turns={4:87.,5:82.,7:90.,8:89.,9:85.,10:90.}
for start,dip in [(171.,.7),(171.,.9),(171.,1.1)]:
    curves={};errors={};curvature_rows=[];lengths=[]
    for slot,row in itertools.product(range(11),source_rows):
        yaw=row['yaw_deg'];original=old[f'z149.0_dip0.6_wire{slot}_y{yaw}']
        if slot not in changed:curves[slot,yaw]=original;errors[slot,yaw]=lane['chord_error_mm'];continue
        p=row['points'];z=p[:,2];base=rotate(p,angles[slot]);j=int(np.searchsorted(original[:,2],149.))
        replay_delta=float(np.max(np.linalg.norm(original[j:]-base,axis=1)));assert replay_delta<1e-8;replay.append(replay_delta)
        u=np.clip((z-start)/(200.-start),0.,1.);active=(z>start)&(z<200.)
        w=10*u**3-15*u**4+6*u**5
        wd=np.where(active,(30*u**2-60*u**3+30*u**4)/(200.-start),0.)
        wdd=np.where(active,(60*u-180*u**2+120*u**3)/(200.-start)**2,0.)
        gamma=math.radians(turns[slot]);t=(z-149.)/51.;co=np.array(row['coefficients'])
        theta=poly.polyval(t,co)+math.radians(angles[slot])+gamma*w
        td=poly.polyval(t,poly.polyder(co))/51.+gamma*wd
        tdd=poly.polyval(t,poly.polyder(co,2))/51.**2+gamma*wdd
        r,rd,rdd=profile(z,10.6,15.2,173.,30.,.6)
        extra_dip=dip if slot==4 else 0.
        v=np.clip((z-161.)/16.,0.,1.);act=(z>161.)&(z<177.)
        rw=10*v**3-15*v**4+6*v**5
        rwd=np.where(act,(30*v**2-60*v**3+30*v**4)/16.,0.)
        rwdd=np.where(act,(60*v-180*v**2+120*v**3)/16.**2,0.)
        r-=extra_dip*rw;rd-=extra_dip*rwd;rdd-=extra_dip*rwdd
        cs,sn=np.cos(theta),np.sin(theta);q=np.c_[r*cs,r*sn,z]
        vel=np.c_[rd*cs-r*sn*td,rd*sn+r*cs*td,np.ones(len(z))]
        acc=np.c_[(rdd-r*td**2)*cs-(2*rd*td+r*tdd)*sn,(rdd-r*td**2)*sn+(2*rd*td+r*tdd)*cs,np.zeros(len(z))]
        if slot==5:
            v=np.clip((z-187.)/13.,0.,1.);act=(z>187.)&(z<200.)
            tw=10*v**3-15*v**4+6*v**5
            twd=np.where(act,(30*v**2-60*v**3+30*v**4)/13.,0.)
            twdd=np.where(act,(60*v-180*v**2+120*v**3)/13.**2,0.)
            angle=math.radians(yaw);direction=np.array([-2.*math.cos(angle)+1.5*math.sin(angle),-2.*math.sin(angle)-1.5*math.cos(angle),0.])
            q+=tw[:,None]*direction;vel+=twd[:,None]*direction;acc+=twdd[:,None]*direction
        k=np.linalg.norm(np.cross(vel,acc),axis=1)/np.linalg.norm(vel,axis=1)**3;bend=float(1/k.max())
        half=math.sqrt(30.*4.6-4.6**2/4)
        maxrd=half/math.sqrt(30.**2-half**2)+1.875*.6/8+extra_dip*1.875/16.
        maxrdd=30.**2/(30.**2-half**2)**1.5+5.774*.6/64+extra_dip*5.774/16.**2
        maxthd=absmax(poly.polyder(co))/51.+abs(gamma)*1.875/(200.-start)
        maxthdd=absmax(poly.polyder(co,2))/51.**2+abs(gamma)*5.774/(200.-start)**2
        bound=maxrdd+15.2*maxthd**2+2*maxrd*maxthd+15.2*maxthdd
        if slot==5:bound+=2.5*5.774/13.**2
        error=float(bound*np.diff(z).max()**2/8)
        combined=np.vstack([original[:j],q]);assert np.max(np.linalg.norm(combined[combined[:,2]<=161.]-original[original[:,2]<=161.],axis=1))<1e-8
        curves[slot,yaw]=combined;errors[slot,yaw]=error
        curvature_rows.append(dict(slot=slot,yaw=yaw,minimum_sampled_bend_mm=bend,chord_error_mm=error))
        lengths.append(dict(slot=slot,yaw=yaw,polygon_length_mm=float(np.linalg.norm(np.diff(combined,axis=0),axis=1).sum()),
            delta_from_original_mm=float(np.linalg.norm(np.diff(combined,axis=0),axis=1).sum()-np.linalg.norm(np.diff(original,axis=0),axis=1).sum())))
    hits=[];checks=0;self_rows=[];pairs=[]
    for slot,yaw in itertools.product(changed,range(-60,61,10)):
        p=curves[slot,yaw];err=errors[slot,yaw]
        self_rows.append(dict(slot=slot,yaw=yaw,**self_clear(prepared(p,nr['OD_mm'][slot]/2,err))))
        for group,tg in targets.items():
            ctx.targets=tg
            for pitch in (range(-20,26,5) if group=='pitch' else [0]):
                tr=np.eye(4) if group=='body' else np.linalg.inv(np.asarray(rigidtr(yaw,pitch if group=='pitch' else 0)))
                hit=ctx.clear(p@tr[:3,:3].T+tr[:3,3],chord_error=err,radius=nr['OD_mm'][slot]/2);checks+=1
                if hit:hits.append(dict(slot=slot,yaw=yaw,pitch=pitch,group=group,**hit))
    for yaw in range(-60,61,10):
        items={s:prepared(curves[s,yaw],nr['OD_mm'][s]/2,errors[s,yaw]) for s in range(11)}
        for a,b in itertools.combinations(items,2):
            if not ({a,b}&set(changed)):continue
            pairs.append(dict(yaw=yaw,a=a,b=b,**pair(items[a],items[b])))
    assert len(pairs)==585 and len(self_rows)==78 and checks==936
    success=not hits and all(r['status']=='PASS' for r in self_rows+pairs) and min(r['minimum_sampled_bend_mm'] for r in curvature_rows)>=7.
    result=dict(status='PASS' if success else 'BLOCKED',start_z_mm=start,nominal_turns_deg=turns,power4_extra_radial_dip_mm=dip,power5_local_xy_offset_mm=[-2.,-1.5],unchanged_lower_through_z_mm=161.,modified_slots=changed,
        native_checks=checks,hits=hits,self_checks=self_rows,pair_checks=pairs,curvature=curvature_rows,lengths=lengths,
        needs_constant_length_compensation=True,upper_transitions='NOT_TESTED')
    results.append(result);print('REAR_SEPARATED',start,dip,result['status'],len(hits),min(r['minimum_sampled_bend_mm'] for r in curvature_rows),flush=True)
    if success:
        arrays={f'wire{s}_y{y}':p for (s,y),p in curves.items()};break
ctx.targets=native;ctx.assert_unchanged()
if arrays:np.savez_compressed(OUT/'neck_candidates.npz',**arrays)
inputs=[OLD/'neck_screen.json',OLD/'neck_candidates.npz',HERE/'route_family.py',ROOT/'mechanical/scripts/neck_curve_geometry.py',HERE/'curve_clearance.py']
r=dict(status='PASS' if arrays else 'BLOCKED',sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},
    results=results,maximum_baseline_replay_delta_mm=max(replay),curve_sha256=sha(OUT/'neck_candidates.npz') if arrays else None,
    OD_mm=nr['OD_mm'],unchanged_neck_pairs_reused=130,
    scope='Local geometric screening only, Six upper neck paths steered above the recorded start height; lower samples and all solids unchanged. Variable path length must be compensated before full dynamic route acceptance.',
    main_changed=False,full_harness='BLOCKED',constant_length='BLOCKED',supplier_cut_lengths_released=False,
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'neck_screen.json').write_text(json.dumps(r,indent=2)+'\n');print('REAR_SEPARATED_DONE',r['status'],r['elapsed_s'],flush=True)

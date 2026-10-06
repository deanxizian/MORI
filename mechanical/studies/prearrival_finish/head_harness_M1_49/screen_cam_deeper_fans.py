"""Rearward-loop multi-stage CAM fans with canonical obstacle labels.

Only route centre lines are generated. All four loops use the same 4 mm
leading-straight trim. Existing reports are immutable; this reports fan pin
and obstacle loop pin explicitly, avoiding the old symmetric-cache labels.
"""
from pathlib import Path
import argparse,collections,itertools,json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
parser=argparse.ArgumentParser();parser.add_argument('--case',choices=['rear5','rear7'],default='rear7')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
CASE=args.case
OUT=HERE/'remaining_routes/cam_rearward_fans'/(CASE+'_multistage');OUT.mkdir(exist_ok=True)
LOOP=HERE/'remaining_routes/cam_rearward_loops';LANE=HERE/'remaining_routes/left_tall_balanced'
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from validate import rigidtr
from upper_multistage_geometry import make
from upper_pack_geometry import trimmed,refined
from curve_clearance import prepared,self_clear
from bounded_curve_checks import pair_threshold
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text())
nr=read(LANE/'neck_screen.json');lr=read(LOOP/'loop_screen.json');pr=read(LOOP/'refined_pairs.json')
for report in [nr,lr,pr]:
    for name,h in {**report['sources'],**report['inputs']}.items():assert sha(ROOT/name)==h,name
assert nr['status']==pr['status']=='PASS'
for folder,name,r in [(LOOP,'curves.npz',lr),(LANE,'neck_candidates.npz',nr)]:assert sha(folder/name)==r['curve_sha256']
loops=np.load(LOOP/'curves.npz');neck=np.load(LANE/'neck_candidates.npz')
slot_for={1:9,2:8,3:7,4:10};lane=next(r for r in nr['results'] if r['status']=='PASS')
raw_up={(pin,pitch):trimmed(loops[f'{CASE}_pin{pin}_pitch{pitch}'],4.) for pin,pitch in itertools.product(range(1,5),range(-20,26,5))}
up={k:prepared(refined(p),.3302,.0003) for k,p in raw_up.items()}
raw_low={};low={}
for yaw,slot in itertools.product(range(-60,61,10),range(11)):
    inv=np.linalg.inv(np.asarray(rigidtr(yaw,0)));p=neck[f'z149.0_dip0.6_wire{slot}_y{yaw}'];p=p@inv[:3,:3].T+inv[:3,3]
    raw_low[slot,yaw]=p;low[slot,yaw]=prepared(p,nr['OD_mm'][slot]/2,lane['chord_error_mm'])
native=ctx.targets;groups={n:s.group if s.group in ['yaw','pitch'] else 'body' for n,s in ctx.ss.items()}
targets={g:{n:t for n,t in native.items() if groups.get(n,'body')==g} for g in ['body','yaw','pitch']}
checks=collections.Counter();diagnostics=[];arrays={};rows=[]
def curve_checks(p,m,native_reuse=False):
    pin=m['pin'];err=m['chord_error_mm'];item=prepared(refined(p),.3302,err)
    # Explicit source/obstacle pin labels. Threshold witness can be on either curve.
    for other,pitch in itertools.product(range(1,5),range(-20,26,5)):
        if other==pin:continue
        r=pair_threshold(item,up[other,pitch]);checks['cross_loop']+=1
        if r['status']!='PASS':return dict(kind='fan_to_other_loop',fan_pin=pin,loop_pin=other,pitch=pitch,**r)
    for pitch in range(-20,26,5):
        u=raw_up[pin,pitch];assert np.linalg.norm(p[-1]-u[0])<1e-5
        r=self_clear(prepared(np.vstack([p,u[1:]]),.3302,max(err,.0003)),indices=range(len(p)));checks['own_upper_self']+=1
        if r['status']!='PASS':return dict(kind='own_upper_self',pin=pin,pitch=pitch,**r)
    for yaw,slot in itertools.product(range(-60,61,10),range(11)):
        if slot==slot_for[pin]:continue
        r=pair_threshold(item,low[slot,yaw]);checks['fan_to_other_neck']+=1
        if r['status']!='PASS':return dict(kind='fan_to_other_neck',pin=pin,slot=slot,yaw=yaw,**r)
    for yaw in range(-60,61,10):
        l=raw_low[slot_for[pin],yaw];assert np.linalg.norm(l[-1]-p[0])<1e-5
        q=np.vstack([l,p[1:]])
        r=self_clear(prepared(q,.3302,max(err,lane['chord_error_mm'])),indices=range(len(l)-1,len(q)));checks['own_lower_self']+=1
        if r['status']!='PASS':return dict(kind='own_lower_self',pin=pin,yaw=yaw,**r)
    if not native_reuse:
        ctx.targets=native;hit=ctx.clear(p,radius=.3302,chord_error=err);checks['native']+=1
        if hit:return dict(kind='native',**hit)
        for group,t in targets.items():
            ctx.targets=t
            for yaw,pitch in itertools.product(range(-60,61,10) if group=='body' else [0],range(-20,26,5) if group=='pitch' else [0]):
                tr=np.asarray(rigidtr(yaw,0)) if group=='body' else np.eye(4) if group=='yaw' else np.linalg.inv(np.asarray(rigidtr(0,pitch)))
                hit=ctx.clear(p@tr[:3,:3].T+tr[:3,3],radius=.3302,chord_error=err);checks['native']+=1
                if hit:return dict(kind='native',group=group,yaw=yaw,pitch=pitch,**hit)
    return None
for pin in range(1,5):
    start=neck[f'z149.0_dip0.6_wire{slot_for[pin]}_y0'][-1];anchor=raw_up[pin,0][0]
    accepted=[];failures=[];seen=set();old_counts=collections.Counter()
    kept_per_bucket=collections.Counter()
    for wy,lead,radius,mode in itertools.product([7.,8.,9.,10.,11.],[0.,2.,4.,6.,9.,12.,15.],[7.,8.,10.],['yx','xy','direct']):
        bucket=(wy,mode)
        if kept_per_bucket[bucket]>=3:continue
        wps=([[float(start[0]),wy],[float(anchor[0]),wy]] if mode=='yx' else [[float(anchor[0]),float(start[1])],[float(anchor[0]),wy]]) if mode!='direct' else [[float(anchor[0]),wy]]
        sig=(tuple(map(tuple,wps)),lead,radius)
        if sig in seen:continue
        seen.add(sig);built=make(start,anchor,radius,lead,wps)
        if built is None:checks['height_infeasible']+=1;continue
        p,length,err=built;m=dict(pin=pin,slot=slot_for[pin],loop_case=CASE,radius_mm=radius,lead_mm=lead,anchor_trim_mm=4.,waypoints_xy_mm=wps,
            length_mm=length,chord_error_mm=err,start_mm=start.tolist(),end_mm=anchor.tolist())
        bad=curve_checks(p,m)
        if bad:failures.append(dict(m,failure=bad));continue
        key=f'{CASE}_multi_pin{pin}_{len(accepted)}';arrays[key]=p;accepted.append(dict(m,id=key));kept_per_bucket[bucket]+=1
    rows.append(dict(pin=pin,candidates=accepted,failures=failures,old_counts=dict(old_counts)))
    print('MULTISTAGE_OPTIONS',pin,len(accepted),len(failures),flush=True)
ctx.targets=native;ctx.assert_unchanged();np.savez_compressed(OUT/'fan_candidates.npz',**arrays)
inputs=[LOOP/'loop_screen.json',LOOP/'curves.npz',LOOP/'refined_pairs.json',LANE/'neck_screen.json',LANE/'neck_candidates.npz',
    HERE/'upper_curve_geometry.py',HERE/'upper_multistage_geometry.py',HERE/'upper_pack_geometry.py',HERE/'curve_clearance.py',HERE/'bounded_curve_checks.py']
r=dict(status='PASS' if all(r['candidates'] for r in rows) else 'BLOCKED',sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},
    rows=rows,loop_case=CASE,checks=dict(checks),canonical_old_diagnostics=diagnostics,
    diagnostic_correction='Old pack reports cached a sorted pair but did not normalize directional operands. Their symmetric decisions remain valid; directional labels are not authoritative. This report directly labels the fan and obstacle loop pins.',
    curve_sha256=sha(OUT/'fan_candidates.npz'),main_changed=False,full_harness='BLOCKED',wire_wire='NOT_TESTED between accepted fans',
    scope='Native, own joined self, other-loop and neck checks for each transition, all loop trims fixed at 4 mm. Joint fan packing remains required.',
    wire_OD_mm=.6604,required_gap_mm=.3,script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'fan_screen.json').write_text(json.dumps(r,indent=2)+'\n');print('MULTISTAGE_DONE',r['status'],r['elapsed_s'],flush=True)

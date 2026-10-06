"""Compose a proven CAM upper candidate with the unapproved C6 lower nine.

The shared neck samples must match. Fresh comparisons cover every new upper
piece against every body prefix; all existing native and mutual proofs are
hash guarded. This is not adoption, manufacturing data or a complete harness.
"""
from pathlib import Path
import argparse,itertools,json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
parser=argparse.ArgumentParser();parser.add_argument('--family',default='rear3_multistage')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
assert '/' not in args.family and '..' not in args.family
BASE=HERE/'remaining_routes/cam_rearward_fans'/args.family;UP=BASE/'local_join';OUT=BASE/'c6_join';OUT.mkdir(exist_ok=True)
LOW=HERE/'remaining_routes/c6_left_slot_entry';LANE=HERE/'remaining_routes/left_tall_balanced'
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from curve_clearance import prepared,pair
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text())
ur=read(UP/'local_join_screen.json');lr=read(LOW/'combined/lower_nine_screen.json');nr=read(LANE/'neck_screen.json');gr=read(LOW/'geometry_review.json')
assert ur['status']==lr['status']==nr['status']==gr['status']=='PASS'
assert lr['approved'] is False and not lr['main_changed'] and not ur['main_changed']
assert gr['added_volume_mm3']==0. and gr['construction']['changed_existing_ids']==['Yaw_Base']
assert ur['sources']==lr['sources']==ctx.sources
for report in [ur,lr,nr,gr]:
    for f,h in {**report.get('sources',{}),**report.get('inputs',{})}.items():assert sha(ROOT/f)==h,f
for path,key,r in [(UP/'cam_local_joined.npz','curve_sha256',ur),(LOW/'combined/lower_nine_candidates.npz','curve_sha256',lr),(LANE/'neck_candidates.npz','curve_sha256',nr)]:assert sha(path)==r[key]
assert len(ur['whole_pairs'])==780 and all(r['status']=='PASS' for r in ur['whole_pairs'])
assert len(lr['whole_pairs'])==715 and all(r['status']=='PASS' for r in lr['whole_pairs'])
upper=np.load(UP/'cam_local_joined.npz');lower=np.load(LOW/'combined/lower_nine_candidates.npz');neck=np.load(LANE/'neck_candidates.npz')
row_for={r['endpoint']:r for r in lr['selected']};slot_for={1:9,2:8,3:7,4:10}
parts={};prefixes={};joins=[];samples=[];fresh=[];arrays={};lengths=[]
lane=next(r for r in nr['results'] if r['status']=='PASS')
error=max(lane['chord_error_mm'],.0003,max(r['chord_error_mm'] for r in ur['selected']))
for name,row in row_for.items():
    # Prefix/neck boundary comes from the recorded entry height, not a guessed sample index.
    for yaw in range(-60,61,10):
        l=lower[f'{name}_y{yaw}'];n=neck[f'z149.0_dip0.6_wire{row["slot"]}_y{yaw}'];z=row.get('entry_z_mm',142.)
        a=n[0].copy();a[2]=z;tail=np.vstack([a,n[n[:,2]>z+1e-8]])
        assert len(l)>=len(tail)
        delta=float(np.max(np.linalg.norm(l[-len(tail):]-tail,axis=1)));assert delta<1e-5
        prefix=l[:len(l)-len(tail)+1];prefixes[name,yaw]=prepared(prefix,row['OD_mm']/2,max(row['chord_error_mm'],lane['chord_error_mm']))
        samples.append(dict(endpoint=name,yaw=yaw,shared_tail_max_delta_mm=delta,prefix_max_z_mm=float(prefix[:,2].max())))
for pin in range(1,5):
    values=[]
    for yaw,pitch in itertools.product(range(-60,61,10),range(-20,26,5)):
        n=neck[f'z149.0_dip0.6_wire{slot_for[pin]}_y{yaw}'];u=upper[f'pin{pin}_y{yaw}_p{pitch}'];l=lower[f'CAM_{pin}_y{yaw}']
        delta=float(np.max(np.linalg.norm(u[:len(n)]-n,axis=1)));assert delta<1e-5
        addition=u[len(n)-1:];assert np.linalg.norm(addition[0]-l[-1])<1e-5
        q=np.vstack([l,addition[1:]]);arrays[f'CAM_{pin}_y{yaw}_p{pitch}']=q
        values.append(float(np.linalg.norm(np.diff(q,axis=0),axis=1).sum()))
        joins.append(dict(pin=pin,yaw=yaw,pitch=pitch,shared_neck_max_delta_mm=delta,join_error_mm=float(np.linalg.norm(addition[0]-l[-1]))))
        item=prepared(addition,.3302,error)
        for name,row in row_for.items():
            r=pair(item,prefixes[name,yaw]);fresh.append(dict(upper_pin=pin,body_prefix=name,yaw=yaw,pitch=pitch,**r))
    lengths.append(dict(pin=pin,polygon_min_mm=min(values),polygon_max_mm=max(values),not_supplier_cut_length=True))
for name in row_for:
    if not name.startswith('CAM_'):
        for yaw in range(-60,61,10):arrays[f'{name}_y{yaw}']=lower[f'{name}_y{yaw}']
for slot in [3,6]:
    for yaw in range(-60,61,10):arrays[f'SPK_reservation_{slot}_y{yaw}']=neck[f'z149.0_dip0.6_wire{slot}_y{yaw}']
ctx.assert_unchanged();passed=len(fresh)==4680 and all(r['status']=='PASS' for r in fresh)
if passed:np.savez_compressed(OUT/'candidate_curves.npz',**arrays)
inputs=[UP/'local_join_screen.json',UP/'cam_local_joined.npz',LOW/'combined/lower_nine_screen.json',LOW/'combined/lower_nine_candidates.npz',LOW/'geometry_review.json',
    LOW/'Yaw_Base_candidate.npz',LANE/'neck_screen.json',LANE/'neck_candidates.npz',HERE/'curve_clearance.py']
r=dict(status='PASS' if passed else 'BLOCKED',sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},
    upper_family=args.family,shared_samples=samples,joins=joins,upper_to_body_prefix=fresh,lengths=lengths,
    proof_reuse=dict(lower_nine_plus_two_reservations=715,upper_four_whole_pairs=780,
        upper_fan_to_other_neck='Checked by selected candidates in the hash-verified upper report',
        loop_to_all_neck=len(ur['upper_lower']),upper_native_and_self='Checked by hash-verified upper input reports',
        lower_native_and_self='Checked on unapproved C6 in hash-verified lower input reports',
        fresh_crosses='Each new upper fan/loop is freshly compared with each of the nine body prefixes; includes each own prefix'),
    scope='Four CAM reference routes continuous from body to estimated CAM endpoints, together with five other lower wires and two local speaker reservations; 13 yaw x 10 pitch samples. This remains an independent unapproved C6 candidate.',
    curve_sha256=sha(OUT/'candidate_curves.npz') if passed else None,approved=False,C6_main_applied=False,main_changed=False,
    full_harness='BLOCKED',other_upper_endpoints='NOT_TESTED',anchors='NOT_TESTED',wired_assembly='NOT_TESTED',
    physical_qualification='NOT_TESTED',supplier_cut_lengths_released=False,script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'join_review.json').write_text(json.dumps(r,indent=2)+'\n');print('C6_CAM_JOIN_DONE',r['status'],len(fresh),r['elapsed_s'],flush=True)

"""Conditionally join current CAM routes to the unchanged, unapproved C6 prefixes."""
from pathlib import Path
import itertools,json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes';LOW=BASE/'c6_left_slot_entry';N=BASE/'neck_side_tail_gentle';F=BASE/'cam_side_fans';LANE=BASE/'left_tall_balanced'
OUT=F/'c6_join';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from validate import rigidtr
from curve_clearance import prepared
from curve_self_partition import self_clear
from bounded_curve_checks import pair_threshold
from upper_pack_geometry import refined
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text())
fr=read(F/'fan_screen.json');nr=read(N/'join_screen.json');lr=read(LOW/'combined/lower_nine_screen.json');lane=read(LANE/'neck_screen.json');gr=read(LOW/'geometry_review.json')
reports=[fr,nr,lr,lane,gr]
for r in reports:
    assert r['status']=='PASS'
    for f,h in {**r.get('sources',{}),**r.get('inputs',{})}.items():assert sha(ROOT/f)==h,f
assert not lr['approved'] and not lr['main_changed']
assert gr['added_volume_mm3']==0. and gr['construction']['changed_existing_ids']==['Yaw_Base']
assert len(fr['joined_pairs'])==780 and all(r['status']=='PASS' for r in fr['joined_pairs'])
assert len(lr['whole_pairs'])==715 and all(r['status']=='PASS' for r in lr['whole_pairs'])
for folder,name,report,key in [(N,'neck_curves.npz',nr,'neck_curve_sha256'),(F,'joined_curves.npz',fr,'joined_curve_sha256'),(LOW/'combined','lower_nine_candidates.npz',lr,'curve_sha256'),(LANE,'neck_candidates.npz',lane,'curve_sha256')]:assert sha(folder/name)==report[key]
nc=np.load(N/'neck_curves.npz');cam=np.load(F/'joined_curves.npz');lower=np.load(LOW/'combined/lower_nine_candidates.npz');old=np.load(LANE/'neck_candidates.npz')
yaws=range(-60,61,10);pitches=range(-20,26,5);rows={r['endpoint']:r for r in lr['selected']};slots={r['slot']:name for name,r in rows.items()}
prefix={};prefix_items={};shared=[];fresh=[];joined={};self_rows=[];lengths=[];join_errors=[]
for name,row in rows.items():
    for yaw in yaws:
        n=old[f'z149.0_dip0.6_wire{row["slot"]}_y{yaw}'];l=lower[f'{name}_y{yaw}'];z=row.get('entry_z_mm',142.)
        a=n[0].copy();a[2]=z;tail=np.vstack([a,n[n[:,2]>z+1e-8]])
        delta=float(np.max(np.linalg.norm(l[-len(tail):]-tail,axis=1)));assert delta<1e-5
        pre=l[:len(l)-len(tail)+1];prefix[name,yaw]=pre
        prefix_items[name,yaw]=prepared(refined(pre,.01),row['OD_mm']/2,max(.0003,row['chord_error_mm']))
        shared.append(dict(endpoint=name,yaw=yaw,old_prefix_reconstruction_max_delta_mm=delta,entry_z_mm=z,prefix_max_z_mm=float(pre[:,2].max())))
for yaw in yaws:
    for slot in range(11):
        p=nc[f'wire{slot}_y{yaw}'];item=prepared(refined(p,.01),nr['OD_mm'][slot]/2,.0003)
        for name,row in rows.items():
            if row['slot']==slot:continue
            fresh.append(dict(scope='new_neck_vs_other_body_prefix',slot=slot,endpoint=name,yaw=yaw,**pair_threshold(item,prefix_items[name,yaw])))
assert len(fresh)==1170
for name,row in rows.items():
    slot=row['slot'];values=[]
    for yaw in yaws:
        pre=prefix[name,yaw];z=row.get('entry_z_mm',142.);n=nc[f'wire{slot}_y{yaw}']
        for pitch in (pitches if name.startswith('CAM_') else [0]):
            if name.startswith('CAM_'):
                pin=int(name.split('_')[-1]);mat=np.asarray(rigidtr(yaw,0));u=cam[f'pin{pin}_y{yaw}_p{pitch}']@mat[:3,:3].T+mat[:3,3]
                delta=float(np.max(np.linalg.norm(u[:len(n)]-n,axis=1)));assert delta<1e-5
                # The rest is not monotonic in Z; trim only inside the known neck segment.
                j=int(np.flatnonzero(n[:,2]>z+1e-8)[0]);a=n[0].copy();a[2]=z;remaining=np.vstack([a,u[j:]])
                addition=u[len(n)-1:];item=prepared(refined(addition,.01),.3302,.0003)
                for peer in rows:fresh.append(dict(scope='new_upper_vs_body_prefix',pin=pin,endpoint=peer,yaw=yaw,pitch=pitch,**pair_threshold(item,prefix_items[peer,yaw])))
            else:
                a=n[0].copy();a[2]=z;remaining=np.vstack([a,n[n[:,2]>z+1e-8]])
            error=float(np.linalg.norm(pre[-1]-remaining[0]));assert error<1e-5
            p=np.vstack([pre,remaining[1:]]);key=f'{name}_y{yaw}'+(f'_p{pitch}' if name.startswith('CAM_') else '')
            joined[key]=p;join_errors.append(dict(endpoint=name,yaw=yaw,pitch=pitch,error_mm=error))
            values.append(float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum()))
            self_rows.append(dict(endpoint=name,yaw=yaw,pitch=pitch,**self_clear(prepared(refined(p,.01),row['OD_mm']/2,.0003))))
    lengths.append(dict(endpoint=name,min_mm=min(values),max_mm=max(values),range_mm=max(values)-min(values),not_supplier_cut_length=True))
    print('C6_SIDE_JOIN',name,'self_failures',sum(r['status']!='PASS' for r in self_rows),'fresh_pair_failures',sum(r['status']!='PASS' for r in fresh),flush=True)
for slot in [3,6]:
    for yaw in yaws:joined[f'SPK_reservation_{slot}_y{yaw}']=nc[f'wire{slot}_y{yaw}']
assert len(fresh)==5850 and len(self_rows)==585
cam_lengths=[r for r in lengths if r['endpoint'].startswith('CAM_')]
ok=all(r['status']=='PASS' for r in fresh+self_rows) and all(r['range_mm']<.01 for r in cam_lengths)
ctx.assert_unchanged()
if ok:np.savez_compressed(OUT/'candidate_curves.npz',**joined)
inputs=[F/'fan_screen.json',F/'joined_curves.npz',N/'join_screen.json',N/'neck_curves.npz',LOW/'combined/lower_nine_screen.json',LOW/'combined/lower_nine_candidates.npz',LOW/'geometry_review.json',LOW/'Yaw_Base_candidate.npz',LANE/'neck_screen.json',LANE/'neck_candidates.npz',HERE/'curve_clearance.py',HERE/'curve_self_partition.py',HERE/'bounded_curve_checks.py',HERE/'upper_pack_geometry.py']
r=dict(status='PASS' if ok else 'BLOCKED',sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},shared_prefix_evidence=shared,
    fresh_cross_pairs=fresh,self_checks=self_rows,joins=join_errors,lengths=lengths,
    curve_sha256=sha(OUT/'candidate_curves.npz') if ok else None,approved=False,C6_main_applied=False,main_changed=False,full_harness='BLOCKED',supplier_cut_lengths_released=False,
    proof_reuse=dict(prefix_native='Identical C6 lower-nine prefixes; approved=False',prefix_mutual='Unchanged prefixes bounded by the prior715 whole-lower-pair checks',
        new_neck='neck_side_tail_gentle native and715 composed mutual checks',upper='cam_side_fans and cam_side_following: native, fan/neck, fan/upper, neck/upper, full4-CAM mutual checks',
        native_C6='New upper and neck clear unchanged native model. Unapproved C6 removes material only and cannot introduce a native solid collision.',
        fresh='1170 neck-to-other-body-prefix +4680 upper-to-all-body-prefix checks;585 full remote-self checks'),
    scope='Conditional C6 candidate: four continuous motion-J5 to estimated CAM reference ports through130 poses; five additional lower lines and two speaker neck reservations. No C6 adoption.',
    open=['C6 user approval','Other upper endpoints','Real anchoring and strain relief','FPC/FFC','Wired assembly','Supplier terminal and physical qualification'],
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'join_review.json').write_text(json.dumps(r,indent=2)+'\n');print('C6_SIDE_JOIN_DONE',r['status'],r['elapsed_s'],flush=True)

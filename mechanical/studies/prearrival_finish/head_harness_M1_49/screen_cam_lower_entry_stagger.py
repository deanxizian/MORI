"""Separate CAM3/4 turn heights below the unchanged annular shoulder."""
from pathlib import Path
import json,sys,time,collections
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
OUT=HERE/'remaining_routes/cam_lower_entry_stagger';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE));sys.path.insert(0,str(HERE.parent/'harness_A8/body_prefix_v2'))
from harness_context import Context,np,sha
from body_arc_geometry import rebuild,line
from curve_clearance import prepared
from bounded_curve_checks import pair_threshold
ctx=Context();start=time.time()
base=HERE/'remaining_routes/cam_four_order_expanded';local=HERE/'remaining_routes/left_lower_entry'
src=json.loads((base/'body_prefix_screen.json').read_text());nr=json.loads((local/'neck_screen.json').read_text());lane=nr['results'][0]
for d in [src,nr]:
    assert d['status']=='PASS'
    for f,h in {**d['sources'],**d['inputs']}.items():assert sha(ROOT/f)==h,f
for folder,f,d in [(base,'body_prefix_candidates.npz',src),(local,'neck_candidates.npz',nr)]:assert sha(folder/f)==d['curve_sha256']
old=np.load(base/'body_prefix_candidates.npz');neck=np.load(local/'neck_candidates.npz')
reserves={i:prepared(neck[f'z149.0_dip0.6_wire{i}_y0'],nr['OD_mm'][i]/2,lane['chord_error_mm']) for i in range(11)}
roots={}
for port,prefix,count,OD in [('motion_J5','CAM',4,.6604),('power_J9','P_J9',3,1.1684),('power_J18','P_J18',2,1.1684)]:
    for pin in range(1,count+1):
        p=ctx.port_pins[port]['pins'][str(pin)];roots[f'{prefix}_{pin}']=prepared(line(p,p+[0,0,5]),OD/2,0.)
arrays={};pools=collections.defaultdict(list);fail=collections.Counter();witness={};checks=0
for pin,z in [(1,139.8),(2,140.9)]:
    count=0
    for seed in [r for rows in src['pools'].values() for r in rows if r['pin']==pin]:
        endpoint=seed['endpoint'];q=old[seed['id']][-1];p=ctx.port_pins['motion_J5']['pins'][str(pin)]
        points=rebuild(p,q,seed,z)
        if points is None:continue
        n=int(np.flatnonzero(np.linalg.norm(points[:,:2]-points[0,:2],axis=1)>1e-8)[0])
        err=seed['chord_error_mm'] # prior .06mm bound also covers rebuilt .03mm steps
        hit=ctx.clear(points[:n],radius=.3302,ignore=['Plug_motion_J5']) or ctx.clear(points[n-1:],chord_error=err,radius=.3302);checks+=1
        item=prepared(points,.3302,err)
        if not hit:
            for key,b in {**{'root_'+k:v for k,v in roots.items() if k!=endpoint},**{'neck_'+str(i):v for i,v in reserves.items() if i!=seed['slot']}}.items():
                result=pair_threshold(item,b);checks+=1
                if result['status']!='PASS':hit=dict(object=key,**result);break
        if hit:fail[hit['object']]+=1;witness.setdefault(hit['object'],hit);continue
        key=f'entry{z:g}_'+seed['id'];arrays[key]=points;count+=1
        # Integrate sampled length only for option ordering; not supplier cut length.
        row=dict(seed,id=key,entry_z_mm=z,analytic_length_mm=float(np.linalg.norm(np.diff(points,axis=0),axis=1).sum()),length_method='sampled polyline for search ordering only',source_seed=seed['id'])
        pools[f'CAM_{pin}_entry{z:g}'].append(row)
    print('SMALL_STAGGER_POOL',pin,z,count,flush=True)
ctx.assert_unchanged();np.savez_compressed(OUT/'body_prefix_candidates.npz',**arrays)
result=dict(status='PASS' if arrays else 'BLOCKED',sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in [base/'body_prefix_screen.json',base/'body_prefix_candidates.npz',local/'neck_screen.json',local/'neck_candidates.npz',HERE/'body_arc_geometry.py',HERE/'bounded_curve_checks.py',HERE/'curve_clearance.py',HERE.parent/'harness_A8/body_prefix_v2/curvature_paths.py']},
    pools=dict(pools),checks=checks,fail_counts=dict(fail),first_witness=witness,curve_sha256=sha(OUT/'body_prefix_candidates.npz'),
    scope='Individual CAM1/2 lower entry options at Z139.8/140.9, with unchanged higher approach from real connector roots; no complete nine-wire proof',
    full_harness='BLOCKED',main_changed=False,script_sha256=sha(Path(__file__)),elapsed_s=time.time()-start)
(OUT/'body_prefix_screen.json').write_text(json.dumps(result,indent=2)+'\n');print('SMALL_STAGGER_DONE',result['status'],len(arrays),time.time()-start,flush=True)

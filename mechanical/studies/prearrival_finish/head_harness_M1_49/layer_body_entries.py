"""Compare three exit-lead heights, without modifying any connector or print."""
from pathlib import Path
import sys,json,time
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
sys.path.insert(0,str(HERE.parent/'harness_A8/body_prefix_v2'))
sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from body_curve_geometry import make
ctx=Context();start=time.time()
old=json.loads((HERE/'body_aligned_screen.json').read_text());assert old['status']=='PASS'
for p,h in old['sources'].items():assert sha(PROJECT/p)==h,p
native=np.load(HERE/'body_aligned_candidates.npz');assert sha(HERE/'body_aligned_candidates.npz')==old['curve_sha256']
pins={int(k):v for k,v in ctx.port_pins['motion_J5']['pins'].items()};arrays={};pools={};failed=[]
for key,pool in old['pools'].items():
    accepted=[]
    for row in pool:
        source=make(row,row['body_entry_angle_deg'],pins[row['pin']])
        assert source and source[0].shape==native[row['id']].shape
        assert np.max(np.abs(source[0]-native[row['id']]))<1e-8
        for lead in [5.,6.05,7.1]:
            trial=dict(row,lead_mm=lead,id=row['id']+f'_lead{lead:g}')
            candidate=make(trial,row['body_entry_angle_deg'],pins[row['pin']])
            if candidate is None:failed.append(dict(id=trial['id'],reason='finite tangent family unavailable'));continue
            p,n,L,error=candidate
            hit=ctx.clear(p[:n],ignore=['Plug_motion_J5'],chord_error=error,radius=.6604/2)
            if not hit:hit=ctx.clear(p[n-1:],chord_error=error,radius=.6604/2)
            if hit:failed.append(dict(id=trial['id'],**hit));continue
            arrays[trial['id']]=p
            accepted.append(dict(trial,length_mm=L,chord_error_mm=error,plane_z_mm=float(pins[row['pin']][2]+lead+7)))
    pools[key]=sorted(accepted,key=lambda r:r['length_mm'])
    print('LAYERED_POOL',key,len(accepted),flush=True)
ctx.assert_unchanged();np.savez_compressed(HERE/'body_layered_candidates.npz',**arrays)
result=dict(status='PASS' if all(pools.values()) else 'BLOCKED',scope='Individual body routes with 5/6.05/7.1mm straight lead allocations, not confirmed crimp/strain-relief dimensions',sources=ctx.sources,pools=pools,failed=failed,curve_sha256=sha(HERE/'body_layered_candidates.npz'),inputs={p.name:sha(p) for p in [HERE/'body_aligned_screen.json',HERE/'body_curve_geometry.py',HERE/'spaced_entry_screen.json']},script_sha256=sha(Path(__file__)),main_changed=False,body_wire_packing='NOT_TESTED',body_motion='NOT_TESTED',full_endpoint_routing='BLOCKED',wired_assembly='NOT_TESTED',supplier_cut_lengths_released=False,elapsed_s=time.time()-start)
(HERE/'body_layered_screen.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('LAYERED_BODY_DONE',result['status'],len(arrays),'rejected',len(failed),flush=True)

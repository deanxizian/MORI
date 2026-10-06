"""Screen circular material reserve around each curve against native head.

The reserve is NOT a strength criterion or a designed wall. It tests whether
the prior angular packing could be revised before altering the source shell.
"""
from pathlib import Path
import sys,json,math,time
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'outer_harness_M1_48'));sys.path.insert(0,str(HERE))
from native_context import Context,np,sha
from validate import rigidtr
from tapered_family import rotate
ctx=Context();start=time.time();source=json.loads((HERE/'screen.json').read_text());pack=json.loads((HERE/'packing.json').read_text())
assert sha(HERE/'curves.npz')==source['curves_sha256']
data=np.load(HERE/'curves.npz');fid=pack['family']['id'];chord=pack['family']['chord_error_mm']
nodes=[{k:r[k] for k in ['kind','OD_mm','angle_deg']} for r in source['rows'] if r['family']==fid and r['status']=='PASS']
original=ctx.targets;ctx.targets={n:original[n] for n in ['Head_Front','Head_Rear']}
rows=[]
for reserve in [2.2,1.2]:
    passed=[];fails=[]
    for slot in nodes:
        hit=None
        for yaw in range(-60,61,10):
            p=rotate(data[f'{fid}_y{yaw}'],slot['angle_deg'])
            p=p[(p[:,2]>=160.)&(p[:,2]<=174.)]
            for pitch in range(-20,26,5):
                tr=np.linalg.inv(np.asarray(rigidtr(yaw,pitch)));q=p@tr[:3,:3].T+tr[:3,3]
                hit=ctx.clear(q,chord_error=chord,radius=slot['OD_mm']/2+reserve)
                if hit:hit.update(yaw=yaw,pitch=pitch);break
            if hit:break
        if hit:fails.append(dict(**slot,hit=hit))
        else:passed.append(slot)
    lookup={r['delta_deg']:r['centerline_lower_bound_mm'] for r in pack['pair_bounds']};lookup[0]=0.
    def gap(a,b):
        d=abs(a['angle_deg']-b['angle_deg']);d=min(d,360-d)
        return lookup[d]-(a['OD_mm']+b['OD_mm'])/2
    power=[r for r in passed if r['kind']=='power_sample'];signals=[r for r in passed if r['kind']=='signal']
    calls=0;limit=2000000;solution=None
    def sig(options,chosen,need):
        global calls
        calls+=1
        if calls>limit or len(options)<need:return None
        if not need:return chosen
        for i,a in enumerate(options):
            r=sig([b for b in options[i+1:] if gap(a,b)>=.3],chosen+[a],need-1)
            if r is not None:return r
        return None
    def pick(options,sigs,chosen,need):
        global calls,solution
        calls+=1
        if calls>limit or len(options)<need or len(sigs)<4:return False
        if not need:
            r=sig(sigs,[],4)
            if r is not None:solution=chosen+r;return True
            return False
        for i,a in enumerate(options):
            if pick([b for b in options[i+1:] if gap(a,b)>=.3],[b for b in sigs if gap(a,b)>=.3],chosen+[a],need-1):return True
        return False
    pick(power,signals,[],7)
    row=dict(reserve_mm=reserve,status='PASS' if solution else 'BLOCKED',passed=passed,failed=fails,
        solution=solution,search_nodes=calls,limit_reached=calls>limit)
    rows.append(row);print('WALL_CAPACITY',reserve,'passing',len(passed),'solution',solution,'seconds',round(time.time()-start,1),flush=True)
ctx.targets=original;ctx.assert_unchanged()
out=dict(status='PASS' if any(r['solution'] for r in rows) else 'BLOCKED',
    scope='Local circular wall reserve around wires versus unmodified head shells, not complete printable neck',
    source_main_sha256=ctx.source_hash,script_sha256=sha(__file__),source_screen_sha256=sha(HERE/'screen.json'),
    source_curves_sha256=sha(HERE/'curves.npz'),packing_reference_sha256=sha(HERE/'packing.json'),
    z_range_mm=[160,174],rows=rows,new_strength_standard=False,main_applied=False,
    limits=['Finite sampled curve family only; no proof all original-shell layouts impossible.',
        '1.2mm and2.2mm are comparison reserves, not load-qualified minimum wall limits.',
        'A feasible11wire reserve does not prove one connected simple printed support can be constructed.'],elapsed_s=time.time()-start)
(HERE/'wall_capacity.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')

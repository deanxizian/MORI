"""Recheck selected curves after enabling hidden validation-proxy transforms.

Earlier reports remain historical. Their curve-only spacing proofs are reused
only after exact file and concatenation checks; all solid/motion checks rerun.
"""
from pathlib import Path
import sys,json,time
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import COLS,bpy
from validate import rigidtr
ctx=Context();start=time.time()
read=lambda name:json.loads((HERE/name).read_text())
local=read('spaced_entry_screen.json');packing=read('spaced_local_packing.json')
body=read('body_layered_four_screen.json');oldmotion=read('selected_body_motion.json')
historical_context='533a4c4f0c79967073935cc58bff311df06f690b4963b054cc1622da2a1c0b1d'
for report in [local,packing,body,oldmotion]:
    assert report['status']=='PASS'
    for p,h in report['sources'].items():
        if p=='mechanical/scripts/harness_context.py':assert h==historical_context
        else:assert sha(PROJECT/p)==h,p
neck=np.load(HERE/'spaced_entry_candidates.npz')
prefix=np.load(HERE/'body_layered_candidates.npz')
combined=np.load(HERE/'body_layered_four_candidates.npz')
assert sha(HERE/'spaced_entry_candidates.npz')==local['curve_file_sha256']==packing['curve_sha256']
assert sha(HERE/'body_layered_four_candidates.npz')==body['curve_sha256']
assert sha(HERE/'body_layered_candidates.npz')==oldmotion['source_curve_sha256']
assert sha(HERE/'spaced_entry_screen.json')==packing['input_report_sha256']
assert sha(HERE/'body_layered_four_screen.json')==oldmotion['selected_report_sha256']
for name,h in body['inputs'].items():assert sha(HERE/name)==h,name
for row in body['selected']:
    for yaw in range(-60,61,10):
        expected=np.vstack([prefix[row['id']],neck[f'case0_wire{row["slot"]}_y{yaw}'][1:]])
        assert np.array_equal(expected,combined[f'pin{row["pin"]}_y{yaw}'])
original=ctx.targets
groups={n:s.group if s.group in ['yaw','pitch'] else 'body' for n,s in ctx.ss.items()}
bygroup={g:{n:t for n,t in original.items() if groups.get(n,'body')==g} for g in ['body','yaw','pitch']}
checks={'neck':0,'body':0};hits=[]
ng=local['results'][0]['max_chord_error_mm']
from common import P
for i,slot in enumerate(P['neck_harness_capacity']['wire_allocations']):
    for yaw in range(-60,61,10):
        p=neck[f'case0_wire{i}_y{yaw}']
        for group,targets in bygroup.items():
            ctx.targets=targets
            for pitch in (range(-20,26,5) if group=='pitch' else [0]):
                tr=np.eye(4) if group=='body' else np.linalg.inv(np.asarray(rigidtr(yaw,pitch if group=='pitch' else 0)))
                points=p@tr[:3,:3].T+tr[:3,3]
                issue=ctx.clear(points,chord_error=ng,radius=slot['OD_mm']/2)
                checks['neck']+=1
                if issue:hits.append(dict(segment='neck',wire=i,group=group,yaw=yaw,pitch=pitch,**issue))
    print('RECHECK_NECK',i,len(hits),flush=True)
for row in body['selected']:
    p=prefix[row['id']];lead_points=int(np.ceil(row['lead_mm']/.06))+1
    for group,targets in bygroup.items():
        ctx.targets=targets
        for yaw in ([0] if group=='body' else range(-60,61,10)):
            for pitch in (range(-20,26,5) if group=='pitch' else [0]):
                tr=np.eye(4) if group=='body' else np.linalg.inv(np.asarray(rigidtr(yaw,pitch if group=='pitch' else 0)))
                for section,piece in [('stem',p[:lead_points]),('tail',p[lead_points-1:])]:
                    points=piece@tr[:3,:3].T+tr[:3,3]
                    issue=ctx.clear(points,chord_error=row['chord_error_mm'],radius=.6604/2,
                        ignore=['Plug_motion_J5'] if section=='stem' else [])
                    checks['body']+=1
                    if issue:hits.append(dict(segment='body',pin=row['pin'],group=group,yaw=yaw,pitch=pitch,section=section,**issue))
    print('RECHECK_BODY',row['pin'],len(hits),flush=True)
ctx.targets=original
ctx.assert_unchanged()
# This is the operation that previously revealed stale proxies. It must now
# leave every native solid fingerprint exactly unchanged.
for collection in COLS.values():collection.hide_viewport=False
bpy.context.view_layer.update();ctx.assert_unchanged()
inputs={name:sha(HERE/name) for name in [
    'spaced_entry_screen.json','spaced_local_packing.json','spaced_entry_candidates.npz',
    'body_layered_four_screen.json','body_layered_four_candidates.npz',
    'body_layered_candidates.npz','selected_body_motion.json']}
result=dict(status='PASS' if not hits else 'BLOCKED',sources=ctx.sources,
    source_blend_sha256=ctx.source_hash,inputs=inputs,checks=checks,hits=hits,
    proxy_activation_consistency='PASS',main_changed=False,
    correction='Enable KEEP_OUT before assembled solid baseline, matching main validate.py; historical solid checks superseded by this complete rerun.',
    geometry_check_scope='11 local curves plus four fixed body prefixes, current native/proxy parts and moving groups',
    reused_curve_only_evidence=dict(local_pair_report='spaced_local_packing.json',whole_pair_report='body_layered_four_screen.json',
        reason='Exact curve hashes and each body/neck concatenation checked; pair/self distances depend only on those unchanged curves, not proxy transforms.'),
    full_harness='BLOCKED',anchors='NOT_TESTED',wired_assembly='NOT_TESTED',
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-start)
(HERE/'current_source_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('CURRENT_PROXY_ROUTE_CHECK',result['status'],checks,'hits',len(hits),flush=True)

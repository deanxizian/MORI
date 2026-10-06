"""Current native geometry checks for the four selected fixed body prefixes."""
from pathlib import Path
import sys,json,time
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from harness_context import Context,np,sha
from validate import rigidtr
ctx=Context();start=time.time()
r=json.loads((HERE/'body_layered_four_screen.json').read_text());assert r['status']=='PASS'
for p,h in r['sources'].items():assert sha(PROJECT/p)==h,p
d=np.load(HERE/'body_layered_candidates.npz');original=ctx.targets
groups={n:s.group if s.group in ['yaw','pitch'] else 'body' for n,s in ctx.ss.items()}
bygroup={g:{n:t for n,t in original.items() if groups.get(n,'body')==g} for g in ['body','yaw','pitch']}
checks=0;hits=[]
for row in r['selected']:
    p=d[row['id']];lead_points=int(np.ceil(row['lead_mm']/.06))+1
    # First straight segment has only the intentional source plug departure.
    stem=p[:lead_points];tail=p[lead_points-1:]
    for group,targets in bygroup.items():
        ctx.targets=targets
        for yaw in ([0] if group=='body' else range(-60,61,10)):
            for pitch in (range(-20,26,5) if group=='pitch' else [0]):
                tr=np.eye(4) if group=='body' else np.linalg.inv(np.asarray(rigidtr(yaw,pitch if group=='pitch' else 0)))
                for part,pts in [('stem',stem),('tail',tail)]:
                    points=pts@tr[:3,:3].T+tr[:3,3]
                    issue=ctx.clear(points,chord_error=row['chord_error_mm'],radius=.6604/2,ignore=['Plug_motion_J5'] if part=='stem' else [])
                    checks+=1
                    if issue:hits.append(dict(pin=row['pin'],group=group,yaw=yaw,pitch=pitch,part=part,**issue))
ctx.targets=original;ctx.assert_unchanged()
result=dict(status='PASS' if not hits else 'BLOCKED',sources=ctx.sources,source_blend_sha256=ctx.source_hash,selected_report_sha256=sha(HERE/'body_layered_four_screen.json'),source_curve_sha256=sha(HERE/'body_layered_candidates.npz'),checks=checks,hits=hits,scope='Fixed four-signal body prefixes versus body plus13yaw/130pitch-yaw poses; local neck checked separately against the same current inputs',full_endpoint_routing='BLOCKED',anchors='NOT_TESTED',wired_assembly='NOT_TESTED',script_sha256=sha(Path(__file__)),elapsed_s=time.time()-start)
(HERE/'selected_body_motion.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('SELECTED_BODY_MOTION',result['status'],checks,'hits',len(hits),flush=True)

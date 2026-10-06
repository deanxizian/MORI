"""Screen alternate signal phases through unchanged neck solids, not a redesign."""
from pathlib import Path
import sys,json,time
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from route_family import family,rotate
from validate import rigidtr
ctx=Context();start=time.time();base=family(z0=138,dip=.37,samples=7201)
original=ctx.targets;groups={n:s.group if s.group in ['yaw','pitch'] else 'body' for n,s in ctx.ss.items()}
targets={g:{n:t for n,t in original.items() if groups.get(n,'body')==g} for g in ['body','yaw','pitch']}
report=[];arrays={};checks=0
for angle in [55,60,65,70,75,80,90,100,110,115,120,185,195,205,215,225,240,270,300,325,340,345,350]:
    curves={r['yaw_deg']:rotate(r['points'],angle) for r in base}
    error=max(r['chord_error_mm'] for r in base)
    ctx.targets=original;hit=ctx.clear(curves[0],chord_error=error,radius=.6604/2);checks+=1
    if not hit:
        for yaw,p in curves.items():
            for group,t in targets.items():
                ctx.targets=t
                for pitch in (range(-20,26,5) if group=='pitch' else [0]):
                    tr=np.eye(4) if group=='body' else np.linalg.inv(np.asarray(rigidtr(yaw,pitch if group=='pitch' else 0)))
                    issue=ctx.clear(p@tr[:3,:3].T+tr[:3,3],chord_error=error,radius=.6604/2);checks+=1
                    if issue:hit=dict(issue,yaw=yaw,pitch=pitch,group=group);break
                if hit:break
            if hit:break
    if not hit:arrays.update({f'angle{angle}_y{yaw}':p for yaw,p in curves.items()})
    report.append(dict(angle_deg=angle,status='BLOCKED' if hit else 'PASS',hit=hit))
    print('SIGNAL_PHASE',angle,report[-1]['status'],hit,flush=True)
ctx.targets=original;ctx.assert_unchanged()
np.savez_compressed(HERE/'signal_phase_candidates.npz',**arrays)
out=dict(status='PASS' if arrays else 'BLOCKED',sources=ctx.sources,rows=report,checks=checks,
    curve_sha256=sha(HERE/'signal_phase_candidates.npz'),script_sha256=sha(Path(__file__)),
    family_sha256=sha(HERE/'route_family.py'),chord_error_mm=error,wire_OD_mm=.6604,
    scope='Individual signal phase alternatives; body connection, wire packing and upper fan not checked',
    main_changed=False,full_harness='BLOCKED',elapsed_s=time.time()-start)
(HERE/'signal_phase_screen.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')

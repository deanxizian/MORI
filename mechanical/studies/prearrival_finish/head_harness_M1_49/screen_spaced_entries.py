"""Read-only current-main route screen; no hole, hardware or print changes."""
from pathlib import Path
import sys, json, time
HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
sys.path.insert(0, str(PROJECT / 'mechanical/scripts'))
sys.path.insert(0, str(HERE))
from harness_context import Context, np, sha
from common import P
from validate import rigidtr
from route_family import family, rotate

ctx = Context(); start = time.time(); targets = ctx.targets
group = {n: s.group for n, s in ctx.ss.items()}
bygroup = {g: {n:s for n,s in targets.items() if group.get(n, 'body') == g or (g == 'body' and group.get(n, 'body') not in ['yaw', 'pitch'])} for g in ['body', 'yaw', 'pitch']}
slots = P['neck_harness_capacity']['wire_allocations']
results = []; saved = {}
for dip in [.37]:
    angles = [11,24,38,125,144,163,0,49,135,153,173]
    rows = family(z0=138, dip=dip, samples=7201)
    chord = max(r['chord_error_mm'] for r in rows)
    data = {f'wire{i}_y{r["yaw_deg"]}':rotate(r['points'], angles[i]) for i in range(11) for r in rows}
    failures = []; checks = 0
    for i, slot in enumerate(slots):
        for yaw in range(-60, 61, 10):
            p = data[f'wire{i}_y{yaw}']
            for g,t in bygroup.items():
                ctx.targets = t
                for pitch in (range(-20, 26, 5) if g == 'pitch' else [0]):
                    tr = np.linalg.inv(np.asarray(rigidtr(yaw, pitch if g == 'pitch' else 0)))
                    pts = p if g == 'body' else p @ tr[:3,:3].T + tr[:3,3]
                    checks += 1
                    hit = ctx.clear(pts, chord_error=chord, radius=slot['OD_mm']/2)
                    if hit:
                        failures.append(dict(wire=i,yaw=yaw,pitch=pitch,group=g,**hit)); break
                if failures:break
            if failures:break
        if failures:break
    bend = min(r['minimum_sampled_bend_mm'] for r in rows)
    result = dict(angles_deg=angles, body_entry_z_mm=138, dip_mm=dip, status='PASS' if not failures and bend>=14.224 else 'BLOCKED', checks=checks, hits=failures, minimum_sampled_bend_mm=bend, length_mm=rows[0]['length_mm'], max_chord_error_mm=chord)
    results.append(result)
    if result['status']=='PASS':saved.update({f'case{len(results)-1}_{k}':v for k,v in data.items()})
    print('SPACED_ENTRY', result, flush=True)
ctx.targets = targets; ctx.assert_unchanged()
np.savez_compressed(HERE/'spaced_entry_candidates.npz', **saved)
r = dict(status='PASS' if saved else 'BLOCKED', sources=ctx.sources, results=results, curve_file_sha256=sha(HERE/'spaced_entry_candidates.npz'), script_sha256=sha(Path(__file__)), family_sha256=sha(HERE/'route_family.py'), full_harness='BLOCKED', wire_wire='NOT_TESTED', main_changed=False, elapsed_s=time.time()-start)
(HERE/'spaced_entry_screen.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')

"""Read-only C6 compatibility screen against the two newly adopted body shells."""
from pathlib import Path
import sys,json,time
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
H=OUT.parent/'head_harness_M1_49';C=H/'remaining_routes/c6_left_slot_entry'
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(H))
from harness_context import Context,np,sha,manifold
from common import P
from entry_channel_candidate import build
ctx=Context();start=time.time();current=ctx.ss['Yaw_Base'].m
candidate,construction=build(current,P['neck_harness_capacity'])
data=np.load(C/'Yaw_Base_candidate.npz');stored=manifold.Manifold(manifold.Mesh64(data['vertices_mm'],data['triangles'].astype(np.uint64)))
delta=float((candidate-stored).volume()+(stored-candidate).volume());assert delta<1e-7
old=json.loads((C/'combined/lower_nine_screen.json').read_text());path=C/'combined/lower_nine_candidates.npz'
assert old['status']=='PASS' and sha(path)==old['curve_sha256']
curves=dict(np.load(path));ctx.targets={n:ctx.target(ctx.ss[n].m) for n in ['Body_Front','Body_Rear']}
lane=json.loads((H/'remaining_routes/left_tall_balanced/neck_screen.json').read_text())
chord=next(r for r in lane['results'] if r['status']=='PASS')['chord_error_mm']
rows=[]
for row in old['selected']:
 for yaw in range(-60,61,10):
  name=row['endpoint']+f'_y{yaw}';points=curves[name]
  hit=ctx.clear(points,chord_error=max(chord,row['chord_error_mm']),radius=row['OD_mm']/2)
  rows.append(dict(curve=name,status='FAIL' if hit else 'PASS',failure=hit))
assert len(rows)==117 and all(r['status']=='PASS' for r in rows)
ctx.assert_unchanged()
(OUT/'c6_current_body_screen.json').write_text(json.dumps(dict(status='PASS',revision=P['revision'],source_blend_sha256=ctx.source_hash,
 scope='Only C6 candidate identity and existing nine lower-route candidates against the two M1.51 body shells; no full route/adoption/assembly claim.',
 candidate_difference_mm3=delta,construction=construction,route_checks=rows,
 inputs={str(p.relative_to(ROOT)):sha(p) for p in [path,C/'combined/lower_nine_screen.json',C/'Yaw_Base_candidate.npz',H/'entry_channel_candidate.py',H/'remaining_routes/left_tall_balanced/neck_screen.json']},
 approved=False,main_changed=False,full_harness='BLOCKED',physical_fit='NOT_TESTED',elapsed_seconds=time.time()-start),ensure_ascii=False,indent=2)+'\n')
print('C6_NEW_BODY_ONLY_PASS',len(rows),flush=True)

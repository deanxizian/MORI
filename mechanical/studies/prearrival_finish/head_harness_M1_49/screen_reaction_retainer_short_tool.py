"""Finite nominal right-angle tool screen at the reaction retaining screw.

No tool SKU or changed screw is selected by this study. A passing local pose
would still need a complete entry/exit path and a matching drive/tool drawing.
"""
from pathlib import Path
import json,math,sys,time,collections
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes';REST=BASE/'cam_restraints';OUT=REST/'reaction_short_tool'
OUT.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import manifold
from interface_completion import axial
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text())
file=REST/'inner_head_lowering/review.json';prior=read(file)
for f,h in {**prior['sources'],**prior['inputs']}.items():assert sha(ROOT/f)==h,f
absent=set(prior['rows'][1]['not_yet_installed']);inputs=[file,ROOT/'mechanical/scripts/interface_completion.py']
fixed={n:s.m for n,s in ctx.ss.items() if n not in absent}
for n,p in [('Yaw_Base',BASE/'c6_left_slot_entry/Yaw_Base_candidate.npz'),
            ('Pitch_Yoke',REST/'sliding_guide_v4/Pitch_Yoke_candidate.npz'),
            ('Pitch_Cradle',REST/'return_clamp_v3/Pitch_Cradle_candidate.npz'),
            ('connector_band',REST/'return_clamp_v3/band.npz'),('connector_head',REST/'return_clamp_v3/head.npz')]:
    inputs.append(p);a=np.load(p);fixed[n]=manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles'].astype(np.uint64)))
fixed.update({n:t['m'] for n,t in ctx.targets.items() if n.startswith(('Plug_','fixed_wire_'))})
boxes={n:np.asarray(t.bounding_box()) for n,t in fixed.items()}
def blocked(m):
    bb=np.asarray(m.bounding_box());out=[]
    for n,t in fixed.items():
        tb=boxes[n]
        if np.any(bb[3:]+.3<tb[:3]) or np.any(tb[3:]+.3<bb[:3]):continue
        v=float((m^t).volume());gap=0. if abs(v)>1e-6 else float(m.min_gap(t,.301))
        if abs(v)>1e-6 or gap<.3:out.append(dict(target=n,overlap_mm3=v,gap_mm_capped=gap))
    return out
rows=[]
for short in [5.5,10.,15.,20.,25.,30.]:
    results=[];counter=collections.Counter()
    face=np.array([0.,10.2,142.5]);a=np.array([0.,1.,0.]);elbow=face+a*short
    for angle in range(0,360,5):
        b=np.array([math.cos(math.radians(angle)),0.,math.sin(math.radians(angle))])
        parts=[axial(1.25,short,face+a*short/2,a),axial(1.25,70.,elbow+b*35.,b),
               manifold.Manifold.sphere(1.25*math.sqrt(3),24).translate(elbow.tolist())]
        hits=[]
        for i,m in enumerate(parts):hits.extend(dict(piece=i,**h) for h in blocked(m))
        counter.update(set(h['target'] for h in hits))
        results.append(dict(angle_deg=angle,status='BLOCKED' if hits else 'PASS',hits=hits))
    row=dict(short_leg_mm=short,clear_angles_deg=[r['angle_deg'] for r in results if r['status']=='PASS'],
             target_counts=dict(counter),poses=results)
    rows.append(row);print('REACTION_SHORT_TOOL',short,row['clear_angles_deg'],dict(counter),flush=True)
ctx.assert_unchanged()
r=dict(status='PASS' if any(row['clear_angles_deg'] for row in rows) else 'BLOCKED',
    scope='Finite local nominal tool poses only; not installation proof',sources=ctx.sources,
    inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},rows=rows,
    tool='ASSUMED diameter2.5mm two-leg allocation, long leg70mm, enlarged conservative elbow',
    tool_entry_exit='NOT_TESTED',tool_engagement_torque='NOT_TESTED',tool_SKU='BLOCKED',
    main_changed=False,approved=False,C6_main_applied=False,full_harness='BLOCKED',Yaw_Reaction_Link_present=True,
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('REACTION_SHORT_TOOL_DONE',r['status'],r['elapsed_s'],flush=True)

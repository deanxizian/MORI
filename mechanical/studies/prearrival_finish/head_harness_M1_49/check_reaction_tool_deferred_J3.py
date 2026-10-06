"""Recheck the same nominal extraction routes with the J3 cable plug deferred.

Lower body shell and its screws are deferred. No structural change, tool
selection or claim that these finite translation routes exhaust all paths.
"""
from pathlib import Path
import json,math,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes';REST=BASE/'cam_restraints';OUT=REST/'reaction_short_tool_deferred_J3'
OUT.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import manifold
from interface_completion import axial
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text())
source=REST/'reaction_short_tool/review.json';prior=read(source)
for f,h in {**prior['sources'],**prior['inputs']}.items():assert sha(ROOT/f)==h,f
stagefile=REST/'inner_head_lowering/review.json';stage=read(stagefile)
absent=set(stage['rows'][1]['not_yet_installed'])|{'Body_Lower'}|{n for n in ctx.ss if n.startswith(('Frame_Screw_','Shell_Screw_'))}
inputs=[source,stagefile,ROOT/'mechanical/scripts/interface_completion.py']
fixed={n:s.m for n,s in ctx.ss.items() if n not in absent}
for n,p in [('Yaw_Base',BASE/'c6_left_slot_entry/Yaw_Base_candidate.npz'),
            ('Pitch_Yoke',REST/'sliding_guide_v4/Pitch_Yoke_candidate.npz'),
            ('Pitch_Cradle',REST/'return_clamp_v3/Pitch_Cradle_candidate.npz'),
            ('connector_band',REST/'return_clamp_v3/band.npz'),('connector_head',REST/'return_clamp_v3/head.npz')]:
    inputs.append(p);a=np.load(p);fixed[n]=manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles'].astype(np.uint64)))
fixed.update({n:t['m'] for n,t in ctx.targets.items() if n.startswith(('Plug_','fixed_wire_'))})
deferred_plugs=['Plug_power_J3']
for name in deferred_plugs:fixed.pop(name)
boxes={n:np.asarray(t.bounding_box()) for n,t in fixed.items()}
def collision(parts,shift):
    for i,part in enumerate(parts):
        m=part.translate(np.asarray(shift).tolist());bb=np.asarray(m.bounding_box())
        for n,t in fixed.items():
            tb=boxes[n]
            if np.any(bb[3:]<tb[:3]) or np.any(tb[3:]<bb[:3]):continue
            v=float((m^t).volume())
            if abs(v)>1e-5:return dict(piece=i,target=n,overlap_mm3=v)
    return None
rows=[]
for row in prior['rows']:
 for angle in row['clear_angles_deg']:
    short=row['short_leg_mm'];face=np.array([0.,10.2,142.5]);a=np.array([0.,1.,0.]);elbow=face+a*short
    b=np.array([math.cos(math.radians(angle)),0.,math.sin(math.radians(angle))])
    parts=[axial(1.25,short,face+a*short/2,a),axial(1.25,70.,elbow+b*35.,b),manifold.Manifold.sphere(1.25*math.sqrt(3),24).translate(elbow.tolist())]
    # First disengage along the screw's +Y axis, then try lowering or pulling
    # along the long arm into the not-yet-closed lower-body workspace.
    for retract in [2.,4.,8.]:
     for label,direction in [('down',np.array([0.,0.,-1.])),('along_handle',b)]:
        poses=[np.array([0.,d,0.]) for d in np.arange(0,retract+.01,.25)]
        poses += [np.array([0.,retract,0.])+direction*d for d in np.arange(.25,140.01,.25)]
        first=None;checked=0
        for shift in poses:
            h=collision(parts,shift);checked+=1
            if h:first=dict(translation_mm=shift.tolist(),**h);break
        rows.append(dict(short_leg_mm=short,angle_deg=angle,disengage_mm=retract,route=label,status='BLOCKED' if first else 'PASS',first_failure=first,checked_samples=checked))
ctx.assert_unchanged()
r=dict(status='PASS' if any(x['status']=='PASS' for x in rows) else 'BLOCKED',
    scope='Finite nominal rigid-tool translations with lower shell deferred; no complete tool or manipulation qualification',
    sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},rows=rows,absent=sorted(absent),
    deferred_plugs=deferred_plugs,late_plug_installation='NOT_TESTED',route_count=len(rows),clear_routes=sum(x['status']=='PASS' for x in rows),all_other_tool_routes='NOT_TESTED',
    main_changed=False,approved=False,C6_main_applied=False,full_harness='BLOCKED',Yaw_Reaction_Link_present=True,
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('REACTION_DEFERRED_J3_DONE',r['status'],len(rows),r['clear_routes'],r['elapsed_s'],flush=True)

"""Screen short-leg M3 tooling under a closed upper shell, lower shell off.

Catalogue 2 mm / 100 mm / 5.5 mm Wera lengths; elbow remains an assumed
conservative envelope. This does not qualify actual socket engagement.
"""
from pathlib import Path
import json,math,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=HERE/'remaining_routes'
OUT=BASE/'cam_restraints/head_module_tools';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import manifold
from interface_completion import axial
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text())
stagefile=BASE/'cam_restraints/head_module_sequence_v2/review.json';stage=read(stagefile);assert stage['status']=='PASS'
for f,h in {**stage['sources'],**stage['inputs']}.items():assert sha(ROOT/f)==h,f
preflight=ROOT/'mechanical/studies/prearrival_closure/assembly_preflight.json'
catalogue=HERE.parent/'harness_A8/cam_socket_tool/sources/Wera_950_PKLS.html'
inputs=[stagefile,preflight,catalogue,ROOT/'mechanical/scripts/interface_completion.py']
removed=set(stage['removed_before_motion'])|{n for n in ctx.ss if n.startswith(('Wheel_Hub_','Tire_','Wheel_Hub_Lock_','Wheel_Spacer_L_1','Wheel_Spacer_R_1'))}
fixed={n:s.m for n,s in ctx.ss.items() if n not in removed}
# Existing rigid body wire candidates and mating housings retained; the moving
# eleven head leads have no complete assembly shapes and are not certified.
fixed.update({n:t['m'] for n,t in ctx.targets.items() if n.startswith(('fixed_wire_','Plug_'))})
rad=2/math.sqrt(3)+.01;rows=[]
def hits(m,ignore=()):
    bb=np.asarray(m.bounding_box());bad=[];minimum=.301
    for n,t in fixed.items():
        if n in ignore:continue
        tb=np.asarray(t.bounding_box())
        if np.any(bb[3:]+.301<tb[:3]) or np.any(tb[3:]+.301<bb[:3]):continue
        v=float((m^t).volume());gap=0. if abs(v)>1e-6 else float(m.min_gap(t,.301))
        minimum=min(minimum,gap)
        if abs(v)>1e-6 or gap<.3:bad.append(dict(target=n,overlap_mm3=v,gap_mm=gap))
    return bad,minimum
def pieces(face,axis,angle,extra=0.):
    b=np.array([0.,math.sin(math.radians(angle)),-math.cos(math.radians(angle))]);p=face+axis*(-.8+extra)
    return [axial(rad,5.5,p+axis*2.75,axis),axial(rad,100.,p+axis*5.5+b*50,b),
            manifold.Manifold.sphere(rad*math.sqrt(3),24).translate((p+axis*5.5).tolist())]
for f in read(preflight)['fasteners']:
    if not f['id'].startswith('Yaw_Base'):continue
    name=f['id'];face=np.asarray(f['head_top_mm']);axis=np.asarray(f['axis']);s=ctx.ss[name]
    assert abs(float((s.v@axis).max())-float(face@axis))<1e-5
    orientations=[]
    for angle in range(-180,181,5):
        tool=manifold.Manifold.batch_boolean(pieces(face,axis,angle),manifold.OpType.Add)
        bad,gap=hits(tool);orientations.append(dict(angle_deg=angle,status='BLOCKED' if bad else 'PASS',gap_mm=gap,hits=bad[:3]))
    screw_sweeps=[]
    for start,end in [(0.,8.),(0.,2.)]:
        hull=manifold.Manifold.hull_points(np.vstack([s.v+axis*start,s.v+axis*end]));bad,gap=hits(hull,ignore=['Yaw_Base',name.replace('_Screw','_Nut')])
        screw_sweeps.append(dict(from_mm=start,to_mm=end,status='BLOCKED' if bad else 'PASS',hits=bad,gap_mm=gap,
                                 excluded_intended_shank_hole_and_thread=['Yaw_Base',name.replace('_Screw','_Nut')]))
    passed=[r['angle_deg'] for r in orientations if r['status']=='PASS'];runs=[]
    for a in passed:
        if not runs or a!=runs[-1][-1]+5:runs.append([a])
        else:runs[-1].append(a)
    longest=max(runs,key=len) if runs else []
    row=dict(screw=name,orientations=orientations,sampled_clear_angle_run_deg=longest,screw_axial_sweeps=screw_sweeps,
             status='PASS' if len(longest)>12 and all(r['status']=='PASS' for r in screw_sweeps) else 'BLOCKED')
    rows.append(row);print('HEAD_MODULE_TOOLS',name,row['status'],longest,screw_sweeps,flush=True)
ctx.assert_unchanged()
r=dict(status='PASS' if all(x['status']=='PASS' for x in rows) else 'BLOCKED',scope='Sampled short-leg access and rigid axial screw sweep; no claim of complete tightening or tool entry',
    sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},rows=rows,
    removed_before_work=sorted(removed),retained_fixed_wire_solids=14,retained_mating_allocations=len(ctx.plug),
    tool=dict(manufacturer='Wera',model='950 PKLS',sku='05022041001',AF_mm=2,long_leg_mm=100,short_leg_mm=5.5,
              url='https://www.wera.de/en/tools/950-pkls-l-key-metric-chrome-plated',
              evidence='Manufacturer table, refreshed 2026-10-06; length convention and filled elbow are conservative assumptions, not exact CAD'),
    continuous_tool_rotation='NOT_TESTED',tool_entry_from_outside='NOT_TESTED',actual_socket_engagement='NOT_TESTED',
    complete_flexible_head_wires='NOT_TESTED',main_changed=False,approved=False,full_harness='BLOCKED',Yaw_Reaction_Link_present=True,
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('HEAD_MODULE_TOOLS_DONE',r['status'],r['elapsed_s'],flush=True)

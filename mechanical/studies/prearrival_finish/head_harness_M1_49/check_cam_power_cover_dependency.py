"""Check the late-plug path against the actual prepositioned body shell.

The raised pose is borrowed as a rigid fixture hypothesis, not a demonstrated
flexible-harness sequence. Shell-carried connector/wire reshaping is unresolved.
"""
from pathlib import Path
import json,sys,time,math
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=HERE/'remaining_routes'
OUT=BASE/'cam_restraints/power_cover_dependency';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import manifold,D
from mathutils import Matrix,Vector
ctx=Context();started=time.time()
priorfile=ROOT/'mechanical/reports/assembly_issue_validation.json'
upper=set(json.loads(priorfile.read_text())['body_service']['upper_shell']['moving'])
assert upper<=set(ctx.ss),upper-set(ctx.ss)
pathdir=BASE/'cam_restraints/power_plug_simple';report=json.loads((pathdir/'review.json').read_text());assert report['status']=='PASS'
for f,h in {**report['sources'],**report['inputs']}.items():assert sha(ROOT/f)==h,f
assert sha(pathdir/'path.npz')==report['path_sha256'];data=np.load(pathdir/'path.npz');points=data['shifts_mm'];plug=ctx.plug['power_J18']
origin=Vector((0,0,D['body_z']))
raised=Matrix.Translation((0,0,14))@Matrix.Translation(origin)@Matrix.Rotation(math.radians(15),4,'X')@Matrix.Translation(-origin)
rows=[];head_checks=[]
for name,tr in [('closed',Matrix.Identity(4)),('prepositioned_15deg_14up',raised)]:
    solids={n:ctx.ss[n].m.transform(np.asarray(tr)[:3,:]) for n in upper}
    hits=[]
    for i,(a,b) in enumerate(zip(points,points[1:])):
        m=manifold.Manifold.hull_points(np.vstack([plug.v+a,plug.v+b]));box=np.asarray(m.bounding_box())
        for part,t in solids.items():
            tb=np.asarray(t.bounding_box())
            if not(np.all(box[:3]<=tb[3:]+.301) and np.all(box[3:]+.301>=tb[:3])):continue
            v=float((m^t).volume());gap=float(m.min_gap(t,.301)) if abs(v)<1e-7 else 0.
            if abs(v)>1e-6 or gap<.3:hits.append(dict(segment=i,target=part,overlap_mm3=v,gap_mm=gap))
    rows.append(dict(pose=name,status='BLOCKED' if hits else 'PASS',path_hits=hits))
    if name!='closed':
        for part,m in solids.items():
            box=np.asarray(m.bounding_box())
            for head,s in ctx.ss.items():
                if s.group not in ['yaw','pitch']:continue
                if not(np.all(box[:3]<=s.hi) and np.all(box[3:]>=s.lo)):continue
                v=float((m^s.m).volume())
                if abs(v)>1e-6:head_checks.append(dict(moving=part,head_part=head,overlap_mm3=v))
    print('POWER_COVER_PATH',name,rows[-1],flush=True)
ctx.assert_unchanged()
r=dict(status='PASS' if rows[-1]['status']=='PASS' and not head_checks else 'BLOCKED',
    scope='Known five-segment bare-housing route with closed/raised shell; raised shell endpoint vs installed head only',
    sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in [priorfile,pathdir/'review.json',pathdir/'path.npz',ROOT/'mechanical/reports/head_retention_body_sequence.json',ROOT/'mechanical/studies/prearrival_closure/dual_body_sequence.py']},
    moved_shell_module=sorted(upper),raised_transform=np.asarray(raised).tolist(),path_checks=rows,
    raised_shell_vs_head_intersections=head_checks,
    matching_old_body_sequence='Rigid-only sequence uses shell 15deg and +14mm; full head/soft-wire dependency not thereby qualified',
    body_shell_transition_with_head='NOT_TESTED',shell_carried_wire_reshaping='NOT_TESTED',J18_attached_wires='NOT_TESTED',
    main_changed=False,approved=False,full_harness='BLOCKED',Yaw_Reaction_Link_present=True,
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('POWER_COVER_DEPENDENCY_DONE',r['status'],head_checks,r['elapsed_s'],flush=True)

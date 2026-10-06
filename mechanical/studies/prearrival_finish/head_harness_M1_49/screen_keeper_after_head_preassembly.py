"""Current-main keeper access after full or CAM-only head preassembly.

Source lengths of the extra-short 2AF key are documented; the round rods and
filled elbow are conservative assumptions. No actual socket fit or lead
motion is qualified by this screen.
"""
from pathlib import Path
import json,math,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes';REST=BASE/'cam_restraints';OUT=REST/'keeper_after_head'
OUT.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import manifold
from validate import rigidtr
from interface_completion import axial
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text())
benchfile=REST/'bench_preassembly_v2/review.json';bench=read(benchfile)
toolfile=REST/'head_module_tools/review.json';tool=read(toolfile)
inputs=[benchfile,toolfile,ROOT/'mechanical/scripts/interface_completion.py',ROOT/'mechanical/scripts/validate.py']
for r in [bench,tool]:
    for f,h in {**r.get('sources',{}),**r.get('inputs',{})}.items():assert sha(ROOT/f)==h,f
stages={'full_head':set(),'CAM_cradle_before_optics':set(bench['not_yet_installed'])}
rad=2/math.sqrt(3)+.01;rows=[]
def key_parts(face,angle,extra=0.):
    a=np.array([0.,0,1.]);b=np.array([math.cos(math.radians(angle)),math.sin(math.radians(angle)),0.])
    p=face+a*(-.8+extra)
    return [axial(rad,5.5,p+a*2.75,a),axial(rad,100.,p+a*5.5+b*50,b),
            manifold.Manifold.sphere(rad*math.sqrt(3),24).translate((p+a*5.5).tolist())]
def hits(m,targets,gap=.3):
    bb=np.asarray(m.bounding_box());bad=[]
    for n,t in targets.items():
        tb=np.asarray(t.bounding_box())
        if np.any(bb[3:]+gap<tb[:3]) or np.any(tb[3:]+gap<bb[:3]):continue
        v=float((m^t).volume());d=0 if abs(v)>1e-6 else float(m.min_gap(t,gap+.001))
        if abs(v)>1e-6 or d<gap:bad.append(dict(target=n,overlap_mm3=v,gap_mm=d))
    return bad
for stage,absent in stages.items():
 for yaw in [-60,0,60]:
    native={n:(s.m.transform(np.asarray(rigidtr(yaw,0))[:3,:]) if s.group in ['yaw','pitch'] else s.m)
            for n,s in ctx.ss.items() if n not in absent}
    native.update({n:t['m'] for n,t in ctx.targets.items() if n.startswith(('Plug_','fixed_wire_'))})
    for name in ['Yaw_Keeper_Screw_0','Yaw_Keeper_Screw_1']:
        s=ctx.ss[name];face=np.array([(s.lo[0]+s.hi[0])/2,(s.lo[1]+s.hi[1])/2,s.hi[2]])
        fixed={n:m for n,m in native.items() if n!=name};angles=[]
        for angle in range(0,360,5):
            bad=[]
            for i,m in enumerate(key_parts(face,angle)):
                bad.extend(dict(piece=i,**h) for h in hits(m,fixed))
            angles.append(dict(angle_deg=angle,status='BLOCKED' if bad else 'PASS',hits=bad[:6]))
        screw_rows=[]
        # Actual rigid screw positions; no whole-screw convex hull which would
        # artificially fill the space between a wide head and narrow shank.
        for z in np.arange(0,8.01,.25):
            m=s.m.translate([0,0,float(z)]);bad=hits(m,fixed,gap=0.)
            screw_rows.append(dict(lift_mm=float(z),status='BLOCKED' if bad else 'PASS',hits=bad))
            if bad:break
        clear=[x['angle_deg'] for x in angles if x['status']=='PASS'];extended=clear+[x+360 for x in clear];runs=[]
        for a in extended:
            if not runs or a!=runs[-1][-1]+5:runs.append([a])
            else:runs[-1].append(a)
        longest=max(runs,key=len)[:72] if runs else []
        ok=bool(longest) and all(r['status']=='PASS' for r in screw_rows)
        row=dict(stage=stage,yaw_deg=yaw,pitch_deg=0,screw=name,head_top_mm=face.tolist(),
                 status='PASS' if ok else 'BLOCKED',clear_angles_deg=clear,longest_sampled_run_deg=longest,
                 angles=angles,screw_entry_samples=screw_rows)
        rows.append(row);print('KEEPER_AFTER_HEAD_CASE',stage,yaw,name,row['status'],clear,
                             screw_rows[-1] if screw_rows[-1]['status']=='BLOCKED' else 'screw samples clear',flush=True)
ctx.assert_unchanged()
usable=[dict(stage=st,yaw_deg=y) for st in stages for y in [-60,0,60]
        if all(r['status']=='PASS' for r in rows if r['stage']==st and r['yaw_deg']==y)]
r=dict(status='PASS' if usable else 'BLOCKED',scope='Sampled keeper tool access and actual screw insertion positions after preassembled head; no full wired sequence',
       sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},
       stages={n:sorted(a) for n,a in stages.items()},rows=rows,usable_stages=usable,tool=tool['tool'],
       retained_fixed_wire_solids=14,retained_mating_allocations=29,
       continuous_tool_rotation='NOT_TESTED',tool_entry='NOT_TESTED',complete_head_lowering='NOT_TESTED',
       full_soft_lead_clearance='NOT_TESTED',actual_SCS0009_interface='BLOCKED',
       main_changed=False,approved=False,full_harness='BLOCKED',Yaw_Reaction_Link_present=True,
       script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('KEEPER_AFTER_HEAD_DONE',r['status'],usable,r['elapsed_s'],flush=True)

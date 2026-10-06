"""Compare a few rigid continuations before altering any wire recipe.

Read-only geometry. Rear plugs keep their conservative source envelopes.
This diagnostic does not establish wire or assembly feasibility.
"""
from pathlib import Path
DIAG_SCRIPT=Path(__file__).resolve()
DIAG_HELPER=DIAG_SCRIPT.parent/'screen_shell16_joint_feed.py'
__file__=str(DIAG_HELPER)
exec(compile(DIAG_HELPER.read_text().split('\nfor label,poses in stages_for',1)[0],str(DIAG_HELPER),'exec'),globals())
__file__=str(DIAG_SCRIPT)
OUT=ORDER_OUT/'shell16_rigid_continuations';OUT.mkdir(exist_ok=True)

def check_rigid(p):
    bridge_t=trans(y=p.get('by',0.),z=p['bz'])
    upper_t=shellpose(p['a'],p['y'],p['sz'])
    u=placed(upper_rigid,upper_t);b=placed(bridge_rigid,bridge_t)
    return collisions(u,fixed_placed) or collisions(b,fixed_placed) or collisions(u,b)

reports=[]
for rise in [0.,1.,2.]:
    poses=[dict(a=16.,y=-14.*float(t),by=-14.*float(t),sz=14.+rise*float(t),bz=18.+rise*float(t))
           for t in np.linspace(0.,1.,57)]
    failure=None;rows=[]
    for i,p in enumerate(poses):
        failure=check_rigid(p)
        rows.append(dict(index=i,pose=p,status='BLOCKED' if failure else 'PASS',failure=failure))
        if failure:break
    phases=[dict(stage='shared_back',status='BLOCKED' if failure else 'PASS',rows=rows)]
    if not failure:
        zero=shellpose(16.,-14.,0.)
        upper_low=min(m.transform(zero[:3,:4]).bounding_box()[2] for m in upper_rigid.values())
        end=math.ceil(max(body_max_z+1.-upper_low+4.,body_max_z+1.-bridge_min_z)*2)/2
        rows=[]
        for i,z in enumerate(np.arange(18.+rise,end+.01,.5)):
            p=dict(a=16.,y=-14.,by=-14.,sz=float(z-4.),bz=float(z))
            failure=check_rigid(p)
            rows.append(dict(index=i,pose=p,status='BLOCKED' if failure else 'PASS',failure=failure))
            if failure:break
        phases.append(dict(stage='shared_vertical',status='BLOCKED' if failure else 'PASS',rows=rows,endpoint_z_mm=end))
    reports.append(dict(rise_mm=rise,status='BLOCKED' if failure else 'PASS',phases=phases))
    print('SHELL16_RIGID',rise,reports[-1]['status'],phases[-1]['stage'],phases[-1]['rows'][-1],flush=True)

report=dict(status='PASS' if any(r['status']=='PASS' for r in reports) else 'BLOCKED',
            scope='Rigid continuations only; wire formation not covered',script_sha256=sha(DIAG_SCRIPT),
            helper_sha256=sha(DIAG_HELPER),protected_sources=protected,paths=reports,
            all14_fixed_body_wires=True,conservative_plugs_unchanged=True,
            whole_harness='BLOCKED',main_applied=False,manufacturing_release=False)
(OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())

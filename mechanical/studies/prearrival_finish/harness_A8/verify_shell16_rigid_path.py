"""Replay all four stages together at the intended wire-check sample spacing."""
from pathlib import Path
RIGID16_SCRIPT=Path(__file__).resolve();RIGID16_HELPER=RIGID16_SCRIPT.parent/'diagnose_shell16_continuations.py'
__file__=str(RIGID16_HELPER)
exec(compile(RIGID16_HELPER.read_text().split('\nreports=[]',1)[0],str(RIGID16_HELPER),'exec'),globals())
__file__=str(RIGID16_SCRIPT)
OUT=ORDER_OUT/'shell16_full_rigid_path';OUT.mkdir(exist_ok=True)
prior_path=ORDER_OUT/'shell16_extended_back/screen.json'
prior=json.loads(prior_path.read_text())
assert prior['script_sha256']==sha(RIGID16_SCRIPT.parent/'diagnose_shell16_extended_back.py')
selected=next(r for r in prior['vertical_candidates'] if r['held_y_mm']==-20. and r['status']=='PASS')
endpoint=selected['endpoint_z_mm']
phases=stages_for(16.,14.,0.)[:2]+[
    ('shared_back20',[dict(a=16.,y=float(y),by=float(y),sz=14.,bz=18.) for y in np.linspace(0.,-20.,81)]),
    ('shared_vertical',[dict(a=16.,y=-20.,by=-20.,sz=float(z-4.),bz=float(z)) for z in np.arange(18.,endpoint+.01,.5)])]
records=[];unique=set();failure=None
for label,poses in phases:
    rows=[]
    for i,p in enumerate(poses):
        failure=check_rigid(p)
        rows.append(dict(index=i,pose=p,status='BLOCKED' if failure else 'PASS',failure=failure))
        unique.add(tuple(p.get(k,0.) for k in ['a','y','sz','by','bz']))
        if failure:break
    records.append(dict(stage=label,planned_positions=len(poses),checked_positions=len(rows),
                         status='BLOCKED' if failure else 'PASS',rows=rows))
    print('SHELL16_RIGID_REPLAY',label,records[-1]['status'],len(rows),round(time.time()-started,2),flush=True)
    if failure:break
assert not failure,failure
report=dict(status='PASS',scope='Four sampled rigid stages with installed body/rear plug allocations and 14 fixed body wires; CAM movement excluded',
    script_sha256=sha(RIGID16_SCRIPT),helper_sha256=sha(RIGID16_HELPER),
    source_files={**joint['source_files'],str(prior_path.relative_to(PROJECT)):sha(prior_path),
                  str(joint_path.relative_to(PROJECT)):sha(joint_path),str((JOINT/'wire_solids.json').relative_to(PROJECT)):sha(JOINT/'wire_solids.json')},
    protected_sources=protected,source_main_sha256=source_hash,
    substituted_unadopted_prints=membership['substituted_unadopted_prints'],
    members=dict(core=sorted(core),upper=sorted(upper),bridge=sorted(bridge),
                 body_plugs=sorted(body_plugs),upper_plugs=sorted(upper_plugs),deferred_head_plugs=deferred_plugs),
    fixed_body_wires=sorted(n for n in fixed_rigid if n.startswith('fixed_wire_')),
    records=records,sample_records=sum(r['checked_positions'] for r in records),unique_poses=len(unique),
    endpoint=dict(bridge_y_mm=-20.,bridge_z_mm=endpoint,shell_z_mm=endpoint-4.,shell_tilt_deg=16.),
    final_z_separation_mm=1.,continuous_rigid_motion='NOT_TESTED',
    CAM_wire_movement='NOT_TESTED',complete_attached_assembly='BLOCKED',main_applied=False,manufacturing_release=False)
(OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('SHELL16_RIGID_REPLAY_DONE',report['sample_records'],report['unique_poses'],flush=True)

"""Compare common upper-body/head handling without changing printed geometry."""
from pathlib import Path
THIS=Path(__file__).resolve(); HELPER=THIS.parent/'screen_CAM_complete_head_insertion.py'
__file__=str(HELPER)
exec(compile(HELPER.read_text().split('\nheadsets=',1)[0],str(HELPER),'exec'),globals())
__file__=str(THIS)
COUPLED=OUT/'coupled';COUPLED.mkdir(exist_ok=True)
fixed=placed(fixture,I);started=time.time();rows=[]
module=upper|moving
# A single rigid module preserves all head-to-shell gaps automatically.
# Check its initial removal and subsequent backward/lifted motion against
# every installed lower member, not just the old selected bridge fixture.
for angle in (15.,10.,5.,0.):
    poses=[shellpose(angle*float(u),0,14*float(u)) for u in np.linspace(0,1,57)]
    poses += [shellpose(angle,float(y),14) for y in np.linspace(0,-14,29)[1:]]
    poses += [shellpose(angle,-14,float(z)) for z in np.linspace(14,140,64)[1:]]
    failures=[];checked=0
    for index,T in enumerate(poses):
        hits=pairs(placed(module,T),fixed);checked+=1
        if hits:failures=[dict(index=index,transform=T.tolist(),hits=hits)];break
    row=dict(candidate='common_rigid_module',tilt_deg=angle,status='BLOCKED' if failures else 'PASS',
        checked_positions=checked,planned_positions=len(poses),failures=failures)
    rows.append(row);print('COUPLED_HEAD_BODY',row,flush=True)

# The keyed bridge starts seated. A small straight lift followed by rotation
# is a distinct bounded candidate, not a clearance waiver at the initial pose.
for initial in (2.,4.,6.,8.,10.,12.):
    poses=[trans(z=float(z)) for z in np.linspace(0,initial,int(initial/.25)+1)]
    poses += [shellpose(15*float(u),0,initial+(14-initial)*float(u)) for u in np.linspace(0,1,61)[1:]]
    poses += [shellpose(15,float(y),14) for y in np.linspace(0,-14,29)[1:]]
    poses += [shellpose(15,-14,float(z)) for z in np.linspace(14,140,64)[1:]]
    failures=[];checked=0
    for index,T in enumerate(poses):
        hits=pairs(placed(module,T),fixed);checked+=1
        if hits:failures=[dict(index=index,transform=T.tolist(),hits=hits)];break
    row=dict(candidate='vertical_then_tilt',initial_lift_mm=initial,status='BLOCKED' if failures else 'PASS',
        checked_positions=checked,planned_positions=len(poses),failures=failures)
    rows.append(row);print('COUPLED_HEAD_BODY',row,flush=True)
report=dict(status='PASS' if any(r['status']=='PASS' for r in rows) else 'BLOCKED',
    scope='Finite rigid upper-body plus full-head path screening; unchanged relative pose',
    script_sha256=sha(THIS),helper_sha256=sha(HELPER),source_main_sha256=source_hash,protected_sources=protected,
    source_rigid_screen_sha256=sha(OUT/'rigid_screen.json'),moving_members=sorted(module),fixture_members=sorted(fixture),
    removed_for_access=sorted(deferred),rows=rows,full_wires='NOT_TESTED',continuous_motion='NOT_TESTED',
    no_universal_impossibility_claim=True,main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,
    elapsed_s=time.time()-started)
(COUPLED/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('COUPLED_HEAD_BODY_DONE',report['status'],round(time.time()-started,2),flush=True)

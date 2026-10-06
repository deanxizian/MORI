"""Bounded four-wire continuation search on the cleared 20 mm rigid route.

Keep each saved bend family and vary only its documented recipe parameters.
Passing endpoints are not called a passing motion; interpolation, fixed
obstacles, wire self-clearance and mutual packing are checked separately.
"""
from pathlib import Path
BACK20_SCRIPT=Path(__file__).resolve();BACK20_HELPER=BACK20_SCRIPT.parent/'screen_shell16_joint_feed.py'
__file__=str(BACK20_HELPER)
exec(compile(BACK20_HELPER.read_text().split('\nfor label,poses in stages_for',1)[0],str(BACK20_HELPER),'exec'),globals())
__file__=str(BACK20_SCRIPT)
OUT=ORDER_OUT/'shell16_back20_wire_families';OUT.mkdir(exist_ok=True)
rigid_path=ORDER_OUT/'shell16_extended_back/screen.json'
rigid_report=json.loads(rigid_path.read_text())
assert rigid_report['status']=='PASS'
assert rigid_report['script_sha256']==sha(BACK20_SCRIPT.parent/'diagnose_shell16_extended_back.py')
assert any(r['held_y_mm']==-20. and r['status']=='PASS' for r in rigid_report['vertical_candidates'])

def set_pose(y):
    global bt,matrices
    bt=trans(y=float(y),z=18.);st=shellpose(16.,float(y),14.)
    matrices=dict(core=I,upper=np.linalg.inv(st),bridge=np.linalg.inv(bt))

def one(pin,p):
    c,f=variant_curve(pin,p['entry_azimuth_deg'],p['planar_radius_mm'],p['family'],p['elevation_fraction'])
    if f:return c,f
    lengths[pin-1]['curve_chord_error_mm']=c['curve_chord_error_mm']
    f=wire_check(pin,c['points'],matrices) or self_check(c) or rigid_check(make_terminal(c,bt),matrices)
    return c,f

pools={};results=[];candidate_curves={};saved={}
for pin in range(1,5):
    p0=starts[pin];set_pose(-20.)
    azs=sorted(set(p0['entry_azimuth_deg']+d for d in [-45.,-30.,-15.,0.,15.,30.,45.]))
    radii=sorted(set([7.,8.,10.,12.,14.,18.,p0['planar_radius_mm']]))
    trials=[];valid=[];failures=Counter()
    for az,radius,fraction in itertools.product(azs,radii,[0.,.25,.5,.75,1.]):
        p=dict(entry_azimuth_deg=az,planar_radius_mm=radius,family=p0['family'],elevation_fraction=fraction)
        c,f=one(pin,p)
        if f:
            failures[f['kind']+(':'+f['obstacle'] if 'obstacle' in f else '')]+=1
            continue
        score=((az-p0['entry_azimuth_deg'])/15.)**2+((radius-p0['planar_radius_mm'])/2.)**2+4*(fraction-p0['elevation_fraction'])**2
        valid.append((score,p,c))
    # Preserve parameter variety rather than testing many equal neighboring endpoints.
    valid.sort(key=lambda row:row[0]);ends=valid[:24]
    passing_paths=[]
    for k,(score,p1,end_curve) in enumerate(ends):
        poses=[];failure=None;previous=None
        for i,u in enumerate(np.linspace(0.,1.,81)):
            set_pose(-20.*float(u))
            p={key:float((1-u)*p0[key]+u*p1[key]) for key in ['entry_azimuth_deg','planar_radius_mm','elevation_fraction']}
            p['family']=p0['family'];c,failure=one(pin,p)
            if failure:break
            if i==0:assert np.array_equal(c['points'],start_curves[f'pin{pin}_pose36'])
            angles=np.asarray(c['planar_angles_rad'])
            if previous is not None and np.max(np.abs(angles-previous))>math.pi:
                failure=dict(kind='arc_branch_jump',pin=pin);break
            previous=angles;poses.append(c)
        label=f'pin{pin}_candidate{k}'
        r=dict(id=label,status='BLOCKED' if failure else 'PASS',parameters=p1,score=score,
               planned_positions=81,passing_positions=len(poses),first_failure_index=len(poses) if failure else None,failure=failure)
        trials.append(r)
        if failure is None:
            passing_paths.append(r);candidate_curves[label]=poses
        if len(passing_paths)>=6:break
    pools[pin]=passing_paths
    results.append(dict(pin=pin,starting_parameters=p0,endpoint_choices=len(valid),
                         endpoint_rejections=dict(failures),continuation_trials=trials,passing_continuations=len(passing_paths)))
    print('SHELL16_BACK20_PIN',pin,'endpoints',len(valid),'paths',len(passing_paths),'failure',trials[0]['failure'] if trials else None,round(time.time()-started,2),flush=True)

chosen=None;packing=[]
if all(pools.values()):
    for choice in itertools.product(*(pools[p] for p in range(1,5))):
        records=[];failure=None
        for i in range(81):
            set_pose(-.25*i)
            curves={pin:candidate_curves[choice[pin-1]['id']][i] for pin in range(1,5)}
            pairs,failure=mutual_check(curves)
            if not failure:failure=terminal_checks(curves,bt)
            if failure:break
            records.append(dict(index=i,pairs=pairs))
        packing.append(dict(ids=[r['id'] for r in choice],status='BLOCKED' if failure else 'PASS',passing_positions=len(records),failure=failure))
        if failure is None:
            chosen=dict(ids=[r['id'] for r in choice],parameters=[r['parameters'] for r in choice],records=records)
            for pin in range(1,5):
                for i,c in enumerate(candidate_curves[choice[pin-1]['id']]):saved[f'pin{pin}_pose{i}']=c['points']
            break
np.savez_compressed(OUT/'curves.npz',**saved)
report=dict(status='PASS' if chosen else 'BLOCKED',scope='Finite fixed-family CAM wire continuation on the cleared shared rear path',
    script_sha256=sha(BACK20_SCRIPT),helper_sha256=sha(BACK20_HELPER),
    source_files={str(p.relative_to(PROJECT)):sha(p) for p in [rigid_path,JOINT/'screen.json',JOINT/'verification.json',JOINT/'curves.npz',JOINT/'wire_solids.json']},
    protected_sources=protected,results=results,packing=packing,selected=chosen,
    curves_sha256=sha(OUT/'curves.npz'),all14_body_wires_present=True,
    full_nominal_lengths_preserved=True,wire_family_change=False,continuous_motion='NOT_TESTED',
    complete_attached_assembly='BLOCKED',main_applied=False,manufacturing_release=False,elapsed_s=time.time()-started)
(OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('SHELL16_BACK20_WIRE_DONE',report['status'],round(time.time()-started,2),flush=True)

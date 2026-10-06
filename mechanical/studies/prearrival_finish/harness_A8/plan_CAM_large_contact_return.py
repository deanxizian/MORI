"""Screen earlier temporary height recovery for the larger contact allocation.

Only an independent assembly-motion candidate is changed. Source solids,
resting wires, terminals, endpoints and required clearances stay unchanged.
"""
from pathlib import Path
LR_SCRIPT=Path(__file__).resolve();LR_ROOT=LR_SCRIPT.parent
LR_HELPER=LR_ROOT/'check_CAM_large_contact_downstream.py';__file__=str(LR_HELPER)
exec(compile(LR_HELPER.read_text().split('\nfor offset in np.linspace(',1)[0],str(LR_HELPER),'exec'),globals())
__file__=str(LR_SCRIPT)
LR_OUT=LC_OUT/'earlier_return';LR_OUT.mkdir(exist_ok=True)
lr_started=time.time();lr_source=lc_forming['stages'][3]['path'];lr_trials=[];lr_selected=None
lr_source_screen=LC_OUT/'screen.json';lr_screen=json.loads(lr_source_screen.read_text())
assert lr_screen['status']=='BLOCKED' and lr_screen['contact_dimensions_mm']==ft_dims.tolist()


def lr_original(f):
    edge=next((a,b) for a,b in zip(lr_source,lr_source[1:]) if a['fraction']-1e-10<=f<=b['fraction']+1e-10)
    return sc_control(edge,f)


def lr_path(start,end):
    fractions=sorted(set([r['fraction'] for r in lr_source]+[start,end]))
    result=[]
    for f in fractions:
        amp,angle=lr_original(f)
        if f>=start:
            amp=min(amp,10.5-1.5*float(np.clip((f-start)/(end-start),0.,1.)))
        result.append(dict(fraction=f,amplitude_mm=amp,side_angle_deg=angle))
    assert result[0]==lr_source[0] and result[-1]==lr_source[-1]
    return result


for start,end in [(.8025,.805),(.8000,.8025),(.7975,.8000),(.8025,.80625),(.8000,.805)]:
    path=lr_path(start,end);rows=[];failure=None;changed_rows=0;min_servo_gap=math.inf
    # Test changed edges first; unchanged old contact states remain covered by
    # the subsequent complete finite replay, without claiming continuity.
    edges=list(zip(path,path[1:]));edges.sort(key=lambda e:(not(start-1e-8<=e[0]['fraction']<=.81),e[0]['fraction']))
    for a,b in edges:
        for f in np.linspace(a['fraction'],b['fraction'],5):
            f=float(f);amp,angle=sc_control((a,b),f)
            failure,curves,contacts=lc_forming_pose(3,(a,b),f)
            changed=abs(amp-lr_original(f)[0])>1e-10
            wire_result=None
            if failure is None and changed:
                changed_rows+=1
                wire_result,_=oe_check(amp,angle,3,f,da_order)
                if wire_result['status']!='PASS':failure=dict(kind='changed_wire_geometry',detail=wire_result)
            servo=next(t[2] for t in fm_targets if t[0]=='Pitch_Servo')
            gap=float(contacts[0][2].min_gap(servo,3.))
            min_servo_gap=min(min_servo_gap,gap)
            rows.append(dict(fraction=f,amplitude_mm=amp,side_angle_deg=angle,changed=changed,
                status='PASS' if failure is None else 'BLOCKED',failure=failure,servo_gap_capped_3mm=gap))
            if failure:break
        if failure:break
    trial=dict(earlier_height_return_fraction=[start,end],path=path,
        status='PASS' if failure is None else 'BLOCKED',rows=rows,checked_positions=len(rows),
        changed_wire_positions=changed_rows,minimum_servo_gap_at_samples_mm=min_servo_gap)
    lr_trials.append(trial)
    print('LARGER_RETURN_TRIAL',start,end,trial['status'],len(rows),'gap',min_servo_gap,'failure',failure,flush=True)
    if failure is None:
        lr_selected=trial;break

report=dict(status='PASS' if lr_selected else 'BLOCKED',scope='Finite whole last-stage replay with an earlier temporary height return; no solid or resting-wire change',
    script_sha256=sha(LR_SCRIPT),helper_sha256=sha(LR_HELPER),source_main_sha256=source_hash,
    source_downstream_screen_sha256=sha(lr_source_screen),source_forming_sha256=sha(lc_forming_path),
    contact_dimensions_mm=ft_dims.tolist(),contact_evidence='ASSUMED requested space, not confirmed post-crimp terminal limits',
    trials=lr_trials,selected_earlier_height_return=lr_selected['earlier_height_return_fraction'] if lr_selected else None,
    selected_path=lr_selected['path'] if lr_selected else None,
    continuous_motion='NOT_TESTED',contact_structure_margin_mm=.3,contact_wire_margin_mm=0.,
    endpoints_unchanged=True,whole_harness='BLOCKED',main_applied=False,manufacturing_release=False,
    elapsed_s=time.time()-lr_started)
(LR_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('LARGER_RETURN_DONE',report['status'],report['selected_earlier_height_return'],flush=True)

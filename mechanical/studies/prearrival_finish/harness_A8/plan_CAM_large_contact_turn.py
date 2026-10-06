"""Compare a small temporary side turn at the later contact-clearance bottleneck.

Earlier height recovery alone missed the neighbouring-wire margin. Here both
contact and wire geometry are screened together, with exact old endpoints.
"""
from pathlib import Path
LT_SCRIPT=Path(__file__).resolve();LT_ROOT=LT_SCRIPT.parent
LT_HELPER=LT_ROOT/'plan_CAM_large_contact_return.py';__file__=str(LT_HELPER)
exec(compile(LT_HELPER.read_text().split('\nfor start,end in [',1)[0],str(LT_HELPER),'exec'),globals())
__file__=str(LT_SCRIPT)
LT_OUT=LC_OUT/'side_turn';LT_OUT.mkdir(exist_ok=True)
lt_started=time.time();lt_trials=[];lt_selected=None
lt_begin=.7975;lt_peak=.8075;lt_end=.82


def lt_bump(f):
    return max(0.,min((f-lt_begin)/(lt_peak-lt_begin),(lt_end-f)/(lt_end-lt_peak)))


def lt_path(da,dh):
    values=sorted(set([r['fraction'] for r in lr_source]+[lt_begin,lt_peak,lt_end]))
    result=[]
    for f in values:
        amp,angle=lr_original(f);weight=lt_bump(f)
        result.append(dict(fraction=f,amplitude_mm=amp+dh*weight,side_angle_deg=angle+da*weight))
    assert result[0]==lr_source[0] and result[-1]==lr_source[-1]
    return result


lt_grid=[(da,dh) for dh in (0.,-.25,.25,-.5,.5) for da in (-.5,.5,-1.,1.,-2.,2.,-3.,3.)]
lt_grid.sort(key=lambda p:abs(p[0])/2.+abs(p[1])*2.)
for da,dh in lt_grid:
    path=lt_path(da,dh);rows=[];failure=None;changed_positions=0
    edges=list(zip(path,path[1:]));edges.sort(key=lambda e:(not(lt_begin-1e-8<=e[0]['fraction']<=lt_end),e[0]['fraction']))
    critical_edge=next((a,b) for a,b in edges if a['fraction']<=.80625<=b['fraction'])
    cases=[(critical_edge,.80625)]
    cases.extend(((a,b),float(f)) for a,b in edges for f in np.linspace(a['fraction'],b['fraction'],5))
    for edge,f in cases:
        amp,angle=sc_control(edge,f);old_amp,old_angle=lr_original(f)
        changed=abs(amp-old_amp)>1e-10 or abs(angle-old_angle)>1e-10
        failure,curves,contacts=lc_forming_pose(3,edge,f)
        if failure is None and changed:
            changed_positions+=1
            check,_=oe_check(amp,angle,3,f,da_order)
            if check['status']!='PASS':failure=dict(kind='changed_wire_geometry',detail=check)
        rows.append(dict(fraction=f,amplitude_mm=amp,side_angle_deg=angle,changed=changed,
            status='PASS' if failure is None else 'BLOCKED',failure=failure))
        if failure:break
    trial=dict(maximum_side_delta_deg=da,maximum_height_delta_mm=dh,
        status='PASS' if failure is None else 'BLOCKED',checked_positions=len(rows),
        changed_wire_positions=changed_positions,rows=rows)
    lt_trials.append(trial)
    print('LARGER_TURN_TRIAL',da,dh,trial['status'],len(rows),failure,flush=True)
    if failure is None:
        lt_selected=dict(**trial,path=path);break

report=dict(status='PASS' if lt_selected else 'BLOCKED',scope='Finite complete last-stage replay with a small temporary side/height change; no structural edits',
    script_sha256=sha(LT_SCRIPT),helper_sha256=sha(LT_HELPER),source_main_sha256=source_hash,
    source_forming_sha256=sha(lc_forming_path),source_original_downstream_sha256=sha(lr_source_screen),
    contact_dimensions_mm=ft_dims.tolist(),contact_evidence='ASSUMED requested space; not a vendor-qualified finished terminal',
    bump_support_fraction=[lt_begin,lt_peak,lt_end],trials=lt_trials,selected=lt_selected,
    continuous_motion='NOT_TESTED',unchanged_forming_stages=[0,1,2],wire_endpoints_unchanged=True,
    contact_structure_margin_mm=.3,wire_structure_and_wire_margin_mm=.3,contact_wire_margin_mm=0.,
    all_other_contacts_and_wires_retained=True,whole_harness='BLOCKED',main_applied=False,
    manufacturing_release=False,elapsed_s=time.time()-lt_started)
(LT_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('LARGER_TURN_DONE',report['status'],len(lt_trials),flush=True)

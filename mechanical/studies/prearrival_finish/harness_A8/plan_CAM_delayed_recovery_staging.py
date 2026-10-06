"""Test a longer temporary tangent before turning selected free leads upright.

The unchanged final fan is laid from the neck upward. A smooth pulse of straight
length delays the temporary recovery arc for the two rear leads, so they can
advance past the root-seat edge before becoming vertical. All material is
drawn from their existing free terminal straight. No robot solid is changed.
This is a finite search; continuous motion and tangent reconstruction remain
unqualified. Rejected variants are retained, never called impossible routes.
"""
from pathlib import Path
DR_SCRIPT=Path(__file__).resolve();DR_ROOT=DR_SCRIPT.parent
DR_HELPER=DR_ROOT/'plan_CAM_progressive_wire_staging.py';__file__=str(DR_HELPER)
exec(compile(DR_HELPER.read_text().split('\nps_rows=[];',1)[0],str(DR_HELPER),'exec'),globals())
__file__=str(DR_SCRIPT)
DR_OUT=RS_OUT/'delayed_recovery';DR_OUT.mkdir(exist_ok=True)
dr_start=time.time();dr_height=0.;dr_fraction=0.;dr_rows=[];dr_saved={}


def dr_curve(slot,fraction):
    q=us_target[slot];s=ps_arc[slot];length=float(s[-1])
    nonvertical=np.where(np.linalg.norm(us_T[slot][:,:2],axis=1)>1e-7)[0]
    end_s=float(s[int(nonvertical[-1])+1]) if len(nonvertical) else 0.
    cut=fraction*end_s
    lead=dr_height*math.sin(math.pi*fraction/.35)**2 if slot in (0,2) and 0.<fraction<.35 else 0.
    if fraction>=1.-1e-12:
        return q.copy(),dict(cut_arclength_mm=end_s,temporary_lead_mm=0.,
            temporary_arc_length_mm=0.,upper_straight_mm=length-end_s,
            analytic_constructed_length_change_mm=0.,polyline_length_change_mm=0.)
    ix=min(len(us_T[slot])-1,int(np.searchsorted(s,cut,side='right')-1))
    t=us_T[slot][ix];p=q[ix]+t*(cut-s[ix]);alpha=math.acos(np.clip(t[2],-1.,1.))
    prefix=np.vstack([q[:ix+1],p]) if np.linalg.norm(p-q[ix])>1e-10 else q[:ix+1].copy()
    line=np.linspace(p,p+lead*t,max(2,int(math.ceil(lead/.008))+1))
    p=line[-1]
    if alpha>1e-8:
        axis=np.r_[t[:2],0.];axis/=np.linalg.norm(axis)
        n=max(2,int(math.ceil(ps_radius*alpha/.008)))
        a=np.linspace(alpha,0.,n+1)
        arc=p+ps_radius*(np.cos(a)-math.cos(alpha))[:,None]*axis
        arc+=ps_radius*(math.sin(alpha)-np.sin(a))[:,None]*np.array([0.,0.,1.])
        arc_length=ps_radius*alpha
        chord_error=ps_radius*(1.-math.cos(alpha/(2*n)))
    else:
        arc=p[None,:];arc_length=0.;chord_error=0.
    remaining=length-cut-lead-arc_length
    assert remaining>2.,(slot,fraction,remaining)
    end=arc[-1]+[0.,0.,remaining]
    tail=np.linspace(arc[-1],end,max(2,int(math.ceil(remaining/.008))+1))
    points=np.vstack([prefix,line[1:],arc[1:],tail[1:]])
    delta=float(np.linalg.norm(np.diff(points,axis=0),axis=1).sum()-length)
    return points,dict(cut_arclength_mm=cut,temporary_lead_mm=lead,
        temporary_turn_deg=math.degrees(alpha),temporary_arc_length_mm=arc_length,
        temporary_arc_chord_error_mm=chord_error,upper_straight_mm=remaining,
        analytic_constructed_length_change_mm=cut+lead+arc_length+remaining-length,
        polyline_length_change_mm=delta)


def rs_curves(unused):
    curves=[];info=[]
    for slot in range(4):
        q,diag=dr_curve(slot,dr_fraction)
        meta=dict(us_info[slot]);meta.update(diag,curve_error_bound_mm=ps_error,
            fraction=dr_fraction,free_end_mm=q[-1].tolist(),
            target_radius_is_not_staged_radius_certificate=True,
            staged_radius_certificate='NOT_TESTED',splice_tangent_error='NOT_TESTED')
        curves.append(q);info.append(meta)
    return curves,info


selected=None
fractions=[.2,.225,.25,.175,.1875,.2125,.2375,.2625,.275,.3,.325,.35,.1,.125,.15,0.]
for height in [4.,8.,12.,16.]:
    dr_height=height;rows=[]
    for f in fractions:
        dr_fraction=f;result,curves,info=rs_check(0.)
        crimp=rx_exact_crimp(curves,info)
        if result['status']=='PASS' and crimp['status']!='PASS':result=crimp
        rows.append(dict(fraction=f,result=result,curves=info,exact_crimp_check=crimp))
        print('DELAYED_RECOVERY',height,f,result['status'],result.get('kind'),result.get('slot'),
              result.get('detail'),round(time.time()-dr_start,1),flush=True)
        for slot,q in enumerate(curves):dr_saved[f'h{height:g}_f{f:g}_slot{slot}']=q
        if result['status']!='PASS':break
    ok=len(rows)==len(fractions) and all(row['result']['status']=='PASS' for row in rows)
    dr_rows.append(dict(lead_pulse_max_mm=height,status='PASS' if ok else 'BLOCKED',rows=rows))
    if ok:selected=height;break
np.savez_compressed(DR_OUT/'curves.npz',**dr_saved)
report=dict(status='PASS' if selected is not None else 'BLOCKED',
    scope='Finite early-stage delayed-recovery search; no complete staging or physical certificate',
    source_main_sha256=source_hash,script_sha256=sha(DR_SCRIPT),helper_sha256=sha(DR_HELPER),
    source_target_seating_sha256=sha(RX_OUT/'verification.json'),
    source_progressive_sha256=sha(PS_OUT/'screen.json'),curves_sha256=sha(DR_OUT/'curves.npz'),
    source_fixture_ids=[t[0] for t in rs_targets],uninstalled_tie_parts=sorted(rs_omitted),
    pulse_fraction_range=[0.,.35],pulse_slots=[0,2],trial_maximum_leads_mm=[4.,8.,12.,16.],
    trials=dr_rows,selected_lead_mm=selected,wire_OD_mm=OD,ordinary_structure_margin_mm=.3,
    provisional_curve_error_mm=ps_error,continuous_motion='NOT_TESTED',
    splice_tangent_error='NOT_TESTED',staged_radius_certificate='NOT_TESTED',
    initial_vertical_feed='Separate local sweep only',complete_body_end_feed='NOT_TESTED',
    actual_contact_profile='NOT_TESTED',main_applied=False,whole_harness='BLOCKED',
    manufacturing_release=False,elapsed_s=time.time()-dr_start)
(DR_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('DELAYED_RECOVERY_DONE',report['status'],selected,round(time.time()-dr_start,1),flush=True)

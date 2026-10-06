"""Screen progressive bottom-up dressing of the four unanchored CAM leads.

Keep the already-dressed target prefix; join its tangent to vertical with a
temporary 7.2-mm circle and use the remaining length as a straight upper tail.
This is a finite polyline diagnostic. Target tangent sampling, splice error,
continuous motion and physical material behaviour are not yet certified.
"""
from pathlib import Path
PS_SCRIPT=Path(__file__).resolve();PS_ROOT=PS_SCRIPT.parent
PS_HELPER=PS_ROOT/'plan_CAM_upper_wire_staging.py';__file__=str(PS_HELPER)
exec(compile(PS_HELPER.read_text().split('\nus_rows=[];',1)[0],str(PS_HELPER),'exec'),globals())
__file__=str(PS_SCRIPT)
PS_OUT=RS_OUT/'progressive_staging';PS_OUT.mkdir(exist_ok=True)
ps_started=time.time();ps_radius=7.2;ps_error=.003
ps_arc=[np.r_[0.,np.cumsum(ds)] for ds in us_ds]
ps_fractions=[0.]*4


def ps_curve(slot,fraction):
    q=us_target[slot];s=ps_arc[slot];length=float(s[-1])
    # Only advance through the portion below the final vertical tail.
    nonvertical=np.where(np.linalg.norm(us_T[slot][:,:2],axis=1)>1e-7)[0]
    end_s=float(s[int(nonvertical[-1])+1]) if len(nonvertical) else 0.
    cut=fraction*end_s
    if fraction>=1.-1e-12:
        return q.copy(),dict(cut_arclength_mm=end_s,temporary_turn_deg=0.,
            temporary_arc_length_mm=0.,upper_straight_mm=length-end_s,
            polyline_length_change_mm=0.,temporary_arc_chord_error_mm=0.)
    ix=min(len(us_T[slot])-1,int(np.searchsorted(s,cut,side='right')-1))
    t=us_T[slot][ix];p=q[ix]+t*(cut-s[ix]);alpha=math.acos(np.clip(t[2],-1.,1.))
    prefix=np.vstack([q[:ix+1],p]) if np.linalg.norm(p-q[ix])>1e-10 else q[:ix+1].copy()
    if alpha>1e-8:
        axis=np.array([t[0],t[1],0.]);axis/=np.linalg.norm(axis)
        n=max(2,int(math.ceil(ps_radius*alpha/.008)))
        a=np.linspace(alpha,0.,n+1)
        arc=p+ps_radius*(np.cos(a)-math.cos(alpha))[:,None]*axis
        arc+=ps_radius*(math.sin(alpha)-np.sin(a))[:,None]*np.array([0.,0.,1.])
        arc_length=ps_radius*alpha
        chord_error=ps_radius*(1.-math.cos(alpha/(2*n)))
    else:
        arc=p[None,:];arc_length=0.;chord_error=0.
    # Exact circular length rather than the slightly shorter chord sum.
    remaining=length-cut-arc_length
    assert remaining>2.,(slot,fraction,remaining)
    end=arc[-1]+[0.,0.,remaining]
    tail=np.linspace(arc[-1],end,max(2,int(math.ceil(remaining/.008))+1))
    points=np.vstack([prefix,arc[1:],tail[1:]])
    delta=float(np.linalg.norm(np.diff(points,axis=0),axis=1).sum()-length)
    return points,dict(cut_arclength_mm=cut,temporary_turn_deg=math.degrees(alpha),
        temporary_arc_length_mm=arc_length,upper_straight_mm=remaining,
        polyline_length_change_mm=delta,analytic_constructed_length_change_mm=cut+arc_length+remaining-length,
        temporary_arc_chord_error_mm=chord_error)


def rs_curves(unused):
    curves=[];info=[]
    for slot,fraction in enumerate(ps_fractions):
        q,diag=ps_curve(slot,fraction)
        meta=dict(us_info[slot]);meta.update(diag,curve_error_bound_mm=ps_error,
            fraction=fraction,free_end_mm=q[-1].tolist(),
            target_radius_is_not_staged_radius_certificate=True,
            staged_radius_certificate='NOT_TESTED',splice_tangent_error='NOT_TESTED')
        curves.append(q);info.append(meta)
    return curves,info


ps_rows=[];ps_saved={}
for fraction in np.linspace(0.,1.,41):
    ps_fractions=[float(fraction)]*4
    result,curves,info=rs_check(0.)
    crimp=rx_exact_crimp(curves,info)
    if result['status']=='PASS' and crimp['status']!='PASS':result=crimp
    ps_rows.append(dict(fractions=ps_fractions.copy(),result=result,exact_crimp_check=crimp,curves=info))
    if any(abs(fraction-v)<1e-9 for v in [0.,.25,.5,.75,1.]):
        for slot,p in enumerate(curves):ps_saved[f'f{fraction:g}_slot{slot}']=p
    print('PROGRESSIVE_STAGING',round(float(fraction),3),result['status'],result.get('kind'),
        result.get('slot'),result.get('other'),result.get('detail'),round(time.time()-ps_started,1),flush=True)
np.savez_compressed(PS_OUT/'curves.npz',**ps_saved)
status='PASS' if all(r['result']['status']=='PASS' for r in ps_rows) else 'BLOCKED'
report=dict(status=status,scope='Forty-one finite bottom-up dressing poses; sampled-tangent route diagnostic only',
    source_main_sha256=source_hash,script_sha256=sha(PS_SCRIPT),helper_sha256=sha(PS_HELPER),
    source_target_seating_sha256=sha(RX_OUT/'verification.json'),
    curves_sha256=sha(PS_OUT/'curves.npz'),rows=ps_rows,
    source_fixture_ids=[t[0] for t in fm_targets],uninstalled_tie_parts=sorted(rs_omitted),
    wire_OD_mm=OD,ordinary_structure_margin_mm=.3,temporary_turn_radius_mm=ps_radius,
    provisional_curve_error_mm=ps_error,continuous_motion='NOT_TESTED',
    splice_tangent_error='NOT_TESTED',staged_radius_certificate='NOT_TESTED',
    initial_vertical_feed='NOT_TESTED',complete_body_end_feed='NOT_TESTED',
    actual_contact_profile='NOT_TESTED',main_applied=False,whole_harness='BLOCKED',
    manufacturing_release=False,elapsed_s=time.time()-ps_started)
(PS_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('PROGRESSIVE_STAGING_DONE',status,round(time.time()-ps_started,1),flush=True)

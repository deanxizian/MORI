"""Resolve the first conservative continuous-screen failure on exact segments.

This does not alter the path or waive the0.3mm conductor clearance. The
distance is a polyline result with explicit smooth-curve and numeric error.
"""
from pathlib import Path
DC_SCRIPT=Path(__file__).resolve();DC_ROOT=DC_SCRIPT.parent
DC_HELPER=DC_ROOT/'check_CAM_sequential_continuous.py';__file__=str(DC_HELPER)
exec(compile(DC_HELPER.read_text().split('\n# Static mixed states',1)[0],str(DC_HELPER),'exec'),globals())
__file__=str(DC_SCRIPT)


def dc_segments(a,b,c,d):
    """One segment against a vector of segments, including all boundaries."""
    v=b-a;w=d-c;r=a-c;vv=float(v@v)
    ww=np.einsum('ij,ij->i',w,w);vw=w@v;vr=r@v;wr=np.einsum('ij,ij->i',w,r)
    denom=vv*ww-vw*vw;valid=denom>1e-18
    ss=np.divide(vw*wr-ww*vr,denom,out=np.zeros_like(denom),where=valid)
    tt=np.divide(vv*wr-vw*vr,denom,out=np.zeros_like(denom),where=valid)
    choices=[(np.zeros(len(c)),np.clip(wr/ww,0.,1.)),
             (np.ones(len(c)),np.clip((wr+vw)/ww,0.,1.)),
             (np.clip(-vr/vv,0.,1.),np.zeros(len(c))),
             (np.clip((vw-vr)/vv,0.,1.),np.ones(len(c)))]
    best=np.full(len(c),np.inf);best_s=np.zeros(len(c));best_t=np.zeros(len(c))
    for s,t in choices+[(ss,tt)]:
        delta=r+s[:,None]*v-t[:,None]*w;dd=np.einsum('ij,ij->i',delta,delta)
        if s is ss:dd=np.where(valid&(ss>=0)&(ss<=1)&(tt>=0)&(tt<=1),dd,np.inf)
        take=dd<best;best[take]=dd[take];best_s[take]=s[take];best_t[take]=t[take]
    return np.sqrt(best),best_s,best_t


def dc_closest(p,target,search_mm=2.):
    q,qs,tree,step=target;best=None;count=0
    # If a polyline pair is within search_mm, an endpoint of its static
    # segment lies within search_mm plus both segment half-lengths of the
    # moving segment midpoint. Adjacent IDs recover that complete segment.
    lo=q.min(0);hi=q.max(0)
    for i,(a,b) in enumerate(zip(p,p[1:])):
        mid=(a+b)/2.;radius=search_mm+float(np.linalg.norm(b-a))/2.+step/2.+1e-5
        lower=np.linalg.norm(np.maximum(np.maximum(lo-mid,mid-hi),0.))
        if lower>radius:continue
        ids=set()
        for _,j,_ in tree.find_range(Vector(mid),radius):
            if j>0:ids.add(j-1)
            if j<len(q)-1:ids.add(j)
        if not ids:continue
        ids=np.array(sorted(ids));dist,s,t=dc_segments(a,b,q[ids],q[ids+1]);j=int(np.argmin(dist));count+=len(ids)
        if best is None or float(dist[j])<best['polyline_distance_mm']:
            k=int(ids[j]);best={'polyline_distance_mm':float(dist[j]),'segments':[i,k],
                'parameters':[float(s[j]),float(t[j])],
                'points_mm':[(a+s[j]*(b-a)).tolist(),(q[k]+t[j]*(q[k+1]-q[k])).tolist()]}
    assert best is not None
    best['segment_pairs_checked']=count;best['search_radius_mm']=search_mm
    return best


if __name__=='__main__':
    prior=json.loads((SC_OUT/'screen.json').read_text())
    row=prior['nominal_intermediate_failures'][0];stage=row['stage'];f=row['fraction']
    path=sc_path['stages'][stage]['path'];edge=next((a,b) for a,b in zip(path,path[1:]) if a['fraction']<=f<=b['fraction'])
    p,u,e=sc_curve(stage,edge,f);other=row['failure']['other_slot'];target=pw_fans[other]
    nearest=dc_closest(p,target);err=e+pw_fan_errors[other]+1e-4
    nearest['wire_surface_gap_lower_mm']=nearest['polyline_distance_mm']-OD-err
    nearest['smooth_curve_error_sum_mm']=e+pw_fan_errors[other]
    nearest['numeric_guard_mm']=1e-4;nearest['required_surface_gap_mm']=.3
    result={'status':'PASS' if nearest['wire_surface_gap_lower_mm']>=.3 else 'BLOCKED',
        'scope':'Only first intermediate active-wire to upstream-fan pair at one position',
        'source_main_sha256':source_hash,'script_sha256':sha(DC_SCRIPT),'helper_sha256':sha(DC_HELPER),
        'source_failure_sha256':sha(SC_OUT/'screen.json'),'fraction':f,'stage':stage,
        'active_slot':row['active_slot'],'other_slot':other,'controls':sc_control(edge,f),
        'closest':nearest,'real_intersection':'FAIL' if nearest['polyline_distance_mm']+err<OD else 'NOT_PROVEN',
        'whole_continuous_path':'BLOCKED','main_applied':False}
    (SC_OUT/'first_failure_segment_distance.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print('SEGMENT_DIAGNOSIS',result,flush=True)

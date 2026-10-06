"""Numerical cross-check of the analytic displacement implementation.

This tests the implementation at sampled parameters; the finite audit is
not itself a proof of continuous collision clearance or physical behavior.
"""
from pathlib import Path
MA_SCRIPT=Path(__file__).resolve();MA_ROOT=MA_SCRIPT.parent
MA_HELPER=MA_ROOT/'check_CAM_sequential_continuous.py';__file__=str(MA_HELPER)
exec(compile(MA_HELPER.read_text().split('\n# Static mixed states',1)[0],str(MA_HELPER),'exec'),globals())
__file__=str(MA_SCRIPT)
rng=np.random.default_rng(471004);rows=[]
for case in range(120):
    a=float(rng.uniform(0.,.999));width=float(min(rng.uniform(.0001,.025),1.-a));b=a+width;mid=(a+b)/2.
    edge=({'fraction':a,'amplitude_mm':float(rng.uniform(0.,24.)),'side_angle_deg':float(rng.uniform(-84.,84.))},
          {'fraction':b,'amplitude_mm':float(rng.uniform(0.,24.)),'side_angle_deg':float(rng.uniform(-84.,84.))})
    stage=case%4;p,u,e=sc_curve(stage,edge,mid);d,meta=sc_bound(stage,edge,a,b,p,u)
    contact_bound=sc_contact_bound(stage,edge,a,b,p,u)
    _,cm=ft_frame(mid,p[-1]);vertices=np.array([[x,y,z] for x in [-.4,.4] for y in [-.675,.675] for z in [-1.95,1.95]])
    cpm=vertices@cm[:,:3].T+cm[:,3];maximum_ratio=0.;maximum_contact_ratio=0.;max_violation=-math.inf
    for f in [a,a+width*.125,a+width*.375,a+width*.625,a+width*.875,b]:
        q,v,qe=sc_curve(stage,edge,f);qi=np.column_stack([np.interp(u,v,q[:,i]) for i in range(3)])
        movement=np.linalg.norm(qi-p,axis=1);allowance=d+e+qe+2e-5
        max_violation=max(max_violation,float(np.max(movement-allowance)))
        mask=d>1e-8
        if np.any(mask):maximum_ratio=max(maximum_ratio,float(np.max(movement[mask]/allowance[mask])))
        _,cf=ft_frame(f,q[-1]);cpf=vertices@cf[:,:3].T+cf[:,3]
        cmove=float(np.linalg.norm(cpf-cpm,axis=1).max());maximum_contact_ratio=max(maximum_contact_ratio,cmove/(contact_bound+2e-5))
        assert cmove<=contact_bound+2e-5,(case,f,cmove,contact_bound)
    assert max_violation<=0.,(case,max_violation)
    rows.append({'case':case,'interval':[a,b],'wire_max_fraction_of_bound':maximum_ratio,
                 'contact_max_fraction_of_bound':maximum_contact_ratio,'max_wire_violation_mm':max_violation})
result={'status':'PASS','scope':'Finite implementation audit of analytic point and contact displacement bounds,120 intervals times6 positions',
    'source_main_sha256':source_hash,'script_sha256':sha(MA_SCRIPT),'helper_sha256':sha(MA_HELPER),
    'seed':471004,'rows':rows,'complete_geometric_clearance_proof':False,'main_applied':False}
(SC_OUT/'math_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('SEQUENTIAL_BOUND_AUDIT',len(rows),'max_wire_ratio',max(r['wire_max_fraction_of_bound'] for r in rows),
      'max_contact_ratio',max(r['contact_max_fraction_of_bound'] for r in rows),flush=True)

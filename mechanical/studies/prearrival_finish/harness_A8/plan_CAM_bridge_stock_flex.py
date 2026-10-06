"""Keep the body PH connector seated while supplying length from upright stock.

Compare bounded, explicitly prescribed flexible wire families during the
body/bridge stages. This is a finite clearance diagnostic, not a wire-force,
minimum-radius certificate, automatic assembly or supplier length release.
"""
from pathlib import Path
FLEX_SCRIPT=Path(__file__).resolve();FLEX_HELPER=FLEX_SCRIPT.parent/'screen_CAM_bridge_wire_stock.py'
text=FLEX_HELPER.read_text().split('\nstages=',1)[0]
writer="np.savez_compressed(STOCK_OUT/'full_wires.npz',**{'pin'+str(k):v for k,v in wire.items()})"
assert text.count(writer)==1
text=text.replace(writer,'# Model-only import: preserve the earlier report arrays.')
__file__=str(FLEX_HELPER);exec(compile(text,str(FLEX_HELPER),'exec'),globals());__file__=str(FLEX_SCRIPT)
FLEX_OUT=STOCK_OUT/'body_fixed_flex';FLEX_OUT.mkdir(exist_ok=True)
from mathutils.kdtree import KDTree
original={pin:partial[f'pin{pin}_yaw0'] for pin in range(1,5)}
meta={}
for pin,p in original.items():
    s=np.r_[0.,np.linalg.norm(np.diff(p,axis=0),axis=1).cumsum()]
    ids=np.flatnonzero((np.linalg.norm(p[:,:2],axis=1)<20)&(p[:,2]<141)&(p[:,2]>137))
    assert len(ids),pin
    grid=np.linspace(0,s[-1],math.ceil(s[-1]/.025)+1)
    pts=np.column_stack([np.interp(grid,s,p[:,i]) for i in range(3)])
    meta[pin]=dict(s=grid,p=pts,end_weight_s=float(s[ids[0]]),original_error=lengths[pin-1]['curve_chord_error_mm'])

def family(pin,shift,start_s,end_advance):
    d=meta[pin];end_s=d['end_weight_s']-end_advance;span=end_s-start_s
    if span<12:return None,dict(reason='blend_span_too_short',span_mm=span)
    u=np.clip((d['s']-start_s)/span,0,1);w=u**3*(10-15*u+6*u*u)
    q=d['p']+w[:,None]*shift
    used=float(np.linalg.norm(np.diff(q,axis=0),axis=1).sum())
    remaining=lengths[pin-1]['full_nominal_allocation_mm']-used
    if remaining<5:return None,dict(reason='insufficient_upright_stock',remaining_mm=remaining)
    tail=q[-1]+np.linspace(0,remaining,math.ceil(remaining/.025)+1)[:,None]*[0.,0.,1.]
    full=np.vstack([q,tail[1:]])
    # Each p sample represents the earlier source curve within its stored
    # chord bound. Bound the added quintic interpolation separately, using a
    # deliberately loose |w''|<=60/span^2 and the longest source chord.
    source_step=float(np.max(np.linalg.norm(np.diff(original[pin],axis=0),axis=1)))
    extra_error=float(np.linalg.norm(shift))*60*source_step**2/(8*span**2)
    error=d['original_error']+extra_error+1e-5
    s=np.r_[0.,np.linalg.norm(np.diff(full,axis=0),axis=1).cumsum()]
    centers=np.arange(.5,s[-1]-.5,.5)
    aa=np.column_stack([np.interp(centers-.5,s,full[:,i]) for i in range(3)])
    bb=np.column_stack([np.interp(centers,s,full[:,i]) for i in range(3)])
    cc=np.column_stack([np.interp(centers+.5,s,full[:,i]) for i in range(3)])
    ab=bb-aa;bc=cc-bb;ac=cc-aa
    cross=np.linalg.norm(np.cross(ab,bc),axis=1)
    radii=np.divide(np.linalg.norm(ab,axis=1)*np.linalg.norm(bc,axis=1)*np.linalg.norm(ac,axis=1),2*cross,
                    out=np.full(len(cross),np.inf),where=cross>1e-10)
    return full,dict(remaining_upright_mm=remaining,body_polyline_mm=used,
        full_polyline_mm=float(s[-1]),target_polyline_mm=lengths[pin-1]['full_nominal_allocation_mm'],
        curve_deviation_bound_mm=error,minimum_three_point_radius_sample_mm=float(np.min(radii)),
        radius_sample_is_certificate=False,weight_start_mm=start_s,weight_end_mm=end_s)

def mutual(curves,details):
    minimum=math.inf
    for a,b in itertools.combinations(curves,2):
        pa=curves[a];pb=curves[b];tree=KDTree(len(pb))
        for i,p in enumerate(pb):tree.insert(p,i)
        tree.balance();ma=float(np.linalg.norm(np.diff(pa,axis=0),axis=1).max());mb=float(np.linalg.norm(np.diff(pb,axis=0),axis=1).max())
        dist=min(tree.find(p)[2] for p in pa)
        gap=dist-OD-(ma+mb)/2-details[a]['curve_deviation_bound_mm']-details[b]['curve_deviation_bound_mm']
        minimum=min(minimum,gap)
        if gap<.3:return dict(kind='mutual_wire',pins=[a,b],gap_bound_mm=gap)
    return None

poses=[]
poses += [('bridge_lift',float(z),shellpose(15,0,14),trans(z=float(z))) for z in (0,.5,1,3,6,12,18)]
poses += [('body_back',float(y),shellpose(15,float(y),14),trans(y=float(y),z=18)) for y in (-7,-14)]
poses += [('body_bench',float(z),shellpose(15,-14,float(z)),trans(y=-14,z=float(z+4))) for z in (40,80,140)]
poses += [('shell_settle',float(u),shellpose(15*u,0,14*u),I) for u in (0.,.25,.5,.75,1.)]
rows=[];started=time.time();saved={}
for start_s,end_advance in itertools.product((5.,10.,20.,30.,40.),(0.,5.)):
    cases=[]
    for stage,position,st,bt in poses:
        mats={'core':I,'upper':np.linalg.inv(st),'bridge':np.linalg.inv(bt)}
        failure=rigid_check(housing,mats,True);curves={};details={}
        for pin in range(1,5):
            if failure:break
            curve,detail=family(pin,bt[:3,3],start_s,end_advance);details[pin]=detail
            if curve is None:failure=dict(kind='material_family',pin=pin,**detail);break
            curves[pin]=curve
            lengths[pin-1]['curve_chord_error_mm']=detail['curve_deviation_bound_mm']
            failure=wire_check(pin,curve,mats)
            if not failure and detail['minimum_three_point_radius_sample_mm']<6.5:
                failure=dict(kind='tight_radius_sample',pin=pin,**detail)
        if not failure:failure=mutual(curves,details)
        case=dict(stage=stage,position=position,status='BLOCKED' if failure else 'PASS',failure=failure,
                  material={str(k):v for k,v in details.items()})
        cases.append(case)
        if failure:
            for pin,p in curves.items():saved[f's{start_s}_a{end_advance}_{stage}_pin{pin}']=p
            break
    row=dict(weight_start_mm=start_s,weight_end_advance_mm=end_advance,
        status='PASS' if len(cases)==len(poses) and all(c['status']=='PASS' for c in cases) else 'BLOCKED',
        cases=cases,planned_positions=len(poses));rows.append(row)
    print('BRIDGE_STOCK_FLEX',start_s,end_advance,row['status'],len(cases),cases[-1]['failure'],round(time.time()-started,2),flush=True)
    if row['status']=='PASS':
        for pin,p in curves.items():saved['selected_pin'+str(pin)]=p
        break
np.savez_compressed(FLEX_OUT/'witness_curves.npz',**saved)
report=dict(status='PASS' if any(r['status']=='PASS' for r in rows) else 'BLOCKED',
    scope='Finite fixed-body-housing flexible-prefix families with constant nominal total wire polylines and explicit upright stock; not a complete assembly or bend proof',
    script_sha256=sha(FLEX_SCRIPT),helper_sha256=sha(FLEX_HELPER),helper_import_mode='Definitions before stages; earlier NPZ writer omitted explicitly',
    source_main_sha256=source_hash,protected_sources=protected,source_split_report_sha256=sha(membership_path),
    source_files={str(p.relative_to(PROJECT)):sha(p) for p in [partial_path,datum_path,body_math_path,fixed_path]},
    substituted_unadopted_prints=membership['substituted_unadopted_prints'],
    source_objects=209,present_source_objects=len(core|upper|bridge),mating_allocations=len(plug),fixed_wire_solids=len(fixed),
    rows=rows,witness_curves_sha256=sha(FLEX_OUT/'witness_curves.npz'),
    wire_OD_mm=OD,clearance_requirement_mm=.3,required_bend_radius_mm=REQUIRED_R,
    reference_body_housing_fit='NOT_TESTED',terminal_tip_sweeps='NOT_TESTED',continuous_motion='NOT_TESTED',
    minimum_bend_radius_certificate='NOT_TESTED',later_yaw_threading='NOT_TESTED',
    no_global_impossibility_claim=True,main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,
    elapsed_s=time.time()-started)
(FLEX_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('BRIDGE_STOCK_FLEX_DONE',report['status'],round(time.time()-started,2),flush=True)

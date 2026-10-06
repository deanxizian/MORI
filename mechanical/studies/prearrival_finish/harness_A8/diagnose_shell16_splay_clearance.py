"""Resolve marginal splay rejections with adaptive distance bounds.

The distance to a closed surface is 1-Lipschitz. A chord of length L with
endpoint distances d0,d1 therefore has lower bound (d0+d1-L)/2. Original
analytic sagitta and 0.0001 mm numerical allowance are retained. This diagnoses
clearance, not strength, real cable flexibility or manufacturing acceptance.
"""
from pathlib import Path
EXACT16_SCRIPT=Path(__file__).resolve()
EXACT16_HELPER=EXACT16_SCRIPT.parent/'screen_shell16_temporary_tail_splay.py'
__file__=str(EXACT16_HELPER)
exec(compile(EXACT16_HELPER.read_text().split('\ntrials=[];',1)[0],str(EXACT16_HELPER),'exec'),globals())
__file__=str(EXACT16_SCRIPT)
OUT=ORDER_OUT/'shell16_splay_clearance';OUT.mkdir(exist_ok=True)
baseline_path=ORDER_OUT/'shell16_back20_merged/screen.json'
baseline=json.loads(baseline_path.read_text())
parameters={int(p):dict(q) for p,q in baseline['records'][-1]['parameters'].items()}
set_pose(-2.)


def adaptive_surface_check(pts,tree,error):
    required=OD/2+MARGIN
    numeric=.0001
    nearest=lambda q:float(tree.find_nearest(Vector(q))[3])
    distances=np.array([nearest(p) for p in pts])
    i=int(np.argmin(distances))
    # The original curve lies within the retained sagitta distance of its
    # polyline. Even the far side of that allowance violates the target here.
    if distances[i]+error+numeric < required:
        return dict(status='FAIL',kind='demonstrated_surface_margin_shortfall',
                    point_mm=pts[i].tolist(),distance_mm=float(distances[i]),
                    surface_gap_upper_bound_mm=float(distances[i]+error+numeric-OD/2)),0
    pending=[(a,b,float(da),float(db),0) for a,b,da,db in zip(pts[:-1],pts[1:],distances[:-1],distances[1:])]
    refinements=0;certified=0;unresolved=[]
    while pending:
        a,b,da,db,depth=pending.pop();length=float(np.linalg.norm(b-a))
        lower=(da+db-length)/2-error-numeric
        if lower>=required:
            certified+=1;continue
        middle=(a+b)/2;dm=nearest(middle);refinements+=1
        if dm+error+numeric < required:
            return dict(status='FAIL',kind='demonstrated_surface_margin_shortfall',
                        point_mm=middle.tolist(),distance_mm=dm,
                        surface_gap_upper_bound_mm=dm+error+numeric-OD/2),refinements
        if depth>=14:
            unresolved.append(dict(point_mm=middle.tolist(),chord_length_mm=length,
                                   lower_bound_mm=lower-OD/2,upper_bound_mm=dm+error+numeric-OD/2))
            continue
        pending.extend([(a,middle,da,dm,depth+1),(middle,b,dm,db,depth+1)])
    return dict(status='BLOCKED' if unresolved else 'PASS',
                kind='uncertain_bound' if unresolved else 'all_chords_certified',
                certified_intervals=certified,unresolved=unresolved),refinements


rows=[];saved={}
for angle in [0.,1.,2.,3.,3.5,4.,5.,6.]:
    p=dict(parameters[1],tail_yaw_deg=angle)
    c,coarse=one(1,p)
    if c is None:
        rows.append(dict(tail_yaw_deg=angle,status='BLOCKED',failure=coarse));continue
    pts=transform_points(c['points'],matrices['bridge'])
    _,lo,hi,tree=target_data['Yaw_Base']
    error=c['curve_chord_error_mm']
    # Select whole contiguous polyline neighborhoods capable of entering the
    # padded target bounds. Coarse bounds already exclude the other segments.
    step=float(np.max(np.linalg.norm(np.diff(pts,axis=0),axis=1)))
    padding=OD/2+MARGIN+error+step+.0001
    close=np.flatnonzero(np.all(pts>=lo-padding,axis=1)&np.all(pts<=hi+padding,axis=1))
    if len(close):
        first=max(0,int(close[0])-1);last=min(len(pts),int(close[-1])+2)
        result,count=adaptive_surface_check(pts[first:last],tree,error)
    else:result=dict(status='PASS',kind='outside_padded_bounds');count=0
    row=dict(tail_yaw_deg=angle,status=result['status'],coarse_failure=coarse,
             original_error_mm=error,adaptive_queries=count,result=result)
    rows.append(row);saved[f'angle{angle:g}']=c['points']
    print('SPLAY_PRECISE',angle,row['status'],result,count,flush=True)
np.savez_compressed(OUT/'curves.npz',**saved)
report=dict(status='PASS',scope='Distance-bound diagnosis for CAM1 versus Yaw_Base only',
    script_sha256=sha(EXACT16_SCRIPT),helper_sha256=sha(EXACT16_HELPER),
    source_files={str(baseline_path.relative_to(PROJECT)):sha(baseline_path),**baseline['source_files']},
    protected_sources=protected,rows=rows,wire_OD_mm=OD,required_surface_margin_mm=MARGIN,
    numerical_allowance_mm=.0001,original_analytic_error_retained=True,
    curves_sha256=sha(OUT/'curves.npz'),whole_path='NOT_TESTED',wire_pairs='NOT_TESTED',
    solid_inside_checks='Inherited from source coarse check; this is a surface-distance diagnosis only',
    complete_attached_assembly='BLOCKED',main_applied=False,manufacturing_release=False)
(OUT/'diagnosis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('SPLAY_PRECISE_DONE',len(rows),flush=True)

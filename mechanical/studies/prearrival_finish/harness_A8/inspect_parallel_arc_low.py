"""Read-only specific lower-loop diagnostic, retaining source geometry."""
from pathlib import Path
LOW_SCRIPT=Path(__file__).resolve();LOW_ROOT=LOW_SCRIPT.parent
LOW_HELPER=LOW_ROOT/'plan_cam_parallel_arcs.py';__file__=str(LOW_HELPER)
exec(compile(LOW_HELPER.read_text().split('\ncounts=Counter();',1)[0],str(LOW_HELPER),'exec'),globals())
__file__=str(LOW_SCRIPT);rows=[]
for ay,az,col,rb in [(9.,205.,24.,7.5),(9.,200.,24.,7.5),(9.,197.,24.,7.5),(9.,200.,23.75,7.),(8.,200.,23.5,7.)]:
    params=(ay,az,col,rb);bases=[route(*params,p) for p in range(-20,26,5)]
    if any(b is None for b in bases):continue
    target=max(bases)+10.00001;hits=[]
    for pitch in [0,25,-20]:
        built=route(*params,pitch,target)
        if built is None:hits.append({'pitch':pitch,'reason':'height'});continue
        points,r=built
        for i,x in enumerate(xx):
            hit=check_curve(points+[x-xc,0.,0.],r['curve_error_bound_mm'],pitch,False)
            if hit:hits.append({'slot':i,**hit});break
    row={'parameters':params,'hits':hits};rows.append(row);print('ARC_LOW_DIAG',row,flush=True)
(LOW_ROOT/'cam_parallel_pitch/arc_low_diagnostic.json').write_text(json.dumps({'rows':rows,'main_applied':False},indent=2)+'\n')

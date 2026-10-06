"""Read-only diagnostics for specific analytic loop heights."""
from pathlib import Path
DIAG_SCRIPT=Path(__file__).resolve();DIAG_ROOT=DIAG_SCRIPT.parent
DIAG_HELPER=DIAG_ROOT/'plan_cam_parallel_arcs.py';__file__=str(DIAG_HELPER)
exec(compile(DIAG_HELPER.read_text().split('\ncounts=Counter();',1)[0],str(DIAG_HELPER),'exec'),globals())
__file__=str(DIAG_SCRIPT)
rows=[]
for az in [234.5,228.,222.,216.,210.,205.]:
    params=(10.,az,25.,7.5)
    base=[route(*params,p) for p in range(-20,26,5)]
    if any(b is None for b in base):continue
    target=max(base)+10.00001;hits=[]
    for pitch in [0,25,-20]:
        built=route(*params,pitch,target)
        if built is None:hits.append({'pitch':pitch,'reason':'height'});continue
        points,r=built
        for i,x in enumerate(xx):
            hit=check_curve(points+[x-xc,0.,0.],r['curve_error_bound_mm'],pitch,False)
            if hit:hits.append({'slot':i,**hit});break
    row={'anchor_z':az,'hits':hits};rows.append(row);print('ARC_HEIGHT_DIAG',row,flush=True)
(DIAG_ROOT/'cam_parallel_pitch/arc_height_diagnostic.json').write_text(json.dumps({'rows':rows,'main_applied':False},indent=2)+'\n')

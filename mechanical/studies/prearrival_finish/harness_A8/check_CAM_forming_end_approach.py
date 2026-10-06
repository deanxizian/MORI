"""Resolve the final part of the raised forming screen without seat waivers."""
from pathlib import Path
FE_SCRIPT=Path(__file__).resolve();FE_ROOT=FE_SCRIPT.parent
FE_HELPER=FE_ROOT/'screen_CAM_wire_forming_raised.py';__file__=str(FE_HELPER)
exec(compile(FE_HELPER.read_text().split('\nfor amplitude in [',1)[0],str(FE_HELPER),'exec'),globals())
__file__=str(FE_SCRIPT)
FE_OUT=FM_OUT/'end_approach';FE_OUT.mkdir(exist_ok=True);fe_rows=[];fe_started=time.time()
for fraction in np.linspace(.975,1.,51):
    fraction=float(fraction);base,parameter,error,extra=fr_curve(fraction,9.);hits=[]
    for slot in range(4):
        points=base+[xx[slot]-xx[0],0.,0.]
        for name,group,m,lo,hi,tree in fm_targets:
            keep=np.ones(len(points),bool)
            if name in {'Pitch_Yoke','CAM_Tie_Head','CAM_Tie_Band'}:keep&=parameter>4.3+1e-5
            ids=np.flatnonzero(keep)
            for span in np.split(ids,np.flatnonzero(np.diff(ids)>1)+1):
                if len(span)<2:continue
                hit=check_one(points[span],error,lo,hi,m,tree)
                if hit:
                    # A loss of the design gap is distinct from the actual
                    # nominal wire intersecting this solid. Query all nearby
                    # stations, not just the first conservative-bound failure.
                    q=points[span];near=np.flatnonzero(np.all(q>=lo-.331,axis=1)&np.all(q<=hi+.331,axis=1))
                    physical=None;mind=1e30
                    for i in near:
                        p=q[i];d=float(tree.find_nearest(Vector(p))[3]);mind=min(mind,d)
                        if d<OD/2.-1e-4:
                            physical={'point_mm':p.tolist(),'distance_to_surface_mm':d,
                                'nominal_wire_radius_mm':OD/2.,'centreline_parameter_mm':float(parameter[span[i]])}
                            break
                    hits.append({'slot':slot,'object':name,'gap_failure':hit,'physical_surface_intersection_witness':physical,
                                 'minimum_queried_centreline_surface_distance_mm':mind if mind<1e20 else None})
    row={'fraction':fraction,'status':'BLOCKED' if hits else 'PASS','hits':hits}
    fe_rows.append(row)
    print('FORMING_END',round(fraction,5),row['status'],[(h['object'],bool(h['physical_surface_intersection_witness'])) for h in hits],flush=True)
report={'status':'PASS' if not any(r['hits'] for r in fe_rows) else 'BLOCKED',
 'scope':'Final forming positions without excluding the CAM seat; source unchanged',
 'source_main_sha256':source_hash,'script_sha256':sha(FE_SCRIPT),'helper_sha256':sha(FE_HELPER),
 'source_raised_screen_sha256':sha(FR_OUT/'screen.json'),'rows':fe_rows,
 'stage_has_CAM_board':False,'CAM_tie_not_yet_tightened':True,'sampling_only':True,
 'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False,'elapsed_s':time.time()-fe_started}
(FE_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('FORMING_END_DONE',report['status'],flush=True)

"""Continuous nominal rigid/wire check: CAM8->2mm over a plug at+2mm.

The board changes position, not the prescribed wire shape. Intended mating
with the separate UART allocation is reported explicitly; it is not a proof
of actual connector compatibility, contact insertion or hand/tool access.
"""
from pathlib import Path
BD_SCRIPT=Path(__file__).resolve();BD_ROOT=BD_SCRIPT.parent
BD_HELPER=BD_ROOT/'check_CAM_board_last.py';__file__=str(BD_HELPER)
exec(compile(BD_HELPER.read_text().split("\nif __name__=='__main__':",1)[0],str(BD_HELPER),'exec'),globals())
__file__=str(BD_SCRIPT)
BD_OUT=BD_ROOT/'cam_wire_forming/lifted_end2';bd_started=time.time()
bd_finite=json.loads((BD_OUT/'screen.json').read_text());assert bd_finite['status']=='PASS'
bd_core,bd_tails,bd_meta=bl_curves(2.,0.)
bd_plug=bl_plug.translate([0.,0.,2.])
bd_fixed={n:m for n,m in bl_fixture.items() if n not in {'CAM_connector_tie_head','CAM_connector_tie_band'}}
bd_passed=[];bd_unproved=[];bd_tests=0
bd_min_gap=math.inf
# The catalogue housing is a convex box. In the board frame its exact
# straight-translation sweep is the hull of its two endpoint placements.
# This resolves tangent surfaces without deleting either surface or
# requiring a positive gap that rigid intended contact does not have.
bd_plug_hull=bd_plug.hull()
assert abs(bd_plug_hull.volume()-bd_plug.volume())<1e-8
assert (bd_plug_hull-bd_plug).volume()<1e-8
bd_plug_sweep=manifold.Manifold.batch_hull([bd_plug.translate([0.,0.,-2.]),bd_plug.translate([0.,0.,-8.])])
bd_exact_plug=[]
for name,m in bl_board.items():
    if name=='CAM_UART_4P':continue
    v=max(0.,float((bd_plug_sweep^m).volume()))
    bd_exact_plug.append({'object':name,'intersection_mm3':v,'minimum_gap_within_1mm':float(bd_plug_sweep.min_gap(m,1.)),
                         'status':'PASS' if v<1e-7 else 'BLOCKED'})


def bd_test(a,b):
    global bd_min_gap
    mid=(a+b)/2.;half=(b-a)/2.;pairs=[]
    # All moving board components translate with unit speed; the closed
    # interval is covered by their midpoint surface gap minus half travel.
    for name,m in bl_board.items():
        placed=m.translate([0.,0.,mid])
        fixtures=bd_fixed
        box=np.array(placed.bounding_box())
        for other,target in fixtures.items():
            bb=np.array(target.bounding_box());bound=half+1e-4
            if np.any(box[:3]>bb[3:]+bound) or np.any(box[3:]<bb[:3]-bound):continue
            volume=max(0.,float((placed^target).volume()))
            if volume>1e-7:return {'kind':'rigid','object':name,'obstacle':other,'intersection_mm3':volume}
            gap=float(placed.min_gap(target,bound+.001))
            if gap<bound:return {'kind':'rigid','object':name,'obstacle':other,'gap_mm':gap,'required_mm':bound}
            pairs.append({'object':name,'obstacle':other,'gap_lower_bound_mm':gap-half})
            bd_min_gap=min(bd_min_gap,gap-half)
    # Only the board moves relative to the fixed +2mm wire shape. Preserve
    # the original source's own-UART exit rule, explicitly enumerated in
    # the output; all other board geometry uses the full0.3mm wire margin.
    for slot in range(4):
        pieces=[('core',bd_core+[xx[slot]-xx[0],0.,0.],bd_meta['core_error_mm']),
                ('tail',bd_tails[slot],bd_meta['tail_error_mm'])]
        for name,m in bl_board.items():
            target=pw_obstacle(name,'board',m);_,_,_,lo,hi,tree=target
            for kind,points,error in pieces:
                local=points-[0.,0.,mid]
                keep=np.ones(len(local),bool)
                if kind=='tail' and name=='CAM_UART_4P':
                    # Exempt only points which stay inside this exact
                    # previously declared exit interval for the entire
                    # translation cell; all transition points are checked.
                    keep&=~((abs(local[:,0]-slots[slot,0])<1e-5)&(abs(local[:,1]-slots[slot,1])<1e-5)
                        &(points[:,2]-b>=slots[slot,2]-5.-1e-5)&(points[:,2]-a<=slots[slot,2]+1e-5))
                ids=np.flatnonzero(keep)
                for span in np.split(ids,np.flatnonzero(np.diff(ids)>1)+1):
                    if not len(span):continue
                    q=local[span]
                    if len(q)==1:q=np.vstack([q,q])
                    hit=check_one(q,error+half,lo,hi,m,tree)
                    if hit:return {'kind':'wire','slot':slot,'object':name,'piece':kind,'temporal_mm':half,**hit}
    return None


def bd_interval(a,b,depth=0):
    global bd_tests
    bd_tests+=1;hit=bd_test(a,b)
    if hit and depth<14:
        mid=(a+b)/2.;bd_interval(a,mid,depth+1);bd_interval(mid,b,depth+1)
    elif hit:
        bd_unproved.append({'interval_mm':[a,b],'failure':hit})
        print('LIFT2_BOARD_UNPROVED',a,b,hit,flush=True)
    else:
        bd_passed.append({'interval_mm':[a,b],'status':'PASS'})
        print('LIFT2_BOARD_INTERVAL',a,b,'PASS',round(time.time()-bd_started,1),flush=True)
    if len(bd_unproved)>20:raise RuntimeError('More than20 unresolved intervals; preserve failure before further planning')


try:
    assert all(r['status']=='PASS' for r in bd_exact_plug),bd_exact_plug
    bd_interval(2.,8.)
    bd_error=None
except Exception as exc:bd_error=repr(exc)
allrows=sorted(bd_passed+bd_unproved,key=lambda r:r['interval_mm'][0])
coverage=bool(allrows and allrows[0]['interval_mm'][0]==2. and allrows[-1]['interval_mm'][1]==8.
    and all(x['interval_mm'][1]==y['interval_mm'][0] for x,y in zip(allrows,allrows[1:])))
report={'status':'PASS' if coverage and not bd_unproved and not bd_error else 'BLOCKED',
    'scope':'Nominal continuous CAM board8->2mm versus stage fixtures, fixed plug and prescribed four-wire shape',
    'source_main_sha256':source_hash,'script_sha256':sha(BD_SCRIPT),'helper_sha256':sha(BD_HELPER),
    'source_finite_screen_sha256':sha(BD_OUT/'screen.json'),'board_translation_range_mm':[2.,8.],
    'plug_lift_mm':2.,'wire_shape':bd_meta,'complete_coverage':coverage,
    'passed_intervals':bd_passed,'unproved_intervals':bd_unproved,'interval_tests':bd_tests,'error':bd_error,
    'exact_convex_plug_sweep':bd_exact_plug,'plug_sweep_bounds_mm':list(bd_plug_sweep.bounding_box()),
    'supersedes_distance_only_diagnostic_sha256':sha(BD_OUT/'board_descent_distance_bound.json'),
    'rigid_gap_lower_bound_mm':bd_min_gap if math.isfinite(bd_min_gap) else None,
    'wire_surface_margin_mm':.3,'bound_rule':'Exact convex plug translation sweep against board; other rigid gaps minus half cell travel, unit speed board translation; wire spatial error included',
    'mating_pair_excluded':['CAM_UART_4P','CAM_catalogue_housing'],
    'own_UART_wire_exit_exception':'Only existing5mm exit interval, with both interval endpoints contained; no other board part exempt',
    'uninstalled_ties':['CAM_connector_tie_head','CAM_connector_tie_band'],
    'actual_connector_compatibility':'BLOCKED_PENDING_IDENTIFICATION',
    'plug_to_wire_exit_geometry':'NOT_TESTED','terminal_insertion':'NOT_TESTED','hands_tools':'NOT_TESTED',
    'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False,'elapsed_s':time.time()-bd_started}
(BD_OUT/'board_descent_continuous.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('LIFT2_BOARD_CONTINUOUS_DONE',report['status'],len(bd_passed),len(bd_unproved),bd_error,flush=True)

"""Check continuous rigid sweeps and the newly required CAM screw access."""
from pathlib import Path
BV_SCRIPT=Path(__file__).resolve();BV_ROOT=BV_SCRIPT.parent
BV_HELPER=BV_ROOT/'check_CAM_board_last.py';__file__=str(BV_HELPER)
exec(compile(BV_HELPER.read_text().split("\nif __name__=='__main__':",1)[0],str(BV_HELPER),'exec'),globals())
__file__=str(BV_SCRIPT)
from interface_completion import axial
bv_screen=json.loads((BL_OUT/'screen.json').read_text());assert bv_screen['status']=='PASS'
assert len(bv_screen['rows'])==16
bv_started=time.time()

def bv_hits(shape,targets):
    hits=[]
    for n,m in targets.items():
        if not overlap_boxes(shape,m,.001):continue
        v=max(0.,float((shape^m).volume()))
        if v>1e-5:hits.append({'object':n,'intersection_mm3':v})
    return hits

sweeps=[]
for n,m in (bl_board|{'CAM_catalogue_housing':bl_plug}).items():
    # A convex hull of the start and end encloses the entire translational
    # sweep. A PASS proves no collision for this leg; a FAIL can be conservative.
    source_parts={ref:q for ref,q in components.items() if ref!='UART_4P'} if n=='CAM_without_own_UART' else {n:m}
    hits=[]
    for ref,q in source_parts.items():
        swept=manifold.Manifold.batch_hull([q,q.translate([0.,0.,6.])])
        hits.extend({'source_component':ref,**hit} for hit in bv_hits(swept,bl_fixture))
    sweeps.append({'stage':'mated_board_lowering','object':n,'travel_mm':6.,'method':'union of convex outer hulls of translated original source components',
        'source_components':len(source_parts),'status':'PASS' if not hits else 'BLOCKED','hits':hits})
plug_sweep=manifold.Manifold.batch_hull([bl_plug,bl_plug.translate([0.,0.,6.])])
targets=bl_fixture|{n:m.translate([0.,0.,6.]) for n,m in bl_board.items() if n!='CAM_UART_4P'}
hits=bv_hits(plug_sweep,targets)
sweeps.append({'stage':'mate_with_board_raised','object':'CAM_catalogue_housing','travel_mm':6.,'method':'convex outer hull of translated source housing','status':'PASS' if not hits else 'BLOCKED','hits':hits})

tools=[];tools_fixed=bl_fixture|bl_board|{'CAM_catalogue_housing':bl_plug}|bl_deferred
core,tails,meta=bl_curves(0.,0.)
for r in P['interface_completion']['inserts']:
    if not r.get('screw','').startswith('CAM_Mount_Screw_'):continue
    n=r['screw'];a=np.array(r['outward']);face=np.array(r['screw_head_bearing_mm'])+a*r['head_height_mm']
    fixture={k:m for k,m in tools_fixed.items() if k!=n};trials=[]
    for sku,length,total in [('Wiha 42415',60.,160.),('Wiha 42416',80.,180.)]:
        parts=[('blade',axial(2.,length,face+a*(.03+length/2.),a)),('handle_allocation',axial(9.,total-length,face+a*(.03+length+(total-length)/2.),a))]
        collisions=[];wire_hits=[]
        for kind,m in parts:
            if n=='CAM_Mount_Screw_0' and sku=='Wiha 42415':cache(BL_OUT/('straight_driver_'+kind+'.npz'),m)
            collisions.extend({'tool_part':kind,**h} for h in bv_hits(m,fixture))
            target=pw_obstacle(kind,'tool',m)
            for i in range(4):
                for label,p,e in [('core',core+[xx[i]-xx[0],0,0],meta['core_error_mm']),('tail',tails[i],meta['tail_error_mm'])]:
                    hit=check_one(p,e,target[3],target[4],m,target[5])
                    if hit:wire_hits.append({'tool_part':kind,'wire_slot':i,'segment':label,**hit})
        trials.append({'tool':sku,'blade_diameter_mm':4.,'blade_length_mm':length,'handle_allocation_diameter_mm':18.,'handle_allocation_length_mm':total-length,
            'status':'PASS' if not collisions and not wire_hits else 'BLOCKED','solid_hits':collisions,'wire_hits':wire_hits})
    tools.append({'screw':n,'status':'PASS' if any(r['status']=='PASS' for r in trials) else 'BLOCKED','trials':trials})
    print('BOARD_LAST_TOOL',n,tools[-1]['status'],[(t['tool'],[(h['tool_part'],h['object']) for h in t['solid_hits']],len(t['wire_hits'])) for t in trials],flush=True)

result={'status':'PASS' if all(r['status']=='PASS' for r in sweeps+tools) else 'BLOCKED',
    'scope':'Continuous outer-hull rigid sweeps and actual final-stage catalogue straight-driver allocations; wires still only at finite prescribed installation poses',
    'source_main_sha256':source_hash,'script_sha256':sha(BV_SCRIPT),'helper_sha256':sha(BV_HELPER),
    'screen_sha256':sha(BL_OUT/'screen.json'),'source_catalogue_driver_sha256':sha(PROJECT/'mechanical/studies/interface_completion/catalogue_driver_checks.json'),
    'rigid_sweeps':sweeps,'driver_access':tools,'deferred_CAM_screws':list(bl_deferred),
    'other_tool_directions_or_tool_types':'NOT_TESTED','continuous_wire_deformation':'NOT_TESTED',
    'initial_terminal_threading_and_curve_formation':'NOT_TESTED','tie_threading_tightening':'NOT_TESTED',
    'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False,'elapsed_s':time.time()-bv_started}
(BL_OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('BOARD_LAST_VERIFY',result['status'],[(r['object'],r['status']) for r in sweeps],flush=True)

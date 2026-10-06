"""Tool and free-tail work volumes at the connector-side CAM anchor.

Only detached-cradle work is assessed. Tool boxes are conservative working
allocations; no claim of actual cutter, hand, latch or flexible assembly fit.
"""
from pathlib import Path
WA_SCRIPT=Path(__file__).resolve();WA_ROOT=WA_SCRIPT.parent
WA_HELPER=WA_ROOT/'screen_CAM_pitch_anchor_warp.py';__file__=str(WA_HELPER)
exec(compile(WA_HELPER.read_text().split('\npw_rows=[];',1)[0],str(WA_HELPER),'exec'),globals())
__file__=str(WA_SCRIPT)
WA_OUT=WA_ROOT/'cam_connector_install';WA_OUT.mkdir(exist_ok=True)
WA_ANCHOR=WA_ROOT/'cam_pitch_anchor/connector_anchor'
wa_cradle=pw_readsolid(WA_ANCHOR/'Pitch_Cradle.npz')
wa_band=pw_readsolid(WA_ANCHOR/'z212.0_band.npz')
wa_head=pw_readsolid(WA_ANCHOR/'z212.0_head.npz')
wa_assembly=json.loads((WA_ANCHOR/'assembly.json').read_text());assert wa_assembly['status']=='PASS'
wa_fixture={'Pitch_Cradle':wa_cradle,'CAM_Mainboard':ss['CAM_Mainboard'].m,'CAM_catalogue_housing':housing}
wa_fixture.update({n:s.m for n,s in ss.items() if n.startswith(('CAM_Mount_Insert_','CAM_Mount_Screw_'))})
wa_wire_straights={f'local_wire_{i}':manifold.Manifold.cylinder(14.6,(OD/2+.001)/math.cos(math.pi/64),circular_segments=64).translate([float(x),float(slots[0,1]),200.]) for i,x in enumerate(slots[:,0])}
wa_xsum=float(slots[:,0].mean()+xx.mean())
wa_transform=np.array([[-1.,0.,0.,wa_xsum],[0.,1.,0.,float(slots[0,1]+1.5)],[0.,0.,1.,-20.]])
# The same free-tail work allocation used at the other CAM anchor, reflected
# and translated with the actual saved tie. No new inferred latch channel.
wa_tail=pw_readsolid(WA_ROOT/'cam_tie_install/tail_corridor.npz').transform(wa_transform)
wa_base_tool=pw_readsolid(WA_ROOT/'cam_tie_install/cutter_allocation.npz').transform(wa_transform)
wa_base_sweep=pw_readsolid(WA_ROOT/'cam_tie_install/cutter_swept.npz').transform(wa_transform)
wa_yfront=float(wa_head.bounding_box()[4])+.25
wa_pivot=np.array([wa_xsum-(float(xx.max()+1.2)+.5+2.6),wa_yfront,212.-2.7/2])

def wa_hits(solid,targets):
    result=[];nearest={'gap_mm':5.,'object':None}
    for name,m in targets.items():
        if not overlap_boxes(solid,m,5.):continue
        volume=max(0.,float((solid^m).volume()))
        if volume>1e-5:result.append({'object':name,'intersection_mm3':volume})
        gap=float(solid.min_gap(m,5.))
        if gap<nearest['gap_mm']:nearest={'gap_mm':gap,'object':name}
    return {'status':'BLOCKED' if result else 'PASS','hits':result,'minimum_gap_below_5mm':nearest}

def wa_loop_hits(solid):
    mesh=solid.to_mesh64();bb=np.array(solid.bounding_box())
    tree=BVHTree.FromPolygons(mesh.vert_properties[:,:3],mesh.tri_verts.tolist(),all_triangles=True)
    hits=[]
    for slot in range(4):
        sample,error=loop_samples[slot,0]
        # check_one enforces the source study's noncontact clearance, including
        # its curve/sample bounds; it is stronger than a single-point overlap.
        hit=check_one(sample[0],error,bb[:3],bb[3:],solid,tree)
        if hit:hits.append({'slot':slot,**hit})
    return {'status':'BLOCKED' if hits else 'PASS','hits':hits,'scope':'Four prescribed pitch tails/loops at mechanical zero, not complete harness'}

wa_tail_result=wa_hits(wa_tail,wa_fixture|wa_wire_straights)
cache(WA_OUT/'tail_corridor.npz',wa_tail)
wa_rows=[]
for angle in [0.,180.,90.,-90.,135.,-135.]:
    def orient(m):return m.translate((-wa_pivot).tolist()).rotate([0.,angle,0.]).translate(wa_pivot.tolist())
    tool=orient(wa_base_tool);sweep=orient(wa_base_sweep)
    row={'angle_about_tail_axis_deg':angle,'bench':wa_hits(sweep,wa_fixture|wa_wire_straights|{'tie_head':wa_head,'tie_band':wa_band}),
         'fixture_only':wa_hits(sweep,wa_fixture),'temporary_wires_only':wa_hits(sweep,wa_wire_straights),
         'tie_only':wa_hits(sweep,{'tie_head':wa_head,'tie_band':wa_band}),
         'final_prescribed_loops':wa_loop_hits(sweep),
         'tool_bounds_mm':list(tool.bounding_box()),'continuous_approach_bounds_mm':list(sweep.bounding_box())}
    row['status']=row['bench']['status'];wa_rows.append(row)
    cache(WA_OUT/f'tool_{angle}.npz',tool);cache(WA_OUT/f'sweep_{angle}.npz',sweep)
    print('CONNECTOR_WORK',angle,row,flush=True)
# Establish which disassembly level the successful bench tool really needs.
# Keep all other source solids and mating allocations; only the explicitly
# removed outer head shells are omitted from the open-head comparison.
wa_selected_sweep=wa_base_sweep.translate((-wa_pivot).tolist()).rotate([0.,180.,0.]).translate(wa_pivot.tolist())
wa_open_head={n:(wa_cradle if n=='Pitch_Cradle' else m) for n,g,m,*_ in ob if n not in ['Head_Front','Head_Rear']}
wa_pitch_module={n:(wa_cradle if n=='Pitch_Cradle' else m) for n,g,m,*_ in ob if g=='pitch' and n not in ['Head_Front','Head_Rear']}
wa_service={'open_head_on_robot':wa_hits(wa_selected_sweep,wa_open_head),
            'detached_pitch_module_no_shells':wa_hits(wa_selected_sweep,wa_pitch_module)}
for name,row in wa_service.items():print('CONNECTOR_SERVICE',name,row,flush=True)
wa_report={'status':'PASS' if wa_tail_result['status']=='PASS' and any(r['status']=='PASS' for r in wa_rows) else 'BLOCKED',
    'scope':'Detached CAM/cradle free-tail and bounded cutter working volumes; no human hand or flexible cable claim',
    'script_sha256':sha(WA_SCRIPT),'helper_sha256':sha(WA_HELPER),'source_main_sha256':source_hash,
    'inputs':{str(p.relative_to(WA_ROOT)):sha(p) for p in [WA_ANCHOR/'Pitch_Cradle.npz',WA_ANCHOR/'z212.0_head.npz',WA_ANCHOR/'z212.0_band.npz',WA_ANCHOR/'assembly.json',WA_ROOT/'cam_tie_install/cutter_allocation.npz',WA_ROOT/'cam_tie_install/cutter_swept.npz',WA_ROOT/'cam_tie_install/tail_corridor.npz']},
    'fixture_ids':list(wa_fixture),'temporary_wires_z_mm':[200.,214.6],
    'tool_reference':'KNIPEX 79 22 125; enlarged working boxes per prior sourced dimensions, no purchase selection',
    'tail_work_volume':wa_tail_result,'rows':wa_rows,'pivot_mm':wa_pivot.tolist(),
    'accepted_angles_deg':[r['angle_about_tail_axis_deg'] for r in wa_rows if r['status']=='PASS'],
    'preferred_angle_deg':180.,'preference_basis':'Downward tool axis avoids the near-zero CAM clearance of the diagonal trial; cut before forming the final pitch tails',
    'service_fixture_levels':wa_service,'service_fixture_ids':{'open_head_on_robot':list(wa_open_head),'detached_pitch_module_no_shells':list(wa_pitch_module)},
    'service_scope':'Tool volume only, excluding flexible wire reshaping; detached-module withdrawal and connected-harness reach not established',
    'tool_opening_force_and_hand_access':'NOT_TESTED','real_tie_threading_tension_and_cutting':'NOT_TESTED',
    'complete_harness_installation':'NOT_TESTED','main_applied':False,'manufacturing_release':False,'whole_harness':'BLOCKED'}
(WA_OUT/'work_access.json').write_text(json.dumps(wa_report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('CONNECTOR_WORK_DONE',wa_report['status'],wa_report['accepted_angles_deg'],flush=True)

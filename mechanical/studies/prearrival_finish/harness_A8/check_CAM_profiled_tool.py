"""Compare the old stepped cutter with an evidence-labelled neck profile.

An exploratory working envelope, NOT vendor CAD. Width/depth transition
stations are assumed from official photos, with manufacturer head/overall
dimensions as anchors. The two profiles are checked on exactly the same
already-seated candidate and prescribed wires; no robot/source edits.
"""
from pathlib import Path
PT_SCRIPT=Path(__file__).resolve();PT_ROOT=PT_SCRIPT.parent
PT_HELPER=PT_ROOT/'check_CAM_sequence_tools.py';__file__=str(PT_HELPER)
exec(compile(PT_HELPER.read_text().split('\nst_rows=[];',1)[0],str(PT_HELPER),'exec'),globals())
__file__=str(PT_SCRIPT)
PT_OUT=PT_ROOT/'cam_profiled_tool';PT_OUT.mkdir(exist_ok=True)

# Coordinates: Z from allocated blade tip toward handles, Y from flush face
# toward back, X across jaws. The unchanged old head already allows +2 mm
# over catalogue A and +1 mm over D. These are working allowances, not
# documented jaw-opening kinematics or assured manufacturing tolerances.
PT_STATIONS=[(0.,13.,7.5),(20.,13.,7.5),(28.,20.,9.),
             (45.,38.,20.),(72.,62.,20.),(125.,62.,20.)]

def pt_sections(stations,travel=0.):
    parts=[]
    for (a,w0,d0),(b,w1,d1) in zip(stations,stations[1:]):
        points=[]
        for z,w,d in [(a,w0,d0),(b,w1,d1)]:
            for dz in ([0.,travel] if travel else [0.]):
                points.extend([[x,y,z+dz] for x in [-w/2,w/2] for y in [0.,d]])
        parts.append(manifold.Manifold.hull_points(np.array(points)))
    m=manifold.Manifold.batch_boolean(parts,manifold.OpType.Add)
    assert m.status()==manifold.Error.NoError and len(m.decompose())==1
    return m.translate(st_pivot.tolist())

pt_tool=pt_sections(PT_STATIONS);pt_sweep=pt_sections(PT_STATIONS,60.)
cache(PT_OUT/'tool_profile.npz',pt_tool);cache(PT_OUT/'sweep_profile.npz',pt_sweep)
pt_profiles={'old_boxes':(st_tool,st_sweep),'photo_profile':(pt_tool,pt_sweep)}
pt_rows=[];pt_start=time.time()
pt_targets=wi_fixed|wi_moving
pt_tail_check=st_hits(st_tail,pt_targets)
for pname,(base,sweep) in pt_profiles.items():
    for angle in [0.,15.,30.,45.,60.,75.,90.,-15.,-30.,-45.,-60.,-75.,-90.,180.]:
        def pt_orient(m):return m.translate((-st_pivot).tolist()).rotate([0.,angle,0.]).translate(st_pivot.tolist())
        tool=pt_orient(base);swept=pt_orient(sweep)
        fixture=st_hits(swept,pt_targets)
        wires=st_wire_hits(swept,0.) if fixture['status']=='PASS' else {'status':'NOT_TESTED'}
        tie=st_hits(swept,{'head':st_head,'band':pw_readsolid(PT_ROOT/'cam_tie_install/oriented_band.npz')})
        status='PASS' if all(x['status']=='PASS' for x in [fixture,wires,tie,pt_tail_check]) else 'BLOCKED'
        row={'profile':pname,'angle_deg':angle,'status':status,'fixture':fixture,'wires':wires,'tie':tie}
        pt_rows.append(row)
        cache(PT_OUT/f'{pname}_{angle:g}_tool.npz',tool)
        cache(PT_OUT/f'{pname}_{angle:g}_sweep.npz',swept)
        print('PROFILE_TOOL',pname,angle,status,[(r['object'],round(r['intersection_mm3'],4)) for r in fixture['hits']],wires,flush=True)
pt_result={
    'status':'PASS' if any(r['status']=='PASS' for r in pt_rows) else 'BLOCKED',
    'scope':'Seated four-wire CAM candidate; 60 mm axial cutter retraction at 14 roll angles per profile; head shells/optics/transmission not yet fitted',
    'profile_evidence':'ASSUMED envelope informed by official KNIPEX 79 22 125 photographs; not complete vendor CAD or physical measurement',
    'nominal_documented_mm':{'overall':[125.,60.,19.],'A':11.,'B':10.,'D':6.5},
    'profile_stations_z_width_depth_mm':PT_STATIONS,
    'station_evidence':'All station Z and transition width/depth values ASSUMED; 20 and 28 mm from rounded photo proportions, 45 and 72 mm enlarged intermediate allocation; overall width/depth enlarged by 2/1 mm',
    'cut_pivot_mm':st_pivot.tolist(),'blade_seating_datum':'same as earlier study; origin at lower band edge with 0.25 mm head-face clearance; exact blade purchase and latch channel unverified',
    'tail_corridor':pt_tail_check,'rows':pt_rows,'fixture_ids':list(pt_targets),
    'not_yet_fitted':wi_excluded,'main_applied':False,'whole_harness':'BLOCKED',
    'profile_manufacturing_fit':'NOT_TESTED','jaw_closing_kinematics_hands_forces':'NOT_TESTED',
    'other_seven_head_wires_FPC':'NOT_TESTED','manufacturing_release':False,
    'source_main_sha256':source_hash,'script_sha256':sha(PT_SCRIPT),'helper_sha256':sha(PT_HELPER),
    'elapsed_s':time.time()-pt_start}
(PT_OUT/'screen.json').write_text(json.dumps(pt_result,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('PROFILE_TOOL_DONE',pt_result['status'],[(r['profile'],r['angle_deg']) for r in pt_rows if r['status']=='PASS'],flush=True)

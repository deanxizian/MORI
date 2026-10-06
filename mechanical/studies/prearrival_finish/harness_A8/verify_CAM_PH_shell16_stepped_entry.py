"""Independently replay the selected cuboid translation sweeps on closed solids."""
from pathlib import Path
VERIFY_STEP_SCRIPT=Path(__file__).resolve()
VERIFY_STEP_HELPER=VERIFY_STEP_SCRIPT.parent/'screen_CAM_PH_shell16_stepped_entry.py'
__file__=str(VERIFY_STEP_HELPER)
exec(compile(VERIFY_STEP_HELPER.read_text().split('\ntrials=[];',1)[0],str(VERIFY_STEP_HELPER),'exec'),globals())
__file__=str(VERIFY_STEP_SCRIPT)
OUT=STOCK_OUT/'PH_shell16_stepped_entry'
src=json.loads((OUT/'screen.json').read_text())
assert src['status']=='PASS' and src['script_sha256']==sha(VERIFY_STEP_HELPER)
for p,h in src['source_files'].items():assert sha(PROJECT/p)==h,p
states=[tuple(p) for p in src['selected']['path_states']]
assert states[0]==(0.,0.,8.,0) and all(p[3]==0 for p in states)
rows=[];max_overlap=0.
for index,(a,b) in enumerate(zip([(0.,0.,0.,0)]+states[:-1],states)):
    sweep=manifold.Manifold.batch_hull([shapes[0].translate(list(a[:3])),shapes[0].translate(list(b[:3]))])
    candidates=near(sweep);tests=[]
    for name,obstacle in candidates:
        overlap=sweep^obstacle
        if index==0 and name=='MCU_Carrier':overlap-=native
        volume=max(0.,float(overlap.volume()));max_overlap=max(max_overlap,volume)
        tests.append(dict(name=name,intersection_mm3=volume))
        assert volume<=1e-5,(index,name,volume)
    rows.append(dict(index=index,start_translation_mm=list(a[:3]),end_translation_mm=list(b[:3]),
                     status='PASS',near_object_tests=tests,initial_mating_exception=index==0))
    print('PH_STEPPED_EXACT',index,len(tests),max_overlap,flush=True)
planes={'YZ':np.array([[0,1,0,0],[0,0,1,0],[1,0,0,0]],dtype=float),
        'XZ':np.array([[1,0,0,0],[0,0,1,0],[0,-1,0,0]],dtype=float)}
parts=['Body_Upper','Yaw_Base','Load_Frame','MCU_Carrier','MCU_Motion','E_Straight_Header',
       'fixed_wire_H02_1','fixed_wire_H02_2','fixed_wire_H03_1','fixed_wire_H03_2']
projections={plane:{n:[np.asarray(poly).tolist() for poly in targets[n].transform(t).project().to_polygons()]
                    for n in parts} for plane,t in planes.items()}
source_geometry={n:dict(bounds_mm=list(targets[n].bounding_box()),volume_mm3=float(targets[n].volume())) for n in sorted(targets)}
last_box=shapes[0].translate(list(states[-1][:3]));upper_top=max(targets[n].bounding_box()[5] for n in targets if target_group[n]=='upper')
exit_gap=last_box.bounding_box()[2]-upper_top
assert exit_gap>0,exit_gap
report=dict(status='PASS',scope='Closed-solid sweep recheck of bare PH candidate, not connected wire assembly',
    script_sha256=sha(VERIFY_STEP_SCRIPT),helper_sha256=sha(VERIFY_STEP_HELPER),source_screen_sha256=sha(OUT/'screen.json'),
    protected_sources=protected,source_files=src['source_files'],rows=rows,continuous_translation_segments=len(rows),
    max_padded_overlap_after_initial_exception_mm3=max_overlap,required_study_margin_mm=.3,
    initial_mating='NOT_TESTED',initial_exception_scope=src['native_overlap_exception'],
    exterior_upper_clearance_mm=exit_gap,source_target_members=sorted(targets),source_target_geometry=source_geometry,
    deferred_wire_ids=deferred_wires,deferred_plugs=deferred_plugs,
    later_deferred_installation='NOT_TESTED',attached_CAM_wires='NOT_TESTED',hands_and_tools='NOT_TESTED',
    complete_attached_assembly='BLOCKED',main_applied=False,manufacturing_release=False)
(OUT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
projection=dict(status='PASS',scope='Exact source solid projections and selected PH center path',
    script_sha256=sha(VERIFY_STEP_SCRIPT),source_screen_sha256=sha(OUT/'screen.json'),
    verification_sha256=sha(OUT/'verification.json'),protected_sources=protected,
    projections=projections,housing_center_mm=center.tolist(),housing_dimensions_mm=size.tolist(),
    withdrawal_translation_mm=[[0.,0.,0.]]+[list(p[:3]) for p in states],main_applied=False)
(OUT/'projections.json').write_text(json.dumps(projection,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('PH_STEPPED_VERIFIED',len(rows),exit_gap,max_overlap,flush=True)

"""Set relative wire heights during lifting, before the constrained rear move.

Changing a wire after lift crossed another fixed rising leg. This instead
varies the lift recipe from the common, exactly identical zero-height state.
All original solids, wire lengths, diameters and clearances remain unchanged.
"""
from pathlib import Path
EARLY16_SCRIPT=Path(__file__).resolve()
EARLY16_HELPER=EARLY16_SCRIPT.parent/'merge_shell16_back20_wires.py'
early_source=EARLY16_HELPER.read_text();early_marker='\nfor k in range(21):'
__file__=str(EARLY16_HELPER)
exec(compile(early_source.split(early_marker,1)[0],str(EARLY16_HELPER),'exec'),globals())
__file__=str(EARLY16_SCRIPT)
import copy
OUT=ORDER_OUT/'shell16_early_wire_planes';OUT.mkdir(exist_ok=True)
original_holds=copy.deepcopy(holds)
original_set_pose=set_pose
early_loop='for k in range(21):'+early_source.split(early_marker,1)[1].split('\nnp.savez_compressed',1)[0]
pool={1:[],2:[]};pool_curves={};individual_rows=[];packing_rows=[];lift_choices=[]
fractions=[.25,.4,.5,.6,.75,1.]


def lift_pose(z):
    global bt,matrices
    bt=trans(z=float(z));st=shellpose(16.,0.,14.)
    matrices=dict(core=I,upper=np.linalg.inv(st),bridge=np.linalg.inv(bt))


for pin in [1,2]:
    for fraction in fractions:
        p=dict(starts[pin],elevation_fraction=fraction)
        poses=[];failure=None;previous=None
        for i,z in enumerate(np.arange(0.,18.01,.5)):
            lift_pose(z);c,failure=one(pin,p)
            if failure:break
            if i==0:assert np.array_equal(c['points'],start_curves[f'pin{pin}_pose0'])
            angles=np.asarray(c['planar_angles_rad'])
            if previous is not None and np.max(np.abs(angles-previous))>math.pi:
                failure=dict(kind='arc_branch_jump',pin=pin);break
            previous=angles;poses.append(c)
        ident=f'pin{pin}_f{fraction:g}'
        row=dict(id=ident,pin=pin,parameters=p,status='BLOCKED' if failure else 'PASS',
                 passing_positions=len(poses),failure=failure)
        individual_rows.append(row)
        if not failure:pool[pin].append(row);pool_curves[ident]=poses
        print('EARLY_PLANES_INDIVIDUAL',ident,row['status'],row['passing_positions'],failure,flush=True)

for choice in itertools.product(pool[1],pool[2]):
    pairs_rows=[];failure=None
    for i,z in enumerate(np.arange(0.,18.01,.5)):
        lift_pose(z)
        cc={1:pool_curves[choice[0]['id']][i],2:pool_curves[choice[1]['id']][i],
            3:curve_for_lift(3,i),4:curve_for_lift(4,i)}
        pairs,failure=mutual_check(cc)
        if not failure:failure=terminal_checks(cc,bt)
        if failure:break
        pairs_rows.append(dict(index=i,bridge_z_mm=float(z),pairs=pairs))
    row=dict(ids=[c['id'] for c in choice],status='BLOCKED' if failure else 'PASS',
             passing_positions=len(pairs_rows),failure=failure,pairs=pairs_rows)
    packing_rows.append(row)
    if not failure:
        lift_choices.append((choice,row))
    print('EARLY_PLANES_PACKING',row['ids'],row['status'],row['passing_positions'],failure,flush=True)

trials=[];selected_early=None;all_arrays={}
# Lower CAM2 before the high fixed leg exists; choose clear plane separation.
lift_choices.sort(key=lambda c:(c[0][1]['parameters']['elevation_fraction'],
                               abs(c[0][0]['parameters']['elevation_fraction']-.5)))
for choice,lift_row in lift_choices:
    holds=copy.deepcopy(original_holds)
    for h in holds.values():h[1]=[];h[2]=[]
    holds[0][4]=[dict(starts[4],entry_azimuth_deg=-7.5,planar_radius_mm=8.)]
    current={pin:dict(p) for pin,p in starts.items()}
    current[1]=dict(choice[0]['parameters']);current[2]=dict(choice[1]['parameters'])
    records=[];diagnostics=[];saved={};failure=None
    f,curves,pairs=evaluate(0.,current);assert not f,f
    for pin in [1,2]:assert np.array_equal(curves[pin]['points'],pool_curves[choice[pin-1]['id']][-1]['points'])
    for pin in [3,4]:assert np.array_equal(curves[pin]['points'],start_curves[f'pin{pin}_pose36'])
    store_record(0.,'modified_lift_end',current,curves,pairs)
    exec(compile(early_loop,str(EARLY16_HELPER),'exec'),globals())
    trial=dict(ids=[c['id'] for c in choice],status='BLOCKED' if failure else 'PASS',
               passing_positions=len(records),furthest_back_mm=-records[-1]['bridge_y_mm'],
               failure=failure,diagnostics=diagnostics)
    trials.append(trial)
    print('EARLY_PLANES_BACK',trial['ids'],trial['status'],trial['furthest_back_mm'],failure,flush=True)
    if not failure:
        selected_early=dict(lift=lift_row,back=trial,records=records,final_parameters=current)
        all_arrays={f'back_{k}':v for k,v in saved.items()}
        for i in range(37):
            for pin in [1,2]:all_arrays[f'lift_pin{pin}_pose{i}']=pool_curves[choice[pin-1]['id']][i]['points']
            for pin in [3,4]:all_arrays[f'lift_pin{pin}_pose{i}']=start_curves[f'pin{pin}_pose{i}']
        break

np.savez_compressed(OUT/'curves.npz',**all_arrays)
report=dict(status='PASS' if selected_early else 'BLOCKED',
    scope='Finite coordinated lift plus shared back20 with constant nominal wire material',
    script_sha256=sha(EARLY16_SCRIPT),helper_sha256=sha(EARLY16_HELPER),
    source_files={**graph['source_files'],str(graph_path.relative_to(PROJECT)):sha(graph_path),
                  str(rigid_all_path.relative_to(PROJECT)):sha(rigid_all_path)},
    protected_sources=protected,individual=individual_rows,packing=packing_rows,
    back_trials=trials,selected=selected_early,curves_sha256=sha(OUT/'curves.npz'),
    full_nominal_lengths_preserved=True,wire_OD_mm=OD,clearance_mm=MARGIN,body_wire_count=14,
    source_initial_boundary_exact=True,continuous_motion='NOT_TESTED',
    vertical_continuation='NOT_TESTED',complete_attached_assembly='BLOCKED',
    main_applied=False,manufacturing_release=False,elapsed_s=time.time()-started)
(OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('EARLY_PLANES_DONE',report['status'],len(lift_choices),len(trials),round(time.time()-started,1),flush=True)

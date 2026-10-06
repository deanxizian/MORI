"""Compare explicit wire-installation orders on the unchanged body geometry.

Deferred H01-H04 harnesses are counted and named, not silently omitted. Their
later installation is a separate obligation. Each CAM wire retains its full
existing nominal length, common PH housing and upright temporary stock.
"""
from pathlib import Path
ORDER_SCRIPT=Path(__file__).resolve();ORDER_HELPER=ORDER_SCRIPT.parent/'screen_CAM_bridge_wire_stock.py'
text=ORDER_HELPER.read_text().split('\nstages=',1)[0]
writer="np.savez_compressed(STOCK_OUT/'full_wires.npz',**{'pin'+str(k):v for k,v in wire.items()})"
assert text.count(writer)==1;text=text.replace(writer,'# Do not overwrite the earlier wire snapshot.')
__file__=str(ORDER_HELPER);exec(compile(text,str(ORDER_HELPER),'exec'),globals());__file__=str(ORDER_SCRIPT)
ORDER_OUT=STOCK_OUT/'install_order';ORDER_OUT.mkdir(exist_ok=True)
all_targets=target_data.copy()
pairings={'H01':['power_J17','motion_J1'],'H02':['motion_J2','power_J13'],
          'H03':['motion_J3','power_J14'],'H04':['motion_J4','imu_J1']}
assert all('Plug_'+n in all_targets for group in pairings.values() for n in group)
stages=[
 ('bridge_lift_shell_held',[(shellpose(15,0,14),trans(z=float(z))) for z in (0,.5,1,3,6,12,18)]),
 ('body_bridge_back',[(shellpose(15,float(y),14),trans(y=float(y),z=18)) for y in (0,-3,-7,-10,-14)]),
 ('body_bridge_bench',[(shellpose(15,-14,float(z)),trans(y=-14,z=float(z+4))) for z in (14,25,40,70,100,140)]),
 ('body_shell_settle',[(shellpose(15*float(u),0,14*float(u)),I) for u in (0,.25,.5,.75,1.)]),
]
started=time.time();trials=[];witnesses={}
for label,deferred in [('H01_after_CAM',{'H01'}),('H01_H04_after_CAM',{'H01','H04'}),('H01_to_H04_after_CAM',set(pairings))]:
    absent_wires={'fixed_wire_'+n for n in fixed if n.split('_')[0] in deferred}
    absent_plugs={'Plug_'+n for group in deferred for n in pairings[group]}
    absent=absent_wires|absent_plugs
    target_data={n:d for n,d in all_targets.items() if n not in absent};cases=[]
    for stage,poses in stages:
        fail=None;checked=0
        for i,(st,bt) in enumerate(poses):
            matrices={'core':bt,'upper':np.linalg.inv(st)@bt,'bridge':I}
            fail=rigid_check(housing,matrices,True)
            if not fail:
                for pin,pts in wire.items():
                    fail=wire_check(pin,pts,matrices) or rigid_check(terminals[pin],matrices)
                    if fail:break
            checked+=1
            if fail:
                fail.update(index=i,shell_transform=st.tolist(),bridge_transform=bt.tolist())
                witnesses[label+'_'+stage+'_housing_transform']=bt
                break
        case=dict(stage=stage,status='BLOCKED' if fail else 'PASS',checked_positions=checked,planned_positions=len(poses),failure=fail)
        cases.append(case);print('CAM_INSTALL_ORDER',label,stage,case['status'],fail,flush=True)
    trials.append(dict(label=label,deferred_harness_groups=sorted(deferred),deferred_wire_ids=sorted(absent_wires),deferred_mating_allocations=sorted(absent_plugs),
        present_fixed_wires=14-len(absent_wires),present_other_mating_allocations=28-len(absent_plugs),
        status='PASS' if all(c['status']=='PASS' for c in cases) else 'BLOCKED',cases=cases,
        later_installation_of_deferred_harnesses='NOT_TESTED'))
target_data=all_targets
report=dict(status='PASS' if any(r['status']=='PASS' for r in trials) else 'BLOCKED',scope='Coarse staged-order diagnostic with four complete nominal CAM lengths; does not qualify a full assembly order',
    script_sha256=sha(ORDER_SCRIPT),helper_sha256=sha(ORDER_HELPER),source_main_sha256=source_hash,protected_sources=protected,
    source_split_report_sha256=sha(membership_path),substituted_unadopted_prints=membership['substituted_unadopted_prints'],
    source_objects=209,present_source_objects=len(core|upper|bridge),original_fixed_wire_count=14,original_mating_allocation_count=29,
    nominal_CAM_lengths_mm=[r['full_nominal_allocation_mm'] for r in lengths],full_wire_arrays_sha256=sha(STOCK_OUT/'full_wires.npz'),
    trials=trials,continuous_motion='NOT_TESTED',CAM_plug_axial_mating='ASSUMED_ORIGINAL_DOMAIN_ONLY',
    later_harness_installation='NOT_TESTED',tools_and_hands='NOT_TESTED',main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,
    no_universal_impossibility_claim=True,elapsed_s=time.time()-started)
(ORDER_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/n)==h for n,h in protected.items())
print('CAM_INSTALL_ORDER_DONE',report['status'],round(time.time()-started,2),flush=True)

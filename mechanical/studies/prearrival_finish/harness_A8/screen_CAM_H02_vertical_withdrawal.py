"""Test removing the unnecessary rearward stage, if actual separation permits.

After the saved 18 mm lift, raise shell and bridge vertically together. The
endpoint derives from complete Z separation of their rigid groups from the
remaining body, not from a shortened arbitrary animation distance.
"""
from pathlib import Path
VERTICAL_SCRIPT=Path(__file__).resolve()
VERTICAL_HELPER=VERTICAL_SCRIPT.parent/'screen_CAM_H02_back_transition.py'
__file__=str(VERTICAL_HELPER)
exec(compile(VERTICAL_HELPER.read_text().split('\nSTEPS=57;',1)[0],str(VERTICAL_HELPER),'exec'),globals())
__file__=str(VERTICAL_SCRIPT)
OUT=ORDER_OUT/'CAM_H02_vertical_withdrawal';OUT.mkdir(exist_ok=True)
fixed_rigid={n:phys[n] for n in core}
fixed_rigid.update({n:r[0] for n,r in target_data.items() if n.startswith('fixed_wire_')})
# Board-side mating allocations are checked as obstacles as before. They are
# not all installed physical parts, so they do not define removal distance.
body_max_z=max(m.bounding_box()[5] for m in fixed_rigid.values())
upper_zero={n:phys[n].transform(shellpose(15.,0.,0.)[:3,:4]) for n in upper}
upper_min_z=min(m.bounding_box()[2] for m in upper_zero.values())
bridge_min_z=min(phys[n].bounding_box()[2] for n in bridge)
separation_mm=1.
needed=max(18.,body_max_z+separation_mm-upper_min_z+4.,body_max_z+separation_mm-bridge_min_z)
endpoint_z=math.ceil(needed*2)/2
assert endpoint_z<=144.,(needed,body_max_z,upper_min_z,bridge_min_z)
z_values=np.arange(18.,endpoint_z+.01,.5)
source_curves={pin:start_curves[f'pin{pin}_pose36'] for pin in range(1,5)}
physical_source={name:dict(solid=m,bounds=np.asarray(m.bounding_box())) for name,m in phys.items()}
rows=[];saved_curves={};previous={};failure=None


def placed(items,T):
    out={}
    for name,m in items.items():
        q=m.transform(T[:3,:4]);out[name]=(q,np.asarray(q.bounding_box()))
    return out


def collision_pairs(a,b):
    for na,(ma,ba) in a.items():
        for nb,(mb,bb) in b.items():
            if np.any(ba[:3]>=bb[3:]) or np.any(bb[:3]>=ba[3:]):continue
            volume=max(0.,float((ma^mb).volume()))
            if volume>1e-5:return dict(kind='rigid_overlap',a=na,b=nb,intersection_mm3=volume)
    return None


fixed=placed(fixed_rigid,I)
for index,z in enumerate(z_values):
    bt=trans(z=float(z));st=shellpose(15.,0.,float(z-4.))
    matrices=dict(core=I,upper=np.linalg.inv(st),bridge=np.linalg.inv(bt))
    upper_placed=placed({n:phys[n] for n in upper},st)
    bridge_placed=placed({n:phys[n] for n in bridge},bt)
    failure=(collision_pairs(upper_placed,fixed) or collision_pairs(bridge_placed,fixed)
             or collision_pairs(upper_placed,bridge_placed))
    curves={};pair_rows=[]
    if failure is None:failure=rigid_check(housing,matrices,True)
    for pin,p in starts.items():
        if failure:break
        curve,failure=variant_curve(pin,p['entry_azimuth_deg'],p['planar_radius_mm'],p['family'],p['elevation_fraction'])
        if failure:break
        if index==0:assert np.array_equal(curve['points'],source_curves[pin])
        curve['candidate_id']=f'pin{pin}_vertical{index}'
        angles=np.asarray(curve['planar_angles_rad'])
        if pin in previous and np.max(np.abs(angles-previous[pin]))>math.pi:
            failure=dict(kind='arc_branch_jump',pin=pin);break
        previous[pin]=angles
        lengths[pin-1]['curve_chord_error_mm']=curve['curve_chord_error_mm']
        failure=wire_check(pin,curve['points'],matrices) or self_check(curve)
        if failure:break
        failure=rigid_check(make_terminal(curve,bt),matrices)
        if failure:break
        curves[pin]=curve
    if failure is None:pair_rows,failure=mutual_check(curves)
    for pin,curve in curves.items():saved_curves[f'pin{pin}_pose{index}']=curve['points']
    rows.append(dict(index=index,bridge_z_mm=float(z),shell_z_mm=float(z-4.),
                     status='BLOCKED' if failure else 'PASS',failure=failure,
                     curves=[{k:v for k,v in c.items() if k!='points'} for c in curves.values()],pairs=pair_rows))
    if failure:break
    if index%30==0:print('CAM_VERTICAL_PROGRESS',index,float(z),round(time.time()-started,2),flush=True)
np.savez_compressed(OUT/'curves.npz',**saved_curves)
report=dict(status='PASS' if not failure and len(rows)==len(z_values) else 'BLOCKED',
            scope='Finite vertical continuation to actual rigid-body separation; hands and full sequence still unverified',
            script_sha256=sha(VERTICAL_SCRIPT),helper_sha256=sha(VERTICAL_HELPER),
            source_files={**joint['source_files'],str(joint_path.relative_to(PROJECT)):sha(joint_path),
                          str(joint_check_path.relative_to(PROJECT)):sha(joint_check_path),
                          str((JOINT/'wire_solids.json').relative_to(PROJECT)):sha(JOINT/'wire_solids.json'),
                          str((JOINT/'curves.npz').relative_to(PROJECT)):sha(JOINT/'curves.npz')},
            protected_sources=protected,source_main_sha256=source_hash,
            source_prints=membership['substituted_unadopted_prints'],
            endpoint_derivation=dict(body_max_z_mm=body_max_z,tilted_upper_zero_min_z_mm=upper_min_z,
                                     bridge_zero_min_z_mm=bridge_min_z,separation_mm=separation_mm,
                                     necessary_bridge_z_mm=needed,rounded_bridge_z_mm=endpoint_z,
                                     source='All 94 body-core parts and 14 fixed body wire solids; moved 22 upper and 6 bridge parts'),
            planned_positions=len(z_values),checked_positions=len(rows),sample_spacing_mm=.5,
            rows=rows,curves_sha256=sha(OUT/'curves.npz'),exact_prior_boundary_match=True,
            full_analytic_wire_length_preserved=True,all_29_mating_allocations_retained=True,
            final_vertical_rigid_separation='PASS' if not failure else 'NOT_TESTED',
            loose_terminal_pair_sweep='NOT_TESTED',continuous_motion='NOT_TESTED',
            full_head_later_assembly='NOT_TESTED',actual_parts_and_hands='NOT_TESTED',
            main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,elapsed_s=time.time()-started)
(OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('CAM_VERTICAL_DONE',report['status'],len(rows),'of',len(z_values),
      report['endpoint_derivation'],failure,round(time.time()-started,2),flush=True)

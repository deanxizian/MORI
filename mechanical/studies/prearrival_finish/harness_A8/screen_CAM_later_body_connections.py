"""Check the obligations created by installing the CAM lead before H01/H02/H04.

Explicitly test later connector access and simple whole-harness translations.
Failure of a rigid wire shape is not failure of a flexible hand assembly.
"""
from pathlib import Path
LATER_SCRIPT=Path(__file__).resolve();LATER_HELPER=LATER_SCRIPT.parent/'screen_CAM_body_install_order.py'
prefix=LATER_HELPER.read_text().split('\nstarted=time.time();trials=',1)[0]
__file__=str(LATER_HELPER);exec(compile(prefix,str(LATER_HELPER),'exec'),globals());__file__=str(LATER_SCRIPT)
LATER_OUT=ORDER_OUT/'later_connections';LATER_OUT.mkdir(exist_ok=True)
deferred={'H01','H02','H04'}
absent_wires={'fixed_wire_'+n for n in fixed if n.split('_')[0] in deferred}
absent_plugs={'Plug_'+n for group in deferred for n in pairings[group]}
base_targets={n:d for n,d in all_targets.items() if n not in absent_wires|absent_plugs}
native_names={'power':'Power_Module','motion':'MCU_Carrier','imu':'Body_IMU'}
from mathutils.kdtree import KDTree
cam_data={}
for pin,pts in wire.items():
    tree=KDTree(len(pts))
    for i,q in enumerate(pts):tree.insert(q,i)
    tree.balance()
    cam_data[pin]=dict(points=pts,tree=tree,max_step=float(np.linalg.norm(np.diff(pts,axis=0),axis=1).max()),
        chord=lengths[pin-1]['curve_chord_error_mm'])

def object_data(m):
    a=m.to_mesh64();v=np.asarray(a.vert_properties[:,:3]);f=np.asarray(a.tri_verts)
    return (m,v.min(0),v.max(0),BVHTree.FromPolygons(v,f.tolist(),all_triangles=True))
def physical_targets(shell_tr):
    d={}
    for n,(m,lo,hi,tree) in base_targets.items():
        d[n]=object_data(m.transform(shell_tr[:3,:])) if target_group[n]=='upper' else (m,lo,hi,tree)
    d['CAM_body_PH']=object_data(housing)
    return d

def check_shapes(moving,t,targets,native_domains):
    for name,m in moving.items():
        shape=m.translate(t.tolist());bb=np.asarray(shape.bounding_box())
        for target,(s,lo,hi,_) in targets.items():
            if np.any(bb[:3]>hi) or np.any(bb[3:]<lo):continue
            hit=shape^s
            if (name,target) in native_domains:hit-=native_domains[name,target]
            volume=max(0.,float(hit.volume()))
            if volume>1e-5:return dict(moving=name,obstacle=target,volume_mm3=volume,kind='solid_overlap')
        tree=object_data(shape)[3]
        for pin,d in cam_data.items():
            allowance=OD/2+.3+d['max_step']/2+d['chord']+1e-4
            ids=np.where(np.all(d['points']>=bb[:3]-allowance,axis=1)&np.all(d['points']<=bb[3:]+allowance,axis=1))[0]
            for i in ids:
                pt=d['points'][i];distance=float(tree.find_nearest(Vector(pt))[3])
                if distance<allowance:return dict(moving=name,obstacle='CAM_wire_'+str(pin),kind='clearance_bound',distance_mm=distance,required_mm=allowance,point_mm=pt.tolist())
    return None

started=time.time();rows=[];axis_rows=[];witness=[]
for shell_state,shell_tr in [('upper_held',shellpose(15,0,14)),('upper_seated',I)]:
    targets=physical_targets(shell_tr)
    for group in sorted(deferred):
        ports=pairings[group];axes={n:np.asarray(port_pins[n]['axis']) for n in ports}
        for n in ports:
            moving={n:plug[n].m};native=native_names[n.split('_')[0]]
            domain={(n,native):plug[n].m^phys[native]}
            failure=None;checked=0
            for d in np.arange(0,20.01,.5):
                t=axes[n]*d;failure=check_shapes(moving,t,targets,domain);checked+=1
                if failure:
                    failure.update(offset_mm=float(d),translation_mm=t.tolist());break
            row=dict(shell_state=shell_state,harness=group,port=n,axis=axes[n].tolist(),status='BLOCKED' if failure else 'PASS',
                checked_positions=checked,planned_positions=41,failure=failure)
            rows.append(row);print('LATER_BODY_PORT',group,n,shell_state,row['status'],checked,failure,flush=True)
        compatible=all(np.linalg.norm(a-next(iter(axes.values())))<1e-6 for a in axes.values())
        axis_rows.append(dict(shell_state=shell_state,harness=group,port_axes={n:a.tolist() for n,a in axes.items()},
            common_axial_translation_possible=compatible))
        if not compatible:continue
        moving={n:plug[n].m for n in ports}
        moving.update({'wire_'+n:r['m'] for n,r in fixed.items() if n.split('_')[0]==group})
        domains={(n,native_names[n.split('_')[0]]):plug[n].m^phys[native_names[n.split('_')[0]]] for n in ports}
        failure=None;checked=0;axis=next(iter(axes.values()))
        for d in np.arange(0,25.01,.5):
            failure=check_shapes(moving,axis*d,targets,domains);checked+=1
            if failure:failure.update(offset_mm=float(d),translation_mm=(axis*d).tolist());break
        row=dict(shell_state=shell_state,harness=group,mode='whole_preformed_wire_and_two_housings',
            moving=sorted(moving),status='BLOCKED' if failure else 'PASS',checked_positions=checked,planned_positions=51,failure=failure)
        witness.append(row);print('LATER_BODY_WHOLE',group,shell_state,row['status'],checked,failure,flush=True)
report=dict(status='PASS' if all(r['status']=='PASS' for r in rows+witness) else 'BLOCKED',
    scope='Later port approach and simple rigid-harness diagnostics after CAM-first bridge placement; flexible feeding remains an explicit separate obligation',
    script_sha256=sha(LATER_SCRIPT),helper_sha256=sha(LATER_HELPER),source_main_sha256=source_hash,protected_sources=protected,
    source_split_report_sha256=sha(membership_path),substituted_unadopted_prints=membership['substituted_unadopted_prints'],
    source_objects=209,present_source_objects=122,deferred_harnesses=sorted(deferred),body_H03_wires_present=True,
    full_CAM_arrays_sha256=sha(STOCK_OUT/'full_wires.npz'),connector_rows=rows,axis_compatibility=axis_rows,rigid_harness_rows=witness,
    native_mating_overlap='Only original final mating overlap of each housing with its own board is preserved; no source obstacle or board face removed',
    other_deferred_harnesses_during_each_probe='H01/H02/H04 except the active test are not yet installed; a later ordering must include them',
    flexible_wire_feed='NOT_TESTED',continuous_motion='NOT_TESTED',tools_and_hands='NOT_TESTED',actual_housing_geometry='ASSUMED',
    main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,no_universal_impossibility_claim=True,elapsed_s=time.time()-started)
(LATER_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/n)==h for n,h in protected.items())
print('LATER_BODY_DONE',report['status'],round(time.time()-started,2),flush=True)

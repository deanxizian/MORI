"""Read-only projections of the two checked CAM feed configurations."""
from pathlib import Path

REVIEW_SCRIPT=Path(__file__).resolve()
REVIEW_HELPER=REVIEW_SCRIPT.parent/'screen_CAM_feed_pose_packing.py'
__file__=str(REVIEW_HELPER)
exec(compile(REVIEW_HELPER.read_text().split('\npools = {}',1)[0],str(REVIEW_HELPER),'exec'),globals())
__file__=str(REVIEW_SCRIPT)
REVIEW=ORDER_OUT/'feed_pose_packing'
inputs={}
views={}
source_set=[('source',I,I,wire)]
for label in ['lift18','rear14_lift18']:
    folder=REVIEW/label
    verified=json.loads((folder/'verification.json').read_text())
    screen=json.loads((folder/'screen.json').read_text())
    assert verified['status']==screen['status']=='PASS'
    assert verified['screen_sha256']==sha(folder/'screen.json')
    assert verified['curves_sha256']==sha(folder/'curves.npz')
    saved=np.load(folder/'curves.npz')
    curves={int(row['candidate_id'].split('_')[0][3:]):saved[row['candidate_id']]
            for row in verified['selected_checks']}
    source_set.append((label,np.asarray(screen['pose']['bridge']),np.asarray(screen['pose']['shell']),curves))
    for name in ['screen.json','verification.json','curves.npz']:
        p=folder/name;inputs[str(p.relative_to(PROJECT))]=sha(p)
planes={'XZ':np.array([[1,0,0,0],[0,0,1,0],[0,-1,0,0]],dtype=float),
        'YZ':np.array([[0,1,0,0],[0,0,1,0],[1,0,0,0]],dtype=float)}
part_names=['Body_Upper','Load_Frame','Yaw_Base','Yaw_Bearing','Power_Module','MCU_Carrier','Battery']
for label,bt,st,curves in source_set:
    projections={}
    for plane,T in planes.items():
        projections[plane]={}
        for name in part_names:
            solid=phys[name]
            if isinstance(solid,tuple):solid=solid[0]
            transform=bt if name in bridge else st if name in upper else I
            solid=solid.transform(transform[:3,:4])
            projections[plane][name]=[np.asarray(p).tolist() for p in solid.transform(T).project().to_polygons()]
    views[label]=dict(bridge=bt.tolist(),shell=st.tolist(),projections=projections,
                      curves={str(pin):points.tolist() for pin,points in curves.items()})
body_projections={}
for plane,T in planes.items():
    body_projections[plane]={name:[np.asarray(p).tolist() for p in row[0].transform(T).project().to_polygons()]
                             for name,row in target_data.items() if name.startswith('fixed_wire_')}
    assert len(body_projections[plane])==14
for p in [fixed_path,h02_path,h02_check_path,STOCK_OUT/'full_wires.npz',membership_path,REVIEW_HELPER]:
    inputs[str(p.relative_to(PROJECT))]=sha(p)
record=dict(status='PASS',scope='Saved single-pose candidate projections, not an installation sequence',
            script_sha256=sha(REVIEW_SCRIPT),source_files=inputs,protected_sources=protected,
            views=views,body_projections=body_projections,
            source_prints=membership['substituted_unadopted_prints'],
            main_applied=False,whole_harness='BLOCKED',manufacturing_release=False)
(REVIEW/'projections.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('CAM_FEED_POSE_PROJECTIONS',len(views),flush=True)

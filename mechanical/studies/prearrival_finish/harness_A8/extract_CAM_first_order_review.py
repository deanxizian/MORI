"""Export source-derived projections for the explicit CAM-first assembly order."""
from pathlib import Path
EXTRACT_SCRIPT=Path(__file__).resolve();EXTRACT_HELPER=EXTRACT_SCRIPT.parent/'plan_CAM_later_ports_grid.py'
prefix=EXTRACT_HELPER.read_text().split('\nrows=[]\noverall_started=',1)[0]
__file__=str(EXTRACT_HELPER);exec(compile(prefix,str(EXTRACT_HELPER),'exec'),globals());__file__=str(EXTRACT_SCRIPT)
REVIEW=ORDER_OUT/'review';REVIEW.mkdir(exist_ok=True)
path_file=LATER_OUT/'grid_margin_approach/screen.json'
paths=json.loads(path_file.read_text())
assert paths['status']=='PASS'
matrices={'YZ':np.array([[0,1,0,0],[0,0,1,0],[1,0,0,0]],dtype=float),
          'XZ':np.array([[1,0,0,0],[0,0,1,0],[0,-1,0,0]],dtype=float)}
selected=['Body_Upper','Load_Frame','Yaw_Base','Power_Module','MCU_Carrier','Body_IMU','Battery']
projections={}
for plane,T in matrices.items():
    projections[plane]={}
    for name in selected:
        m=base[name][0]
        projections[plane][name]=[np.asarray(p).tolist() for p in m.transform(T).project().to_polygons()]
centers={}
for row in paths['rows']:
    port=row['port'];bounds=np.asarray(plug[port].m.bounding_box());center=(bounds[:3]+bounds[3:])/2
    centers[port]=dict(initial_center_mm=center.tolist(),box_size_mm=(bounds[3:]-bounds[:3]).tolist(),
        points_mm=(center+np.asarray(row['path_translations_mm'])).tolist())
record=dict(status='PASS',scope='Actual transformed source silhouettes and saved certified connector center paths; projection is not collision evidence',
    script_sha256=sha(EXTRACT_SCRIPT),helper_sha256=sha(EXTRACT_HELPER),path_file=str(path_file.relative_to(PROJECT)),paths_sha256=sha(path_file),
    protected_sources=protected,upper_shell=dict(angle_deg=15,up_mm=14,back_mm=0),
    projections=projections,ports=centers,
    CAM_wire_centerlines_mm={str(k):p.tolist() for k,p in wire.items()},
    deferred_wire_groups=sorted(deferred),retained_H03_wire_count=2,
    main_applied=False,whole_harness='BLOCKED',manufacturing_release=False)
(REVIEW/'projections.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('CAM_FIRST_PROJECTIONS',len(centers),flush=True)

"""Extract source-based projections of the saved six-wire stage, read-only."""
from pathlib import Path
REVIEW_SCRIPT=Path(__file__).resolve()
REVIEW_HELPER=REVIEW_SCRIPT.parent/'screen_CAM_H02_back_transition.py'
__file__=str(REVIEW_HELPER)
exec(compile(REVIEW_HELPER.read_text().split('\nSTEPS=57;',1)[0],str(REVIEW_HELPER),'exec'),globals())
__file__=str(REVIEW_SCRIPT)
OUT=ORDER_OUT/'CAM_H02_joint_lift'
planes={'XZ':np.array([[1,0,0,0],[0,0,1,0],[0,-1,0,0]],dtype=float),
        'YZ':np.array([[0,1,0,0],[0,0,1,0],[1,0,0,0]],dtype=float)}
names=['Body_Upper','Load_Frame','Yaw_Base','Yaw_Bearing','Power_Module','MCU_Carrier']
views={}
for index in [0,18,36]:
    bt=trans(z=.5*index);st=np.asarray(joint['shell_transform'])
    projections={}
    for plane,T in planes.items():
        projections[plane]={}
        for name in names:
            mat=bt if name in bridge else st if name in upper else I
            m=phys[name].transform(mat[:3,:4])
            projections[plane][name]=[np.asarray(p).tolist() for p in m.transform(T).project().to_polygons()]
    views[str(index)]=dict(bridge_z_mm=.5*index,projections=projections,
        curves={str(pin):start_curves[f'pin{pin}_pose{index}'].tolist() for pin in range(1,5)})
body_projections={}
for plane,T in planes.items():
    body_projections[plane]={name:[np.asarray(p).tolist() for p in row[0].transform(T).project().to_polygons()]
                             for name,row in target_data.items() if name.startswith('fixed_wire_')}
    assert len(body_projections[plane])==14
old_path=ORDER_OUT/'H02_preinstalled/screen.json';old=json.loads(old_path.read_text())
old_routes=old['selected']['routes']
assert len(old_routes)==2 and all('curve_mm' in r for r in old_routes)
new_routes=joint['selected']['h02']
plug_pose=shellpose(15.,0.,14.)
rear_plug=plug['rear_J2'].m.transform(plug_pose[:3,:4])
load_frame=phys['Load_Frame']
intersection=rear_plug^load_frame
assert intersection.volume()>1e-5
ib=np.asarray(intersection.bounding_box())
witness=dict(upper_pose=dict(tilt_deg=15.,rearward_mm=0.,lift_mm=14.),
             intersection_mm3=float(intersection.volume()),bounds_mm=ib.tolist(),
             center_mm=((ib[:3]+ib[3:])/2).tolist(),
             evidence='DOCUMENTED_HOUSING_WITH_CONSERVATIVE_NORMAL_BOUNDS; physical interference not established',
             projections={plane:{name:[np.asarray(p).tolist() for p in shape.transform(T).project().to_polygons()]
                                 for name,shape in [('Load_Frame',load_frame),('Plug_rear_J2',rear_plug),('overlap',intersection)]}
                          for plane,T in planes.items()})
inputs={str(p.relative_to(PROJECT)):sha(p) for p in [REVIEW_HELPER,joint_path,joint_check_path,
        JOINT/'curves.npz',JOINT/'wire_solids.json',old_path,membership_path]}
report=dict(status='PASS',scope='Saved six-wire stage projections only, not full assembly',
            script_sha256=sha(REVIEW_SCRIPT),source_files=inputs,protected_sources=protected,
            views=views,body_projections=body_projections,
            old_h02=old_routes,new_h02=new_routes,rear_J2_witness=witness,
            main_applied=False,whole_harness='BLOCKED')
(OUT/'projections.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('CAM_H02_REVIEW_EXTRACTED',len(views),flush=True)

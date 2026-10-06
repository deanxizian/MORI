"""Checks for the requested local M1.10 changes, in the calibrated zero pose."""
from common import *

def validate_detail_fit(solids,Solid,intersect_volume,check):
    if not P.get('detail_fit',{}).get('enabled'):return
    centre=np.array([0.,0.,D['head_z']]);camera=[]
    for n in ['Camera_Lens','Camera_Window']:
        radius=float(np.linalg.norm(solids[n].v-centre,axis=1).max())
        camera.append({'part':n,'maximum_radius_mm':radius,'mother_radius_mm':D['head_radius'],'inset_mm':D['head_radius']-radius})
    default=P['head_joint']['default_pitch_deg'];limits=P['head_joint']['pitch_range_deg']
    check('camera_recess_and_default_pitch','PASS' if all(r['inset_mm']>=0 for r in camera) and limits[0]<=default<=limits[1] else 'FAIL',
          '相机镜筒/保护窗均在头球轮廓内；默认上仰10°',{'meshes':camera,'default_pitch_deg':default,'absolute_joint_limits_deg':limits},
          'All mesh vertices within convex mother sphere; invariant under head rotation. Default is a saved pose, not an extra10deg added to joint limits. Exact camera package remains assumed.')
    pose(0,default);default_bounds=np.array([bounds(o) for o in parts() if o.get('group')!='dock']);assembled()
    data={'default_pitch_deg':default,'bounds_xyz_mm':[[float(default_bounds[:,i,0].min()),float(default_bounds[:,i,1].max())] for i in range(3)],'units':'mm'}
    check('default_pose_height','PASS' if data['bounds_xyz_mm'][2][1]<=300 else 'FAIL','默认仰头姿态的实际尺寸',data,'Actual transformed meshes, separate from zero-pose assembly datum and full-range motion sampling')
    switch=(solids['Power_Switch'].lo+solids['Power_Switch'].hi)/2;usb=(solids['USB_Receptacle'].lo+solids['USB_Receptacle'].hi)/2
    reset=[n for n in solids if 'reset' in n.lower()]
    check('vertical_rear_ports','PASS' if abs(switch[0]-usb[0])<.01 and switch[2]-usb[2]>=15 and not reset else 'FAIL',
          '电源/禁驱开关在USB-C正上方，无独立外置重置件',{'switch_center_mm':switch.tolist(),'usb_center_mm':usb.tolist(),'vertical_pitch_mm':float(switch[2]-usb[2]),'external_reset_objects':reset,'functional_button':'Function_Button retained as STOP/function, explicitly not RESET'})
    speaker=solids['Speaker_Mount'];shell=solids['Body_Upper'];frame=solids['Load_Frame'];s=P['detail_fit']['speaker']
    shellspeaker={'shell_contact_gap_mm':speaker.m.min_gap(shell.m,50),'frame_gap_mm':speaker.m.min_gap(frame.m,50),
       'shell_overlap_mm3':intersect_volume(speaker,shell),'speaker_overlap_mm3':intersect_volume(speaker,solids['Speaker']),
       'fasteners':2,'nominal_diaphragm_clearance_mm':1.2,'supplier_minimum_mm':.8,'tolerance_mm':s['dim_tolerance_mm']}
    check('speaker_shell_attachment','PASS' if shellspeaker['shell_contact_gap_mm']<.02 and shellspeaker['frame_gap_mm']>1 and shellspeaker['shell_overlap_mm3']<.01 and shellspeaker['speaker_overlap_mm3']<.01 else 'FAIL',
          '扬声器压盖落在外壳固定座，内框架无连接',shellspeaker,'Nominal actual-solid contact and intersections; independent removable rear cup. Supplier +/-0.3mm, gasket compression, acoustics and preload are not certified.')
    # Remove upper shell from frame before using these inside-facing screws.
    from mathutils import Matrix,Vector
    tr=Matrix(json.loads((ROOT/'reports/speaker_mount.json').read_text())['world_transform']);toolrows=[]
    keep=['Body_Upper','Speaker','Speaker_Mount','Speaker_Gasket','Speaker_Insert_-1','Speaker_Insert_1']
    for side in [-1,1]:
        tool=cyl('speaker_tool',(side*24,-21.7,0),2.1,30,'Y');tool.matrix_world=tr@tool.matrix_world;bpy.context.view_layer.update();a=Solid(tool)
        overlaps=[{'part':n,'volume_mm3':v} for n in keep if (v:=intersect_volume(a,solids[n]))>.01]
        toolrows.append({'side':side,'failures':overlaps});bpy.data.objects.remove(tool,do_unlink=True)
    check('speaker_shell_tool_access','PASS' if not any(x['failures'] for x in toolrows) else 'FAIL','抬出上壳并断开音频插头后的压盖工具空间',{'rows':toolrows,'shaft_diameter_mm':4.2,'shaft_length_mm':30},'Same speaker and shell solids; frame removed from bench assembly. Handle/fingers and connector qualification remain NOT_TESTED.')
    # A solid cap behind each blind pilot must survive. This checks local
    # remaining material, not a global wall-thickness qualification.
    caprows=[]
    for side in [-1,1]:
        probe=cyl('speaker_blind_cap',(side*24,2.425,0),1.65,1.15,'Y');probe.matrix_world=tr@probe.matrix_world;bpy.context.view_layer.update();a=Solid(probe)
        caprows.append({'side':side,'missing_material_mm3':float((a.m-shell.m).volume()),'checked_cap_thickness_mm':1.15})
        bpy.data.objects.remove(probe,do_unlink=True)
    check('speaker_blind_boss_skin','PASS' if all(x['missing_material_mm3']<.001 for x in caprows) else 'FAIL','扬声器从壳内安装，盲孔末端保留外表皮',{'rows':caprows,'screw_trial':'M2x6'},'Actual shell-solid containment of a1.15mm-thick cap behind each insert pilot; local nominal check, not universal wall-thickness or heat-insert strength proof.')
    weact=json.loads((ROOT/'reports/vendor_weact_import.json').read_text())
    check('weact_vendor_CAD_import','PASS' if weact['source_scale_factor']==1 and weact['solid_count']==224 else 'FAIL','WeAct V1.1原厂224实体按毫米刚性导入',weact,'CAD mesh preserved; complete CAD bounding solid used conservatively in collision checks. Actual carrier/header stack not qualified.')
    check('selected_battery_speaker_nominals','PASS' if np.max(np.abs(solids['Battery'].hi-solids['Battery'].lo-np.array([71,55,20])))<.01 else 'FAIL',
          '成品电池与扬声器采用明确型号的名义尺寸',{'battery':'Tenergy31013 71x55x20mm150g','speaker':'Same Sky CMS-4017-34SP diameter40x17.5mm25g +/-0.3','selection_release':'GEOMETRY_ONLY','battery_NTC_balance_local_cost_charger':'BLOCKED'},'Manufacturer nominal envelope/drawing, no physical measurements; not a procurement or power-on approval.')
    check('onboard_microphone_registration','BLOCKED','两颗板载MIC实体、声孔和独立声道已示意；位置/封装仅照片估计',P['detail_fit']['mic_photo_estimate'],'Vendor board image registered to37mm outline. Does not provide metrology; actual board and acoustic gasket alignment must be measured. No independent microphone purchase.')
    save_json(ROOT/'reports/detail_fit_validation.json',{'revision':P['revision'],'camera':camera,'default_pose':data,'speaker_attachment':shellspeaker,'speaker_tools':toolrows,'speaker_blind_caps':caprows,'real_camera_CAM_and_carrier_fit':'BLOCKED'})

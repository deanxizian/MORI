"""New-interface checks supplement, never waive, full mesh interference checks."""
from common import *
def validate_cleanup(solids,Solid,iv,check):
    q=P.get('layout_cleanup',{})
    if not q.get('enabled'):return
    im=solids['Body_IMU'];bat=solids['Battery'];deck=solids['Load_Frame'];bottom=P['layout']['deck_z_mm']-P['layout']['deck_thickness_mm']/2
    gap=im.m.min_gap(bat.m,30);plug=bpy.data.objects[PREFIX+'IMU_Plug_Reserve'];p=Solid(plug)
    collisions=[{'part':n,'mm3':round(v,3)} for n,b in solids.items() if n!='Body_IMU' and (v:=iv(p,b))>.01]
    check('imu_underside_rigid_mount','PASS' if im.hi[2]<bottom and gap>=3 and not collisions else 'FAIL','原生20×16 IMU装到主托板底面，器件向下；检查电池及插头空间',{'board_bounds_mm':list(zip(im.lo.tolist(),im.hi.tolist())),'deck_underside_plane_z_mm':bottom,'battery_actual_solid_gap_mm':gap,'plug_allocation_mm':[14,7,10],'plug_conflicts':collisions,'axis_transform':'imu_mount_transform.json'},'Actual P2 library CAD at1:1. P3 component changes, mating plug and ICM die-to-board axes require verification; PCB normal is -Z, not an automatic firmware calibration.')
    absent=[n for n in ['Function_Button','Button_Cap','Body_Cheek_L','Body_Cheek_R','Power_Board_Carrier'] if n in solids]
    check('removed_redundant_parts','PASS' if not absent else 'FAIL','移除独立功能键；两侧短板与主托板合并，删除独立电源托板',{'unexpected_objects':absent,'changes':'layout_cleanup_changes.json'})
    check('level_head_independent_optics','PASS' if P['head_joint']['default_pitch_deg']==0 else 'FAIL','头底切面保持水平，屏幕/相机单独固定上仰',json.loads((ROOT/'reports/optical_mounts.json').read_text()),'Applied rigid mounting transforms only to optics, with a new upright screen fork; mechanical controller zero is unchanged. Full assembly/ray/motion checks are separate.')
    # New PCB screw access: bench assembly before electronics/head installation.
    toolrows=[]
    for n in ['IMU_Screw_0','IMU_Screw_1','Rear_Interface_Screw_0','Rear_Interface_Screw_1']:
        a=solids[n];c=(a.lo+a.hi)/2;under=True;start=float(a.lo[2] if under else a.hi[2]);sgn=-1 if under else 1
        tool=cyl('new_board_tool',(c[0],c[1],start+sgn*15.2),2.1,30);ts=Solid(tool)
        targets=['Load_Frame','Body_IMU'] if n.startswith('IMU_') else ['Body_Upper','Rear_Interface_PCB','Power_Switch','USB_Receptacle']
        bad=[{'part':k,'mm3':round(v,3)} for k in targets if (v:=iv(ts,solids[k]))>.01]
        toolrows.append({'screw':n,'direction':'-Z' if under else '+Z','bench_prerequisite':'IMU before battery/drive; interface PCB on detached upper shell','failures':bad});bpy.data.objects.remove(tool,do_unlink=True)
    check('new_PCB_bench_tool_access','FAIL' if any(x['failures'] for x in toolrows) else 'PASS','IMU底面与后接口板的台面装配工具杆空间',toolrows,'4.2mm diameter30mm shafts, prescribed bench sequence. Not a whole-hand/driver-handle proof.')
    check('rear_interface_double_sided_selection','BLOCKED','后接口板已生成板框、壳体安装座及上下开口；双面侧出器件待另任务选型',json.loads((ROOT/'reports/rear_interface_geometry.json').read_text()),'Nominal interfaces are requirements. No exact purchased switch/USB CAD or electrical pin assignment is claimed.')
    check('native_P3_handoff','BLOCKED','P2原生基板/IMU已1:1摆入，电源80×55容量已纳入；正在修改的P3装件与插头仍待交接',{'mechanical_design_dimensions_changed':False,'P2_reference_files':['mechanical/studies/pcb_P2_fit/motion_mesh.json','mechanical/studies/pcb_P2_fit/imu_mesh.json'],'power_capacity':'config/geometry.json#/layout_cleanup/power_bay'},'No edits to KiCad files. P2 library CAD is a reference, never labeled final P3 physical hardware.')

    # Same-group wires do not move relative to their seats, but still need real
    # passages. The general motion pass checks cross-group sweeps separately.
    wirebad=[]
    for o in bpy.context.scene.objects:
        if o.get('role')!='routing':continue
        a=Solid(o)
        for n,b in solids.items():
            if a.group==b.group and (v:=iv(a,b))>.05:wirebad.append({'route':a.name,'part':n,'intersection_mm3':round(v,3)})
    check('static_same_group_wire_passages','PASS' if not wirebad else 'FAIL','全部已画线束预留与同组实体的通孔/槽检查',{'failures':wirebad,'volume_threshold_mm3':.05},'Triangle-solid intersections of the actual routing tubes, including same-group parts. Does not certify real connectors, minimum cable bend radius or strain relief.')
    rows=[]
    cases=[('Rear_interface_bench',['Rear_Interface_PCB','Power_Switch','USB_Receptacle'],['Body_Upper'],(0,1,0),50),('Load_frame_bench',['Load_Frame','Body_IMU','IMU_Screw_0','IMU_Screw_1','IMU_Insert_0','IMU_Insert_1'],['Drive_Bridge','Drive_Motor_L','Drive_Motor_R','Tire_L','Tire_R','Motor_Retainer'],(0,0,1),54)]
    for label,moving,obstacles,direction,length in cases:
        bad=[]
        for step in range(0,length+1,2):
            tr=Matrix.Translation(Vector(direction)*step)
            for n in moving:
                a=Solid(solids[n].o,solids[n],tr)
                for k in obstacles:
                    if (v:=iv(a,solids[k]))>.01:bad.append({'travel_mm':step,'part':n,'obstacle':k,'volume_mm3':round(v,3)})
        rows.append({'case':label,'moving':moving,'obstacles':obstacles,'direction':direction,'travel_mm':length,'step_mm':2,'failures':bad})
    check('merged_frame_and_rear_PCB_removal','PASS' if not any(r['failures'] for r in rows) else 'FAIL','一体短侧板主框与后接口板的规定台面拆出路径',{'cases':rows,'prerequisites':['Rear PCB: upper shell detached, wires disconnected and two underside screws removed; slide toward+Y','Main frame: remove shells, battery/tray, head/yaw bridge, top electronics and four lower drive joints first; lift frame with underside IMU']},'Finite2mm translation samples with listed actual solids. No hand/cable-flex or arbitrary-order assembly claim.')
    save_json(ROOT/'reports/layout_cleanup_validation.json',{'revision':P['revision'],'wire_passages':wirebad,'removal_cases':rows,'status':'FAIL' if wirebad or any(r['failures'] for r in rows) else 'PASS'})

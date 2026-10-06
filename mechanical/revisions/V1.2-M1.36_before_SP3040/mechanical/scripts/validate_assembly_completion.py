"""M1.35 source, captive-mount and finite assembly path checks."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from optics_mount import camera_transform,camera_pupil

def validate_assembly_completion(solids,Solid,iv,check):
    q=P.get('assembly_completion',{})
    if not q.get('enabled'):return
    results={};errors=[]
    from validate_head_cleanup import geometry_record
    base=json.loads((PROJECT/q['baseline_geometry']).read_text());now={o.name.removeprefix(PREFIX):geometry_record(o) for o in parts()}
    changed=sorted(n for n in now if now[n]!=base['parts'].get(n));retired=sorted(set(base['parts'])-set(now));allowed=set(q['changed_existing_ids']+q['new_ids'])
    allowed.update(declared_cap_edge_changes())
    unexpected=sorted(set(changed)-allowed);missing=sorted(set(q['new_ids'])-set(now))
    scope={'baseline':base['revision'],'changed':changed,'unexpected':unexpected,'retired':retired,'missing_new':missing,'allowed_current_stage':sorted(allowed),'later_cap_edge_edit_checked_separately':sorted(declared_cap_edge_changes())}
    results['scope']=scope
    check('completion_scope','PASS' if not unexpected and not retired and not missing else 'FAIL','本轮仅改已列出的固定结构、相机位置与正式交接PCB',scope,'All current part mesh/matrix hashes vs immutable M1.34. Original LCD/WeAct/drive/servo geometry and approved shell-lug holes remain protected by independent checks.')
    if unexpected or retired or missing:errors.append('scope')
    def intersections(m,obstacles,tol=.01):
        bb=np.array(m.bounding_box());out=[]
        for n in obstacles:
            a=solids[n]
            if np.any(bb[3:]<a.lo) or np.any(a.hi<bb[:3]):continue
            v=max(0,(m^a.m).volume())
            if v>tol:out.append({'part':n,'volume_mm3':v})
        return out
    # CAM board is attached to the cradle on the bench before fitting the head.
    rows=[];cradle=['Pitch_Cradle'];board=solids['CAM_Mainboard'].m
    for step in range(61):
        d=step*.5;hits=intersections(board.translate([0,d,0]),cradle)
        if hits:rows.append({'distance_mm':d,'hits':hits})
    tools=[]
    for n in sorted(k for k in solids if k.startswith('CAM_Mount_Screw_')):
        a=solids[n];x,z=(a.lo+a.hi)[[0,2]]/2;start=float(a.hi[1]);r=1.5
        shaft=manifold.Manifold.cylinder(30,r,r,48).rotate([-90,0,0]).translate([x,start,z])
        hits=intersections(shaft,cradle+['CAM_Mainboard','Onboard_MIC_L','Onboard_MIC_R'])
        tools.append({'screw':n,'shaft_diameter_mm':2*r,'length_mm':30,'hits':hits})
    results['CAM']={'board_insertion_samples':61,'step_mm':.5,'direction':[0,1,0],'obstacles':cradle,'board_path_failures':rows,'tool_probes':tools,'prerequisite':'Bench assembly to Pitch_Cradle before optical fork/servo/head-shell assembly; not in-place service with head closed.'}
    ok=not rows and not any(t['hits'] for t in tools)
    check('completion_cam_mount_access','PASS' if ok else 'FAIL','CAM原板四孔固定及拆下头托时的装板、螺丝刀直杆空间',results['CAM'],'Actual closed meshes,61 positions at0.5mm; four nominal3mm tool shafts. Threads, hand grips, solder joints and as-built tolerances not covered.')
    if not ok:errors.append('CAM')
    rc=np.array(camera_transform().to_3x3())@np.array([[1.,0,0],[0,0,1.],[0,-1.,0]])
    cm=solids['Camera_PCB'].m+solids['Camera_Lens'].m;front=rc[:,2]
    obstacles=[n for n in solids if n not in ['Head_Front','Head_Rear','Camera_Window','Camera_PCB','Camera_Lens']]
    rows=[]
    for d in np.arange(0,20.01,.5):
        hits=intersections(cm.translate((front*d).tolist()),obstacles)
        if hits:rows.append({'distance_mm':float(d),'hits':hits})
    capture=[]
    for axis in range(3):
        for sign in [-1,1]:
            hits=intersections(cm.translate((rc[:,axis]*sign*.5).tolist()),['Display_Frame','Head_Front'])
            capture.append({'local_axis':axis,'sign':sign,'displacement_mm':.5,'contact_obstacles':hits})
    close=[]
    for d in np.arange(0,12.01,.5):
        hits=intersections(solids['Head_Front'].m.translate([0,float(d),0]),['Camera_PCB','Camera_Lens','Display_Frame','Pitch_Cradle'])
        if hits:close.append({'distance_mm':float(d),'hits':hits})
    results['camera']={'front_insertion_samples':41,'step_mm':.5,'direction':front.tolist(),'insertion_failures':rows,'capture_probes':capture,'head_front_close_path':close,'head_front_direction':[0,1,0],'closure_samples':25,'prerequisite':'Front and rear shell removed; camera inserted into existing fork, then front shell closes pocket. Optical sheets not included in this local closure test.'}
    ok=not rows and all(r['contact_obstacles'] for r in capture) and not close
    check('completion_camera_capture','PASS' if ok else 'FAIL','相机由原支架与前壳限位，不增加压盖、螺钉或弹性卡臂',results['camera'],'Rigid solid insertion/closure samples and six0.5mm diagnostic escape translations. Contact at probe displacement demonstrates nominal capture only, not preload, stiffness or a continuous path proof.')
    if not ok:errors.append('camera')
    bm=solids['Battery'].m+solids['Battery_Tray'].m+solids['Battery_Strap'].m+solids['Battery_Pad_Top'].m
    excluded={'Battery','Battery_Tray','Battery_Strap','Body_Lower','Body_Upper','Speaker','Speaker_Front_Gasket','Power_Switch','USB_Receptacle','Rear_Interface_PCB'}|{n for n in solids if n.startswith(('Battery_Pad','Battery_Retainer','Battery_Hanger','Shell_Screw','Shell_Insert','Speaker_','Rear_Interface_'))}
    rows=[]
    for d in range(0,121,3):
        hits=intersections(bm.translate([0,d,0]),set(solids)-excluded)
        if hits:rows.append({'distance_mm':d,'hits':hits})
    results['battery']={'pack_mm':[71,55,20],'strap_installed':True,'extraction_samples':41,'step_mm':3,'failures':rows,'removed_with_shell':sorted(excluded-set(['Battery','Battery_Tray','Battery_Strap'])),'prerequisite':'Upper shell removed together with its attached speaker/rear PCB; lower shell and tray-side screws removed. Strap stays with pack/tray. Unplugging and flexible band threading not simulated.'}
    check('completion_battery_strap_extraction','PASS' if not rows else 'FAIL','当前小型3S电池增加绑带后，随托盘向前取出',results['battery'],'Closed-solid sampled path, including strap and top pad; no cable, flexible material or clamp-force qualification.')
    if rows:errors.append('battery')
    results.update(revision=P['revision'],status='FAIL' if errors else 'PASS',failed_sections=errors,manufacturing_release=False,physical_fit='NOT_TESTED',wiring='DEFERRED_BY_USER')
    save_json(ROOT/'reports/assembly_completion_validation.json',results)

if __name__=='__main__':
    from validate import Solid,intersect_volume,check,camera_checks,CHECKS
    from validate_microphones import validate_microphones
    bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections()
    for n in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[n].hide_viewport=False
    assembled();ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.get('group')!='dock'}
    camera_checks(ss);validate_microphones(ss,Solid,intersect_volume,check);validate_assembly_completion(ss,Solid,intersect_volume,check)
    save_json(ROOT/'reports/completion_local_checks.json',{'revision':P['revision'],'checks':CHECKS})

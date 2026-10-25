"""Complete discrete mounting interfaces from the shared M1.35 parameters.

Nominal candidate geometry, never measured hardware or print qualification.
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from monocoque_structure import obj,source_build
from structural_simplification import hardware
from layout_cleanup import mm_mesh
from waveshare_detail import rounded_plate
from optics_mount import camera_transform,camera_pupil

S=P.get('assembly_completion',{})

def trial(o,label,group='pitch'):
    hardware(o,label,group)
    o['model_fidelity']='NOMINAL_FASTENER_ENVELOPE'
    o['interface_status']='Candidate nominal hardware; exact supplier, torque, insert and print fits require coupon.'
    return o

def cam_mount():
    q=S['cam_mount'];c=P['waveshare_detail']['cam'];x,y,z=P['layout']['cam_board_center_from_head_mm'];z+=D['head_z']
    h=P['head_print_cleanup'];rear=h['cradle_rear_y_mm'];wall=h['cradle_wall_mm'];back=y-c['pcb_thickness_mm']/2-q['pad_surface_extra_mm'];front=y+c['pcb_thickness_mm']/2+q['pad_surface_extra_mm']
    top=z+c['hole_grid_mm']/2+q['top_margin_mm'];bottom=D['head_z']+h['cradle_bottom_from_head_mm'];o=obj('Pitch_Cradle')
    # Continue the existing broad rear wall; no separate spanning rods or frame.
    union(o,box('CAM_integral_backplate',(x,rear+wall/2,(top+bottom)/2),(q['rear_plate_width_mm'],wall,top-bottom)))
    sites=[]
    for i,(u,v) in enumerate(( (u,v) for u in [-1,1] for v in [-1,1] )):
        xx=x+u*c['hole_grid_mm']/2;zz=z+v*c['hole_grid_mm']/2
        seat_center=(xx,(rear+wall-.2+back)/2,zz)
        seat_depth=back-(rear+wall)+.2
        if q.get('support_shape')=='square':
            side=q['support_side_mm']
            union(o,box('CAM_plain_short_seat',seat_center,(side,seat_depth,side)))
        else:
            union(o,cyl('CAM_short_seat',seat_center,q['support_diameter_mm']/2,seat_depth,'Y'))
        boolean(o,cyl('CAM_trial_pilot',(xx,back-2.45,zz),q['pilot_diameter_mm']/2,5.1,'Y'))
        ins=ring('CAM_Mount_Insert_'+str(i),(xx,back-.2-q['insert_length_mm']/2,zz),q['insert_outer_diameter_mm']/2,1.05,q['insert_length_mm'],'Y')
        trial(ins,'CAM固定 M2短嵌件 / 试配')
        length=q['screw_length_mm'];bolt=cyl('CAM_Mount_Screw_'+str(i),(xx,front-length/2,zz),.95,length,'Y')
        union(bolt,cyl('CAM_M2_head',(xx,front+.75,zz),1.9,1.5,'Y'));trial(bolt,'CAM固定 M2×'+str(length)+' / 从头内操作')
        sites.append({'xy_board_mm':[u*c['hole_grid_mm']/2,v*c['hole_grid_mm']/2],'axis_world_xz_mm':[xx,zz],'support_face_y_mm':back,'screw_bearing_face_y_mm':front})
    acoustic=[]
    if q.get('acoustic_openings',{}).get('enabled'):
        from microphone_geometry import microphone_paths
        for row in microphone_paths():
            radius=q['acoustic_openings']['radius_mm']
            boolean(o,source_build().beam('CAM_existing_sound_path',row['start'],row['inner'],radius))
            acoustic.append(dict(side=row['side'],start_mm=list(row['start']),end_mm=list(row['inner']),radius_mm=radius))
    o['CAM_retention']='Four documented hole-grid sites, full-root integral short seats and rear plate; four M2 trial fasteners. Two acoustic openings preserve existing assumed mic paths. Board packages and port geometry remain photo estimates.' if acoustic else 'Four documented hole-grid sites, integral rear wall and short seats; four M2 trial fasteners. Board package heights remain photo estimates.'
    source_build().contact('Pitch_Cradle','CAM_Mainboard','Four corner annuli bear on integral seats; no component bodies used as supports')
    return {'sites':sites,'rear_wall_top_z_mm':top,'rear_plate_width_mm':q['rear_plate_width_mm'],'support_shape':q.get('support_shape','round'),'support_side_mm':q.get('support_side_mm'),'acoustic_openings':acoustic,'separate_prints_added':0,'mated_cable_fit':'DEFERRED','physical_fit':'NOT_TESTED'}

def battery_retention():
    q=S['battery_retention'];tray=obj('Battery_Tray');bb=np.asarray(bounds(obj('Battery')));tb=np.asarray(bounds(tray));bottom=float(tb[2,0]);top=float(bb[2,1])+q['top_pad_thickness_mm'];t=q['strap_thickness_mm'];w=q['strap_width_mm']
    for yy in [-29,29]:boolean(tray,box('battery_strap_trial_slot',(0,yy,bottom+1.5),(q['strap_slot_width_mm'],q['strap_slot_depth_mm'],9)))
    inner_y=58.;height=top-bottom;zc=(top+bottom)/2
    # Rounded Y/Z band passes through the tray slots and under its floor.
    band=rounded_plate(inner_y+2*t,height+2*t,w,3)-rounded_plate(inner_y,height,w+2,1.5)
    band=band.transform([[0,0,1,0],[1,0,0,0],[0,1,0,zc]])
    strap=mm_mesh('Battery_Strap',band);finish(strap,'PURCHASED_REFERENCE','20mm自粘绑带 / 包体压持候选','tire','body',False)
    strap['model_fidelity']='NOMINAL_FLEXIBLE_STRAP_REQUIREMENT';strap['interface_status']='20mm self-engaging strap requirement;1.5mm nominal thickness assumption. Routing and overlap are modeled, compression/retention loads are NOT_TESTED.'
    overlap=box('strap_overlap',(0,0,top+t*1.5-.02),(w,30,t));union(strap,overlap)
    pad=box('Battery_Pad_Top',(0,0,top-q['top_pad_thickness_mm']/2),(w,52,q['top_pad_thickness_mm']))
    finish(pad,'PLACEHOLDER','电池顶部软垫 / 试配压缩厚度','tire','body',False)
    pad['model_fidelity']='NOMINAL_COMPRESSED_FOAM_ALLOCATION'
    pad['interface_status']='20x52x1mm nominal soft pad requirement; material, compression and real pack tolerance not measured.'
    b=source_build();b.contact('Battery_Strap','Battery_Tray','Flexible strap passes through two enlarged slots and bears below the tray');b.contact('Battery_Pad_Top','Battery','Soft top pad nominal bearing, compression not modeled');b.contact('Battery_Strap','Battery_Pad_Top','Strap retains pack downward through soft top pad')
    return {'strap_width_mm':w,'nominal_thickness_mm':t,'top_z_mm':top+2*t,'slot_centers_y_mm':[-29,29],'pack_dimensions_mm':list(bb[:,1]-bb[:,0]),'physical_fit':'NOT_TESTED','minimum_cut_length_mm':2*(inner_y+height)+30,'note':'Nominal cut requirement includes30mm overlap; confirm actual tape and compression before cutting.'}

def camera_capture():
    """A rigid captive pocket closed by the already-removable head front.

    Trial clearances are explicit, not a claim of preload or a qualified fit.
    Front lips bear on the plastic base, clear of the optical barrel and flex.
    """
    q=S['camera'];c=P['waveshare_detail']['camera'];h=P['head_print_cleanup']
    frame=obj('Display_Frame');shell=obj('Head_Front');hz=D['head_z']
    r=np.array(camera_transform().to_3x3())@np.array([[1.,0,0],[0,0,1.],[0,-1.,0]])
    p=np.array(camera_pupil());tr=np.column_stack([r,p]).tolist()
    def local(name,lo,hi):
        lo=np.array(lo);hi=np.array(hi)
        return mm_mesh(name,manifold.Manifold.cube((hi-lo).tolist()).translate(lo.tolist()).transform(tr))
    # Remove only the superseded provisional top camera pocket.
    boolean(frame,box('retire_old_camera_seat',(0,29,hz+70),(20,32,2*(70-q['mast_replace_above_z_from_head_mm']))))
    m0=hz+q['mast_replace_above_z_from_head_mm']-.2;m1=hz+q['mast_support_top_z_from_head_mm']
    union(frame,box('camera_pocket_mast',(0,h['face_mast_y_mm'],(m0+m1)/2),(h['face_mast_width_mm'],h['face_mast_thickness_mm'],m1-m0)))
    wx,vy=q['pocket_outer_xy_mm'];back=c['carrier_back_from_pupil_mm'];cx,cy=np.array(c['carrier_xy_mm'])/2+q['pocket_xy_clearance_mm']
    pocket=local('camera_captive_pocket',[-wx/2,-vy/2,q['pocket_back_w_mm']],[wx/2,vy/2,q['pocket_wall_front_w_mm']])
    union(frame,pocket)
    boolean(frame,local('camera_front_insertion',[-cx,-cy,back-q['pocket_back_clearance_mm']],[cx,cy,12]))
    # Keep the carrier tail edge open; this is not an invented routed FPC hole.
    tail=c['flat_fpc_width_mm']/2+.3
    boolean(frame,local('camera_tail_open_edge',[-tail,cy-.01,back-.3],[tail,vy/2+.1,4]))
    basefront=back+c['carrier_thickness_mm']+c['lens_base_depth_mm']
    front=basefront+q['front_capture_clearance_mm']
    for sign in [-1,1]:
        x0,x1=sorted([sign*q['lip_inner_x_mm'],sign*q['lip_outer_x_mm']])
        union(shell,local('camera_integral_front_lip',[x0,-q['lip_half_height_mm'],front],[x1,q['lip_half_height_mm'],front+q['lip_thickness_mm']]))
    if q.get('outer_fov_flare_enabled'):
        # Candidate only: begin ahead of the unchanged protective window.
        w0=q['fov_flare_start_w_mm'];w1=q['fov_flare_end_w_mm'];clear=q['fov_flare_margin_mm']
        hx=math.tan(math.radians(P['camera']['assumed_hfov_deg']/2));hy=math.tan(math.radians(P['camera']['assumed_vfov_deg']/2))
        points=[[sx*(w*hx+clear),sy*(w*hy+clear),w] for w in [w0,w1] for sx in [-1,1] for sy in [-1,1]]
        cone=manifold.Manifold.hull_points(points).transform(tr)
        boolean(shell,mm_mesh('camera_outer_fov_flare_candidate',cone))
    frame['camera_retention']='Front-loaded rectangular pocket; carrier-edge rear stop and four planar side datums. Existing head-front lips capture plastic lens base; no extra cap/screw, no snap deformation claimed.'
    shell['camera_retention']='Two short integral inward lips close the camera pocket when front shell is attached. Trial clearances require a measured camera and fit coupon; no pressure on optical barrel/FPC.'
    source_build().contact('Camera_PCB','Display_Frame','Candidate peripheral support; nominal rear gap0.15mm before settling, not a preload claim')
    source_build().contact('Camera_Lens','Head_Front','Two integral lips capture plastic base; nominal front gap0.15mm, no optical barrel contact')
    return {'retention':'EXISTING_PARTS_CAPTIVE_POCKET','added_parts':0,'added_fasteners':0,'module_pupil_world_mm':p.tolist(),'local_basis_columns':r.tolist(),
      'nominal_module_recess_mm':q['optical_recess_mm'],'side_clearance_each_mm':q['pocket_xy_clearance_mm'],'total_nominal_axial_float_mm':q['pocket_back_clearance_mm']+q['front_capture_clearance_mm'],
      'physical_fit':'NOT_TESTED','preload':'NONE_CLAIMED; verify real dimensions and tighten candidate pocket tolerance before optical calibration',
      'assembly':'With Head_Front removed, insert module from optical-front side into Display_Frame pocket; mate front shell so its two lips close the pocket. Remove shell to release. FPC route is deferred, its exit edge remains open.'}

def apply_assembly_completion():
    if not S.get('enabled'):return
    r={'revision':P['revision'],'CAM':cam_mount(),'battery':battery_retention(),'camera':camera_capture(),'manufacturing_release':False}
    for name,mat in [('Pitch_Cradle','frame'),('Display_Frame','frame'),('Head_Front','shell'),('Battery_Tray','frame'),('Battery_Strap','belt')]:
        o=obj(name);o.data.materials.clear();o.data.materials.append(MATS[mat])
    save_json(ROOT/'reports/assembly_completion_geometry.json',r)

if __name__=='__main__':
    load_collections()
    for n in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[n].hide_viewport=False
    assembled();source_build().materials()
    from waveshare_detail import apply_waveshare_detail
    apply_waveshare_detail();apply_assembly_completion()
    assembled();write_bom()
    out=ROOT/'studies/assembly_completion/candidate.blend';out.parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out))

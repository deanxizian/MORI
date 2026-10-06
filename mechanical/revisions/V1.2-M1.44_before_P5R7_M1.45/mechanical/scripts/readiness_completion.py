"""M1.38 approved optical simplification and actual head fastener candidates.

No purchased geometry is resized or relocated. Native rear SW1 remains as
received; only its shell access is retired, pending electrical-owner receipt.
"""
from common import *
from monocoque_structure import obj,source_build
from purchased_geometry import remove_generated
from optics_mount import display_transform,apply_mount
from structural_simplification import hardware
S=P.get('readiness_completion',{})

def fastener(name,face,direction,length,head_radius,head_height,label):
    face=Vector(face);axis=Vector(direction).normalized()
    tr=Matrix.Translation(face)@axis.to_track_quat('Z','Y').to_matrix().to_4x4()
    o=cyl(name,(0,0,length/2),.95,length)
    union(o,cyl('fastener_head',(0,0,-head_height/2),head_radius,head_height))
    apply_mount(o,tr);hardware(o,label,'pitch')
    o['model_fidelity']='NOMINAL_M2_FASTENER_TRIAL'
    o['interface_status']='Smooth nominal hardware envelope, not a thread model; physical thread fit, torque and printed strength NOT_TESTED.'
    return o

def integral_optics():
    q=S['optics'];front=obj('Head_Front');tr=display_transform();hz=D['head_z'];fy=D['face_y']
    rim=ring('approved_integral_bezel',(0,fy,hz),q['rim_outer_overlap_radius_mm'],q['rim_inner_radius_mm'],q['rim_thickness_mm'],'Y')
    apply_mount(rim,tr);intersect(rim,sphere('keep_mother_surface',(0,0,hz),D['head_radius']))
    union(front,rim)
    aperture=clone(obj('Camera_Window'),'Camera_Aperture_Datum')
    move_collection(aperture,'DATUMS');aperture['role']='construction';aperture['export_candidate']=False
    aperture['label_zh']='相机独立壳孔检查基准 / 不是玻璃零件'
    for n in S['retired_ids']:remove_generated(n)
    # Construction witness of the integral face only; never a separate part or STL.
    witness=clone(front,'Integrated_Face_Region')
    limit=cyl('bezel_region',(0,fy,hz),30.05,1.02,'Y');apply_mount(limit,tr);intersect(witness,limit)
    move_collection(witness,'DATUMS');witness['role']='construction';witness['export_candidate']=False
    front['optical_finish']=q['finish'];front['integrated_functions']='Integral black-painted bezel; camera no extra window; original LCD cover remains.'

def paint_integral_rim():
    o=obj('Head_Front');o.data.materials.clear();o.data.materials.append(MATS['shell']);o.data.materials.append(MATS['dark'])
    inv=display_transform().inverted();fy=D['face_y'];hz=D['head_z']
    for f in o.data.polygons:
        p=inv@(o.matrix_world@f.center)
        f.material_index=1 if (abs(p.y-(fy+.5))<.002 or (p.x*p.x+(p.z-hz)**2<23.5**2 and fy-.51<p.y<fy+.51)) else 0
    # Split sharp hole/plane boundaries so sphere normals cannot interpolate
    # into the open camera aperture or the newly integral planar face.
    edge_faces=[[] for _ in o.data.edges]
    for f in o.data.polygons:
        for k in f.loop_indices:edge_faces[o.data.loops[k].edge_index].append(f.index)
    for e,fs in zip(o.data.edges,edge_faces):
        if len(fs)==2 and o.data.polygons[fs[0]].normal.angle(o.data.polygons[fs[1]].normal,0)>math.radians(35):e.use_edge_sharp=True
    o.data.update()

def lcd_fastening():
    q=S['lcd'];o=obj('Display_Frame');tr=display_transform();axis=tr.to_3x3()@Vector((0,1,0));rows=[]
    ext=q['lower_crossbar_extension_mm'];hz=D['head_z'];bottom=hz+q['original_crossbar_bottom_from_head_mm'];top=hz+q['crossbar_top_from_head_mm']
    holes=INTERFACES['components']['display']['vendor_dimensions']['cad_post_center_xz_from_screen_mm']
    oldrear=q['crossbar_center_y_mm']-q['crossbar_depth_mm']/2;rear=oldrear+q['crossbar_forward_shift_mm'];front=rear+q['crossbar_depth_mm'];width=q['crossbar_width_mm']
    # Full straight bar, moved towards LCD; retain original tilted post-contact
    # blocks only in front of its new back plane, so no rear screw scallops remain.
    seats=[]
    for x,z in holes[1:]:
        point=tr@Vector((x,40.1,hz+z));pad=clone(o,'retained_LCD_lower_seat')
        intersect(pad,box('retain_front_post',(x,(rear+44)/2,point.z),(7,44-rear,7)))
        seats.append(pad)
    boolean(o,box('replace_lower_crossbar',(0,(oldrear-.01+45)/2,(bottom-ext-.01+top-.001)/2),(width+.002,45-oldrear+.01,top-.001-bottom+ext+.01)))
    union(o,box('straight_lower_crossbar',(0,(rear+front)/2,(bottom-ext+top)/2),(width,q['crossbar_depth_mm'],top-bottom+ext)))
    for pad in seats:union(o,pad)
    # Broad integral lap at the existing central mast; no extra loose part,
    # thin spanning rod, cable cut or change to the camera/post datums.
    mz0=hz+q['mast_connection_bottom_from_head_mm'];mz1=hz+q['mast_connection_top_from_head_mm']
    union(o,box('continuous_mast_root',(0,(oldrear+front)/2,(mz0+mz1)/2),(P['head_print_cleanup']['face_mast_width_mm'],front-oldrear,mz1-mz0)))
    for i,((x,z),length,engagement) in enumerate(zip(holes,q['screw_lengths_mm'],q['trial_engagement_mm'])):
        p=tr@Vector((x,P['display']['vendor_mount_back_y_from_head_mm'],D['head_z']+z))
        face=p-axis*(length-engagement)
        # Reopen bores through the later-added straight rear rails. Spot faces
        # make screw bearing planes normal to the10deg optical axis.
        hole=cyl('LCD_M2_complete_bore',(0,0,0),q['clearance_radius_mm'],60)
        hole.matrix_world=Matrix.Translation(p-axis*15)@axis.to_track_quat('Z','Y').to_matrix().to_4x4();SOLIDS.pop(hole.name,None);boolean(o,hole)
        seat=cyl('LCD_head_spotface',(0,0,0),q['spotface_radius_mm'],20)
        seat.matrix_world=Matrix.Translation(face-axis*10)@axis.to_track_quat('Z','Y').to_matrix().to_4x4();SOLIDS.pop(seat.name,None);boolean(o,seat)
        n='LCD_Mount_Screw_'+str(i)
        bolt=fastener(n,face,axis,length,q['head_radius_mm'],q['head_height_mm'],f'LCD原厂M2柱固定 / M2×{length}试配')
        # The source CAD includes internal thread crests. Keep the visible
        # major-diameter envelope; omit only male thread crests in an explicitly
        # declared validation proxy. This cannot certify actual thread fit.
        proxy=clone(bolt,n+'_Thread_Root_Proxy')
        cut=ring('thread_crest_exclusion',(0,0,0),1.02,q['thread_validation']['root_diameter_mm']/2,engagement+.02)
        cut.matrix_world=Matrix.Translation(p+axis*((engagement-.02)/2))@axis.to_track_quat('Z','Y').to_matrix().to_4x4();SOLIDS.pop(cut.name,None)
        boolean(proxy,cut);move_collection(proxy,'DATUMS');proxy['role']='construction';proxy['export_candidate']=False
        bolt['validation_proxy']=proxy.name;bolt['thread_geometry_qualification']='BLOCKED; only root cylinder checked inside original CAD thread cavity'
        bolt['thread_proxy_source']=q['thread_validation']['source']
        rows.append({'id':n,'post_face_mm':list(p),'head_bearing_mm':list(face),'axis':list(axis),'length_mm':length,'trial_engagement_mm':engagement})
        source_build().contact(n,'Display_Frame','Recessed planar head bearing; original factory post coordinates')
        source_build().contact(n,'Display_PCB','Nominal M2 engagement in original CAD cavity; vendor-approved depth pending')
    o['LCD_fastening']='Three rear M2 screws on original CAD axes; rear rails reopened, local normal spot faces. Assemble LCD to detached fork first.'
    return rows

def head_shell_fastening():
    q=S['head_shell'];h=S['head_seam'];hz=D['head_z'];front=obj('Head_Front');cradle=obj('Pitch_Cradle');rows=[]
    for sign in [-1,1]:
        x,y=head_shell_mount_xy_mm(sign);seat=hz+q['head_seat_z_from_head_mm'];top=hz+q['insert_top_from_head_mm'];bot=top-q['insert_length_mm']
        boolean(front,cyl('head_external_M2_clear',(x,y,hz+47),q['clearance_radius_mm'],60))
        boolean(front,cyl('head_external_recess',(x,y,seat+25),q['counterbore_radius_mm'],50))
        lugtop=hz+P['head_print_cleanup']['cradle_shell_lug_top_from_head_mm']
        boolean(cradle,cyl('head_cradle_trial_insert',(x,y,(bot-q['pilot_extra_depth_mm']+lugtop+.2)/2),q['pilot_radius_mm'],lugtop+.2-bot+q['pilot_extra_depth_mm']))
        ins=ring('Head_Cradle_Insert_'+str(sign),(x,y,(bot+top)/2),q['insert_outer_radius_mm'],q['insert_inner_radius_mm'],q['insert_length_mm'])
        hardware(ins,'头壳固定 M2试配嵌件 / 头托原凸台内','pitch')
        n='Head_Cradle_Screw_'+str(sign);fastener(n,(x,y,seat),(0,0,-1),q['screw_length_mm'],q['head_radius_mm'],q['head_height_mm'],'头壳外侧下锁 M2×12 / 头部沉入')
        rows.append({'id':n,'head_bearing_mm':[x,y,seat],'axis':[0,0,-1],'length_mm':q['screw_length_mm'],'insert_z_mm':[bot,top],'engagement_mm':top-(seat-q['screw_length_mm'])})
        source_build().contact(n,'Head_Front','Head bears on existing front-shell lug; exterior cylindrical recess contains head')
        source_build().contact('Head_Cradle_Insert_'+str(sign),'Pitch_Cradle','Trial insert socket in existing shell lug; existing smaller bore continues underneath; no added ears')
        # The original rear seam already has a recessed head seat and front pilot.
        x=sign*h['axis_abs_x_mm'];z=hz+h['axis_z_from_head_mm'];start=h['insert_start_y_mm'];length=h['insert_length_mm']
        ins=ring('Head_Seam_Insert_'+str(sign),(x,start+length/2,z),h['insert_outer_radius_mm'],h['insert_inner_radius_mm'],length,'Y')
        hardware(ins,'前后头壳拼缝 M2试配嵌件','pitch')
        n='Head_Seam_Screw_'+str(sign);face=(x,h['head_bearing_y_mm'],z)
        fastener(n,face,(0,1,0),h['screw_length_mm'],h['head_radius_mm'],h['head_height_mm'],'头壳后侧拼缝 M2×16 / 原沉孔')
        rows.append({'id':n,'head_bearing_mm':list(face),'axis':[0,1,0],'length_mm':h['screw_length_mm'],'insert_y_mm':[start,start+length],'engagement_mm':h['head_bearing_y_mm']+h['screw_length_mm']-start})
        source_build().contact(n,'Head_Rear','Original rear sleeve counterbore; no shell ear added')
    return rows

def apply_readiness_completion():
    if not S.get('enabled'):return
    integral_optics();lcd=lcd_fastening();head=head_shell_fastening();paint_integral_rim()
    save_json(ROOT/'reports/readiness_geometry.json',{'revision':P['revision'],'LCD':lcd,'head':head,'retired_parts':S['retired_ids'],'new_printed_parts':0,'physical_fit':'NOT_TESTED','source':S['baseline_geometry'],'rear_switch':S['rear_switch']})

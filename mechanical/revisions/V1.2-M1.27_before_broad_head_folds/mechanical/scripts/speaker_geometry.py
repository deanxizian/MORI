"""M1.20 drawing-based enclosed speaker and direct upper-shell attachment.

Local axes: +Y sound/front, ears along X, front face Y=0. All dimensions mm.
Box and mounting dimensions are documented; internals, ear taper, vent and leads
are not. No vendor mesh or physical metrology is claimed.
"""
from common import *
from monocoque_structure import obj, source_build
from purchased_geometry import remove_generated, finish_reference
from structural_simplification import hardware
from belly_relayout import relocate


def direct_mount_enabled():
    return P.get('speaker_mount', {}).get('mode') == 'DIRECT_VENDOR_EARS_TO_UPPER_SHELL'


def speaker_transform():
    s = P['detail_fit']['speaker']
    return Matrix.Translation((0, 0, D['body_z'])) @ Matrix.Rotation(
        math.radians(s['radial_pitch_deg']), 4, 'X') @ Matrix.Translation((0, s['front_radius_from_body_mm'], 0))


def mount_datums():
    s, m = P['detail_fit']['speaker'], P['speaker_mount']
    front = -s['ear_front_depth_mm']
    rear = front - s['ear_thickness_mm']
    return {'mount_abs_x': s['mount_hole_pitch_mm']/2, 'ear_front_y': front,
            'ear_rear_y': rear, 'insert_back_y': front + .2,
            'insert_front_y': front + .2 + m['insert_length_mm'],
            'pilot_front_y': front + .4 + m['insert_length_mm'],
            'screw_head_base_y': rear, 'screw_tip_y': rear + m['screw_length_mm']}


def rounded_box(name, width, height, depth, radius):
    o = box(name, (0, -depth/2, 0), (width-2*radius, depth, height))
    union(o, box('rounded_box_cross', (0, -depth/2, 0), (width, depth, height-2*radius)))
    for x in [-width/2+radius, width/2-radius]:
        for z in [-height/2+radius, height/2-radius]:
            union(o, cyl('rounded_box_corner', (x, -depth/2, z), radius, depth, 'Y'))
    return o


def face_material():
    """Illustrate the documented36mm circle on the unchanged box envelope."""
    mat=material('fusheng_box',(.018,.022,.024),roughness=.55)
    nodes=mat.node_tree.nodes;links=mat.node_tree.links
    bsdf=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
    tex=nodes.new('ShaderNodeTexCoord');sep=nodes.new('ShaderNodeSeparateXYZ')
    links.new(tex.outputs['Generated'],sep.inputs[0])
    front=nodes.new('ShaderNodeMath');front.operation='GREATER_THAN';front.inputs[1].default_value=.999
    links.new(sep.outputs['Y'],front.inputs[0])
    mul=nodes.new('ShaderNodeVectorMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=(60,0,45)
    links.new(tex.outputs['Generated'],mul.inputs[0])
    sub=nodes.new('ShaderNodeVectorMath');sub.operation='SUBTRACT';sub.inputs[1].default_value=(30,0,22.5)
    links.new(mul.outputs[0],sub.inputs[0])
    length=nodes.new('ShaderNodeVectorMath');length.operation='LENGTH';links.new(sub.outputs[0],length.inputs[0])
    color=None
    for radius,c in [(18,(.09,.095,.1,1)),(16,(.01,.012,.013,1)),(13,(.035,.04,.043,1)),(6,(.012,.014,.016,1))]:
        less=nodes.new('ShaderNodeMath');less.operation='LESS_THAN';less.inputs[1].default_value=radius;links.new(length.outputs['Value'],less.inputs[0])
        mask=nodes.new('ShaderNodeMath');mask.operation='MULTIPLY';links.new(less.outputs[0],mask.inputs[0]);links.new(front.outputs[0],mask.inputs[1])
        mix=nodes.new('ShaderNodeMixRGB');links.new(mask.outputs[0],mix.inputs[0]);mix.inputs[1].default_value=(.018,.022,.024,1);mix.inputs[2].default_value=c
        if color:links.new(color,mix.inputs[1])
        color=mix.outputs[0]
    links.new(color,bsdf.inputs['Base Color'])
    return mat


def speaker_envelope(name, worst_case=False):
    s = P['detail_fit']['speaker'];d = mount_datums()
    extra = s['box_xy_tolerance_mm'] if worst_case else 0
    depth = s['depth_mm'] + (s['depth_tolerance_mm'] if worst_case else 0)
    o = rounded_box(name, s['box_width_mm']+extra, s['box_height_mm']+extra,
                    depth, s['corner_radius_mm'])
    span = s['overall_ear_span_mm'] + (s['ear_span_tolerance_mm'] if worst_case else 0)
    half_body = s['box_width_mm']/2
    for sign in [-1, 1]:
        # Taper is undimensioned: full documented 12mm root width is conservative.
        ear = box('vendor_ear_envelope', (sign*(span/2+half_body-.2)/2,
                    (d['ear_front_y']+d['ear_rear_y'])/2, 0),
                   (span/2-half_body+.2, s['ear_thickness_mm'], s['ear_width_mm']+extra))
        union(o, ear)
        boolean(o, cyl('vendor_mount_hole', (sign*d['mount_abs_x'], -11, 0),
                       s['mount_hole_diameter_mm']/2, 8, 'Y'))
    return o


def build_shell_speaker():
    s, m = P['detail_fit']['speaker'], P['speaker_mount'];d=mount_datums()
    b=source_build();tr=speaker_transform();upper=obj('Body_Upper')
    for n in ['Speaker', 'Speaker_Mount', 'Speaker_Lead', 'Speaker_Gasket']:
        remove_generated(n)
    sp=speaker_envelope('Speaker')
    finish_reference(sp, '福声FS4545DB0450-H25-R01 / 箱体45×45×25 / 4Ω5W',
                     'USER_SUPPLIED_DIMENSIONED_ENVELOPE', ['FUSHENG_FS4545_DRAWING','FUSHENG_FS4545_SPEC'], 'body', 'dark')
    sp['documented_mass_g']=s['mass_g'];sp['source_revision']='DrawingV0 / specificationA'
    sp['envelope_limit']=s['ear_profile_status']+' '+s['breather_status']+' '+s['lead_status']
    # The circular face is a material-only illustration: no invented cone depth
    # subtracts from the closed conservative package used in fit checking.
    sp.data.materials.clear();sp.data.materials.append(face_material())
    # Split coplanar front regions without changing the package volume.
    # Cylinder union/cut is deliberately not used to imply unknown diaphragm travel.
    sp['front_illustration']='Diameter36 documented; cone/dome depths and excursion unknown, envelope kept full.'
    relocate(sp,tr)

    gasket=ring('Speaker_Gasket',(0,m['gasket_thickness_mm']/2,0),m['gasket_outer_radius_mm'],
                m['gasket_inner_radius_mm'],m['gasket_thickness_mm'],'Y')
    finish(gasket,'PURCHASED_REFERENCE','喇叭前端试配泡棉密封圈 / 自裁软片','tire','body',False,
           note='Custom cut soft sheet, NOT supplied factory gasket; dimensions and compression trial only.')
    gasket['data_status']='ASSUMED';gasket['model_fidelity']='TRIAL_SOFT_SHEET';relocate(gasket,tr)
    seat=ring('integral_front_speaker_seat',(0,(m['gasket_thickness_mm']+m['seat_front_y_mm'])/2,0),
              m['seat_outer_radius_mm'],m['seat_inner_radius_mm'],m['seat_front_y_mm']-m['gasket_thickness_mm'],'Y')
    relocate(seat,tr);intersect(seat,b.body_outer('seat_spherical_outer_limit'));union(upper,seat)
    for sign in [-1,1]:
        x=sign*d['mount_abs_x'];y0=d['ear_front_y'];y1=m['boss_front_y_mm']
        # Broad short pads stay inside shell, without an external screw ear.
        boss=box('integral_vendor_ear_seat',(x,(y0+y1)/2,0),
                 (2*m['boss_half_width_mm'],y1-y0,2*m['boss_half_height_mm']))
        # The purchased square box must have clearance, not be reshaped to fit.
        boolean(boss,box('box_side_clear',(0,-s['depth_mm']/2,0),
                         (s['box_width_mm']+2*m['fit_clearance_mm'],s['depth_mm']+2*m['fit_clearance_mm'],s['box_height_mm']+2*m['fit_clearance_mm'])))
        relocate(boss,tr);intersect(boss,b.body_outer('boss_shell_outer_limit'));union(upper,boss)
        end=d['pilot_front_y'];start=d['ear_front_y']-.1
        pilot=cyl('blind_insert_pilot',(x,(start+end)/2,0),m['insert_pilot_diameter_mm']/2,end-start,'Y')
        relocate(pilot,tr);boolean(upper,pilot)
        bolt=cyl('Speaker_Screw_'+str(sign),(x,d['screw_head_base_y']+m['screw_length_mm']/2,0),
                  m['screw_diameter_mm']/2,m['screw_length_mm'],'Y')
        union(bolt,cyl('trial_pan_head',(x,d['screw_head_base_y']-m['screw_head_height_mm']/2,0),
                       m['screw_head_diameter_mm']/2,m['screw_head_height_mm'],'Y'))
        hardware(bolt,'喇叭原厂耳固定 / 试配M2.5×8盘头螺钉','body');relocate(bolt,tr)
        ins=ring('Speaker_Insert_'+str(sign),(x,(d['insert_back_y']+d['insert_front_y'])/2,0),
                 m['insert_outer_diameter_mm']/2,m['insert_inner_diameter_mm']/2,m['insert_length_mm'],'Y')
        hardware(ins,'喇叭壳内盲孔 / 试配M2.5热熔嵌件','body');relocate(ins,tr)
    # A clearance hole past the insert accepts the screw tip without opening
    # through the visible shell. Pilot/threads are trial, smooth envelopes.
    for sign in [-1,1]:
        start=d['insert_front_y']-.1;end=d['screw_tip_y']+.5
        if end>start:
            q=cyl('speaker_tip_clearance',(sign*d['mount_abs_x'],(start+end)/2,0),1.4,end-start,'Y')
            relocate(q,tr);boolean(upper,q)
    # The user drawing shows the lead exiting a side; exact exit is undimensioned.
    # Orient that side upward in the robot to keep the removable battery bay free.
    pts=[tr@Vector((0,-18,22.5)),tr@Vector((0,-18,27)),Vector((-28,34,153)),Vector((-35,24,146))]
    q=None
    for a,bb in zip(pts,pts[1:]):
        w=b.beam('speaker_wire_trial',a,bb,1)
        if q is None:q=w
        else:union(q,w)
    q.name=PREFIX+'Speaker_Lead';finish(q,'PLACEHOLDER','喇叭可断开服务线 / 出线位置待确认','copper','body',False,role='routing')
    b.contact('Speaker','Body_Upper','Two original ears rest on shell-integral blind seats; no frame connection')
    b.contact('Speaker','Speaker_Gasket','Trial soft gasket at front perimeter; excursion/seal unqualified')
    b.contact('Speaker_Gasket','Body_Upper','Nominal front seat at gasket thickness')
    upper['speaker_mount']='Direct vendor ears / two trialM2.5 screws; enclosure rear face open; no printed rear cup'
    save_json(ROOT/'reports/speaker_mount.json',{'revision':P['revision'],'model':s['model'],'source':s['source'],
        'nominal_box_xyz_mm':[45,25,45],'nominal_including_ears_xyz_mm':[60,25,45],
        'world_transform':list(map(list,tr)),'fasteners':['Speaker_Screw_-1','Speaker_Screw_1'],
        'structural_parent':'Body_Upper','load_frame_attachment':False,'mount_abs_x_mm':d['mount_abs_x'],
        'screw_head_base_local_y_mm':d['screw_head_base_y'],'fastener_trial':'M2.5x8, existing manufacturer ears and blind shell seats',
        'no_printed_back_cup':True,'retired_print_id':'Speaker_Mount',
        'diaphragm_clearance_nominal_mm':m['gasket_thickness_mm'],'acoustic_qualification':'NOT_TESTED',
        'sealing_and_tool_handles':'NOT_TESTED','limits':[s['ear_profile_status'],s['breather_status'],s['lead_status']]})

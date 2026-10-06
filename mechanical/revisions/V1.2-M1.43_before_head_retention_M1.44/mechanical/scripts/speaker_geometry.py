"""Drawing-based enclosed speaker and direct upper-shell attachment.

Local axes: +Y sound/front, ears along X, front face Y=0. All dimensions mm.
M1.37 SP3040 has documented box/pitch and explicitly estimated ear details.
No vendor mesh or physical metrology is claimed. Local +X is its long side.
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
    if height > 2*radius + .001:
        union(o, box('rounded_box_cross', (0, -depth/2, 0), (width, depth, height-2*radius)))
    for x in [-width/2+radius, width/2-radius]:
        for z in [-height/2+radius, height/2-radius]:
            union(o, cyl('rounded_box_corner', (x, -depth/2, z), radius, depth, 'Y'))
    return o


def face_material():
    """Material-only diaphragm illustration; conservative package stays solid."""
    s=P['detail_fit']['speaker']; obround=s.get('face_shape')=='OBROUND_ESTIMATE'
    mat=material('speaker_box',(.018,.022,.024),roughness=.55)
    nodes=mat.node_tree.nodes;links=mat.node_tree.links
    bsdf=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
    tex=nodes.new('ShaderNodeTexCoord');sep=nodes.new('ShaderNodeSeparateXYZ')
    links.new(tex.outputs['Generated'],sep.inputs[0])
    front=nodes.new('ShaderNodeMath');front.operation='GREATER_THAN';front.inputs[1].default_value=.999
    links.new(sep.outputs['Y'],front.inputs[0])
    mul=nodes.new('ShaderNodeVectorMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=(s['overall_ear_span_mm'],0,s['box_height_mm'])
    links.new(tex.outputs['Generated'],mul.inputs[0])
    sub=nodes.new('ShaderNodeVectorMath');sub.operation='SUBTRACT';sub.inputs[1].default_value=(s['overall_ear_span_mm']/2,0,s['box_height_mm']/2)
    links.new(mul.outputs[0],sub.inputs[0])
    dist_input=sub.outputs[0]
    if obround:
        xyz=nodes.new('ShaderNodeSeparateXYZ');links.new(dist_input,xyz.inputs[0])
        ab=nodes.new('ShaderNodeMath');ab.operation='ABSOLUTE';links.new(xyz.outputs['X'],ab.inputs[0])
        straight=nodes.new('ShaderNodeMath');straight.operation='SUBTRACT'
        straight.inputs[1].default_value=(s['diaphragm_outline_xz_mm'][0]-s['diaphragm_outline_xz_mm'][1])/2
        links.new(ab.outputs[0],straight.inputs[0])
        clamp=nodes.new('ShaderNodeMath');clamp.operation='MAXIMUM';clamp.inputs[1].default_value=0;links.new(straight.outputs[0],clamp.inputs[0])
        combine=nodes.new('ShaderNodeCombineXYZ');links.new(clamp.outputs[0],combine.inputs['X']);links.new(xyz.outputs['Z'],combine.inputs['Z']);dist_input=combine.outputs[0]
    length=nodes.new('ShaderNodeVectorMath');length.operation='LENGTH';links.new(dist_input,length.inputs[0])
    color=None
    radius=s['diaphragm_outline_xz_mm'][1]/2 if obround else s['diaphragm_outer_diameter_mm']/2
    for radius,c in [(radius,(.09,.095,.1,1)),(radius-1,(.01,.012,.013,1)),(radius-3,(.035,.04,.043,1)),(radius-7,(.012,.014,.016,1))]:
        less=nodes.new('ShaderNodeMath');less.operation='LESS_THAN';less.inputs[1].default_value=radius;links.new(length.outputs['Value'],less.inputs[0])
        mask=nodes.new('ShaderNodeMath');mask.operation='MULTIPLY';links.new(less.outputs[0],mask.inputs[0]);links.new(front.outputs[0],mask.inputs[1])
        mix=nodes.new('ShaderNodeMixRGB');links.new(mask.outputs[0],mix.inputs[0]);mix.inputs[1].default_value=(.018,.022,.024,1);mix.inputs[2].default_value=c
        if color:links.new(color,mix.inputs[1])
        color=mix.outputs[0]
    links.new(color,bsdf.inputs['Base Color'])
    return mat


def front_ring(name, y0, y1, outer, inner):
    """Simple obround seat/soft gasket; not an additional printed bracket."""
    o=rounded_box(name,*outer,y1-y0,outer[1]/2)
    cut=rounded_box('front_ring_open',*inner,y1-y0+2,inner[1]/2)
    cut.location.y+=1
    # The Boolean kernel caches construction solids in world coordinates.
    # Moving the cutter must invalidate that cache so it crosses BOTH faces.
    # Otherwise its stale front plane is coplanar and can leave zero-volume skins.
    SOLIDS.pop(cut.name,None);bpy.context.view_layer.update()
    boolean(o,cut);o.location.y+=y1
    bpy.context.view_layer.update()
    return o


def estimated_ear(sign, span, width, front, rear):
    """Flat root with two rounded outer corners, as the supplied front view."""
    s=P['detail_fit']['speaker'];r=s['ear_corner_radius_mm'];end=span/2
    root=s['box_width_mm']/2-.5;points=[(root,-width/2),(end-r,-width/2)]
    for k in range(1,13):
        a=-math.pi/2+k*math.pi/24;points.append((end-r+r*math.cos(a),-width/2+r+r*math.sin(a)))
    points.append((end,width/2-r))
    for k in range(1,13):
        a=k*math.pi/24;points.append((end-r+r*math.cos(a),width/2-r+r*math.sin(a)))
    points.append((root,width/2));n=len(points)
    verts=[(sign*x,y,z) for y in [front,rear] for x,z in points]
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    o=mesh('estimated_vendor_ear',verts,faces);recalc(o);return o


def speaker_envelope(name, worst_case=False):
    s = P['detail_fit']['speaker'];d = mount_datums()
    extra = s['box_xy_tolerance_mm'] if worst_case else 0
    depth = s['depth_mm'] + (s['depth_tolerance_mm'] if worst_case else 0)
    o = rounded_box(name, s['box_width_mm']+extra, s['box_height_mm']+extra,
                    depth, s['corner_radius_mm'])
    span = s['overall_ear_span_mm'] + (s['ear_span_tolerance_mm'] if worst_case else 0)
    half_body = s['box_width_mm']/2
    for sign in [-1, 1]:
        if s.get('ear_corner_radius_mm') is not None:
            ear=estimated_ear(sign,span,s['ear_width_mm']+extra,d['ear_front_y'],d['ear_rear_y'])
        else:
            ear = box('vendor_ear_envelope', (sign*(span/2+half_body-.2)/2,
                    (d['ear_front_y']+d['ear_rear_y'])/2, 0),
                   (span/2-half_body+.2, s['ear_thickness_mm'], s['ear_width_mm']+extra))
        union(o, ear)
        boolean(o, cyl('vendor_mount_hole', (sign*d['mount_abs_x'], (d['ear_front_y']+d['ear_rear_y'])/2, 0),
                       s['mount_hole_diameter_mm']/2, s['ear_thickness_mm']+2, 'Y'))
    return o


def build_shell_speaker():
    s, m = P['detail_fit']['speaker'], P['speaker_mount'];d=mount_datums()
    b=source_build();tr=speaker_transform();upper=obj('Body_Upper')
    for n in ['Speaker', 'Speaker_Mount', 'Speaker_Lead', 'Speaker_Gasket']:
        remove_generated(n)
    sp=speaker_envelope('Speaker')
    finish_reference(sp, s['model']+f" / {s['box_width_mm']}×{s['box_height_mm']}×{s['depth_mm']} / {s['impedance_ohm']}Ω{s['rated_power_W']}W",
                     'DIMENSIONED_ENVELOPE_WITH_APPROVED_ESTIMATES', s['source_ids'], 'body', 'dark')
    sp['data_status']='ASSUMED';sp['field_evidence']=json.dumps(s.get('field_evidence',{}),ensure_ascii=False)
    sp['interface_status']='Box/pitch from supplied PDF; unmarked ear/diaphragm geometry estimated with user approval. NOT measured; nominal hole clearance/tolerance not released.'
    if s['mass_g'] is not None:sp['documented_mass_g']=s['mass_g']
    sp['source_revision']=s['revision_specification'];sp['source_sha256']=P['speaker_update']['source_sha256']
    sp['envelope_limit']=s['ear_profile_status']+' '+s['breather_status']+' '+s['lead_status']
    # The circular face is a material-only illustration: no invented cone depth
    # subtracts from the closed conservative package used in fit checking.
    sp.data.materials.clear();sp.data.materials.append(face_material())
    sp.data.materials.append(MATS['unknown'])
    for poly in sp.data.polygons:
        if abs(sum(sp.data.vertices[i].co.x for i in poly.vertices)/len(poly.vertices))>s['box_width_mm']/2+.001:
            poly.material_index=1
    # Split coplanar front regions without changing the package volume.
    # Cylinder union/cut is deliberately not used to imply unknown diaphragm travel.
    sp['front_illustration']='Obround diaphragm from drawing proportions only; no invented cone depth or travel. Amber ears identify estimated details.'
    relocate(sp,tr)

    gasket=front_ring('Speaker_Gasket',0,m['gasket_thickness_mm'],m['gasket_outer_xz_mm'],m['gasket_inner_xz_mm'])
    finish(gasket,'PURCHASED_REFERENCE','喇叭前端试配泡棉密封圈 / 自裁软片','tire','body',False,
           note='Custom cut soft sheet, NOT supplied factory gasket; dimensions and compression trial only.')
    # A die-cut sheet has flat faces. Avoid interpolating their normals toward
    # the thin inner/outer walls; this changes display normals, never the cut.
    normals=[(0,0,0)]*len(gasket.data.loops)
    for face in gasket.data.polygons:
        face.use_smooth=False
        for k in face.loop_indices:normals[k]=face.normal[:]
    gasket.data.normals_split_custom_set(normals);gasket.data.update()
    gasket['data_status']='ASSUMED';gasket['model_fidelity']='TRIAL_SOFT_SHEET';relocate(gasket,tr)
    seat=front_ring('integral_front_speaker_seat',m['gasket_thickness_mm'],m['seat_front_y_mm'],m['seat_outer_xz_mm'],m['seat_inner_xz_mm'])
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
        hardware(bolt,'SP3040安装耳固定 / 试配M2×6盘头螺钉','body');relocate(bolt,tr)
        ins=ring('Speaker_Insert_'+str(sign),(x,(d['insert_back_y']+d['insert_front_y'])/2,0),
                 m['insert_outer_diameter_mm']/2,m['insert_inner_diameter_mm']/2,m['insert_length_mm'],'Y')
        hardware(ins,'喇叭壳内盲孔 / 试配M2热熔嵌件','body');relocate(ins,tr)
    # A clearance hole past the insert accepts the screw tip without opening
    # through the visible shell. Pilot/threads are trial, smooth envelopes.
    for sign in [-1,1]:
        start=d['insert_front_y']-.1;end=d['screw_tip_y']+.5
        if end>start:
            q=cyl('speaker_tip_clearance',(sign*d['mount_abs_x'],(start+end)/2,0),m['insert_inner_diameter_mm']/2,end-start,'Y')
            relocate(q,tr);boolean(upper,q)
    # The user drawing shows the lead exiting a side; exact exit is undimensioned.
    # Orient that side upward in the robot to keep the removable battery bay free.
    pts=[tr@Vector((0,-6.3,s['box_height_mm']/2)),tr@Vector((0,-6.3,s['box_height_mm']/2+5)),Vector((-28,34,153)),Vector((-35,24,146))]
    q=None
    for a,bb in zip(pts,pts[1:]):
        w=b.beam('speaker_wire_trial',a,bb,1)
        if q is None:q=w
        else:union(q,w)
    q.name=PREFIX+'Speaker_Lead';finish(q,'PLACEHOLDER','喇叭可断开服务线 / 出线位置待确认','copper','body',False,role='routing')
    b.contact('Speaker','Body_Upper','Two original ears rest on shell-integral blind seats; no frame connection')
    b.contact('Speaker','Speaker_Gasket','Trial soft gasket at front perimeter; excursion/seal unqualified')
    b.contact('Speaker_Gasket','Body_Upper','Nominal front seat at gasket thickness')
    upper['speaker_mount']='SP3040 direct ears / two trialM2x6 screws; ear geometry estimated; rear face open; no printed rear cup'
    save_json(ROOT/'reports/speaker_mount.json',{'revision':P['revision'],'model':s['model'],'source':s['source'],
        'nominal_box_xyz_mm':[s['box_width_mm'],s['depth_mm'],s['box_height_mm']],
        'nominal_including_ears_xyz_mm':[s['overall_ear_span_mm'],s['depth_mm'],s['box_height_mm']],
        'world_transform':list(map(list,tr)),'fasteners':['Speaker_Screw_-1','Speaker_Screw_1'],
        'structural_parent':'Body_Upper','load_frame_attachment':False,'mount_abs_x_mm':d['mount_abs_x'],
        'screw_head_base_local_y_mm':d['screw_head_base_y'],'fastener_trial':'M2x6, estimated manufacturer ears and blind shell seats; tolerance/zero radial hole clearance requires physical confirmation',
        'no_printed_back_cup':True,'retired_print_id':'Speaker_Mount',
        'diaphragm_clearance_nominal_mm':m['gasket_thickness_mm'],'acoustic_qualification':'NOT_TESTED',
        'sealing_and_tool_handles':'NOT_TESTED','limits':[s['ear_profile_status'],s['breather_status'],s['lead_status']]})

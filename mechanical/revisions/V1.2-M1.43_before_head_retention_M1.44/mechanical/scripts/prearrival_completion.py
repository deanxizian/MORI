"""M1.39 user-approved PA12, servo through-nuts and continuous camera aperture.

All design dimensions come from geometry.json. Native PCB files are read-only;
the proposed IMU outline is a handoff, not a fabricated replacement PCB.
"""
from common import *
from purchased_geometry import remove_generated
from monocoque_structure import obj,source_build
from optics_mount import camera_transform,camera_pupil,display_transform,apply_mount
from readiness_completion import paint_integral_rim

S=P.get('prearrival_completion',{})

def as_mesh(name,m):
    d=m.to_mesh64();o=mesh(name,d.vert_properties[:,:3].tolist(),d.tri_verts.tolist());SOLIDS[o.name]=m
    return o

def aperture_region():
    q=S['camera_aperture'];rot=np.array(camera_transform().to_3x3())@np.array([[1,0,0],[0,0,1],[0,-1,0]])
    return manifold.Manifold.cylinder(q['length_mm'],q['restore_radius_mm'],q['restore_radius_mm'],q['segments']).transform(np.c_[rot,np.array(camera_pupil())])

def ear_change_region():
    """Local permitted bore/pocket regions, for historical scope comparisons."""
    q=S['servo_ears'];rows=json.loads((ROOT/'reports/head_servo_geometry.json').read_text())['mounts'];out=manifold.Manifold()
    for row in rows:
        c=q['mounts'][row['id']];axis=Vector((0,0,1)) if row['axis']=='Z' else Vector((1,0,0));f=Vector(row['ear_top_point_mm'])
        bottom=f-axis*(c['screw_length_mm']+q['bore_bottom_extra_mm']+.02)
        tr=Matrix.Translation(bottom)@axis.to_track_quat('Z','Y').to_matrix().to_4x4()
        out+=manifold.Manifold.cylinder(c['screw_length_mm']+q['bore_bottom_extra_mm']+.54,q['nut_pocket_circumradius_mm']+.02,circular_segments=64).transform(np.array(tr)[:3,:])
    return out

def replace_ear_fasteners():
    q=S['servo_ears'];o=obj('Pitch_Yoke');rows=json.loads((ROOT/'reports/head_servo_geometry.json').read_text())['mounts'];result=[]
    for row in rows:
        name=row['id'];c=q['mounts'][name];p=np.array(row['seat_plane_point_mm']);f=np.array(row['ear_top_point_mm']);axis=np.array([0,0,1.]) if row['axis']=='Z' else np.array([1.,0,0])
        m=P['head_servo_detail']['mount']
        union(o,cyl('restore_old_ear_pilot',row['insert_center_mm'],m['insert_pilot_radius_mm']+q['pilot_restore_radial_overlap_mm'],m['insert_length_mm']+q['pilot_restore_length_overlap_mm'],row['axis'],n=64))
        bottom=p-axis*c['nut_bearing_from_seat_mm']
        if 'nut_bearing_z_from_head_mm' in c:bottom[2]=D['head_z']+c['nut_bearing_z_from_head_mm']
        length=c['screw_length_mm'];recess=c['recess_mm'];nutcentre=bottom-axis*q['nut_height_mm']/2
        boolean(o,cyl('M2_ear_through',f-axis*(length+q['bore_bottom_extra_mm']-.5)/2,q['clearance_radius_mm'],length+q['bore_bottom_extra_mm']+.5,row['axis'],n=64))
        if recess:boolean(o,ring('internal_nut_pocket',bottom-axis*(recess+.1)/2,q['nut_pocket_circumradius_mm'],.05,recess+.1,row['axis'],n=6))
        remove_generated(name+'_Screw');remove_generated(name+'_Insert')
        bolt=cyl(name+'_Screw',f-axis*length/2,q['screw_radius_mm'],length,row['axis'],n=48)
        union(bolt,cyl('M2_GB823_head',f+axis*q['head_height_mm']/2,q['head_radius_mm'],q['head_height_mm'],row['axis'],n=64))
        nut=ring(name+'_Nut',nutcentre,q['nut_AF_mm']/math.sqrt(3),q['nut_thread_radius_mm'],q['nut_height_mm'],row['axis'],n=6)
        boolean(nut,cyl('M2_round_thread_envelope',nutcentre,q['nut_thread_radius_mm'],q['nut_height_mm']+.2,row['axis'],n=64))
        for part,label in [(bolt,f'M2×{length}舵机穿栓 / GB823名义'),(nut,'M2六角螺母 / GB6170名义')]:
            finish(part,'PURCHASED_REFERENCE',label,'metal','yaw',False,note='User-approved through-bolt interface; source dimensioned nominal envelope. Selected supplier, actual thread engagement and strength require samples.')
            part['data_status']='ASSUMED';part['model_fidelity']='DRAWING_REFERENCE_ENVELOPE';part['source_dimensions']='GB823 M2 head3.5×1.4; GB6170M2 nutAF4×1.6'
        source_build().contact(name+'_Screw',name+'_Nut','M2 nominal thread envelope, not helical contact or torque qualification')
        source_build().contact(name+'_Nut','Pitch_Yoke','Metal nut bears on integral internal seat; install on detached yoke')
        result.append(dict(id=name,screw_length_mm=length,seat_point_mm=p.tolist(),ear_top_mm=f.tolist(),axis=row['axis'],nut_bearing_mm=bottom.tolist(),nut_center_mm=nutcentre.tolist(),recess_mm=recess,
            screw_thread_projection_beyond_nut_mm=float(np.dot(bottom-axis*q['nut_height_mm']-(f-axis*length),axis))))
    o['fastening']='Four M2 through bolts and metal nuts; three internal nut pockets, one long-post bolt. No extra printed part.'
    o['material_suggestion']='PA12 nylon; first structural prototype, print process and fits unvalidated'
    return result

def continuous_aperture():
    from validate import Solid
    bpy.context.view_layer.update()
    q=S['camera_aperture'];shell=obj('Head_Front');rot=np.array(camera_transform().to_3x3())@np.array([[1,0,0],[0,0,1],[0,-1,0]])
    tr=np.c_[rot,np.array(camera_pupil())];R=D['head_radius'];hz=D['head_z']
    patch=sphere('restore_camera_sphere',(0,0,hz),R);boolean(patch,sphere('camera_inner_skin',(0,0,hz),R-P['shell_thickness_mm']))
    intersect(patch,as_mesh('camera_local_patch',aperture_region()))
    boolean(patch,apply_mount(cyl('preserve_LCD_opening',(0,60,hz+P['display'].get('mask_z_from_head_mm',0)),P['display']['aperture_diameter_mm']/2,50,'Y'),display_transform()))
    collision=Solid(patch).m^Solid(obj('Display_PCB')).m
    if collision.volume()>1e-6:
        bb=np.array(collision.bounding_box());lo=bb[:3]-q['restored_skin_LCD_clearance_mm'];hi=bb[3:]+q['restored_skin_LCD_clearance_mm']
        boolean(patch,box('preserve_original_LCD_fit',(lo+hi)/2,hi-lo))
    union(shell,patch)
    kh=math.sqrt(2)*math.tan(math.radians(P['camera']['assumed_hfov_deg']/2));kv=math.sqrt(2)*math.tan(math.radians(P['camera']['assumed_vfov_deg']/2))
    points=[[math.cos(a)*(q['pupil_margin_mm']+kh*w),math.sin(a)*(q['pupil_margin_mm']+kv*w),w] for w in [0,q['length_mm']] for a in np.linspace(0,2*math.pi,q['segments'],endpoint=False)]
    cut=manifold.Manifold.hull_points(points).transform(tr)
    bezel=Solid(obj('Integrated_Face_Region')).m
    initial_bezel_overlap=max(0,(cut^bezel).volume())
    # Preserve the already-approved integral black rim. This clips only the
    # internal end of the flare where it meets that existing interface.
    cut=cut-bezel
    removed_bezel=max(0,(cut^bezel).volume())
    boolean(shell,as_mesh('continuous_elliptical_flare',cut));paint_integral_rim()
    shell['camera_aperture']='User-approved single elliptical conical flare on original spherical skin; lens and captive pocket unchanged'
    return dict(initial_flare_bezel_overlap_mm3=initial_bezel_overlap,protected_integral_bezel_mm3=removed_bezel,cone_slopes_uv=[kh,kv],pupil_margin_mm=q['pupil_margin_mm'])

def apply_prearrival_completion():
    if not S.get('enabled'):return
    retired=set(S['retired_ids'])
    source_build().CONTACTS[:]=[c for c in source_build().CONTACTS if c['a'] not in retired and c['b'] not in retired]
    ears=replace_ear_fasteners();camera=continuous_aperture()
    save_json(ROOT/'reports/prearrival_geometry.json',{'revision':P['revision'],'servo_ears':ears,'camera':camera,'printed_part_delta':0,'fastener_count_delta':0,'IMU':'User withdrew expansion: retain original20×16 native PCB and two existing mounts','material':'PA12 user-selected; physical strength and fits NOT_TESTED'})

def apply_print_material():
    if not S.get('enabled'):return
    for o in parts(True):
        if o.get('category')=='PRINTABLE':
            o['material_suggestion']='PA12 nylon / JLC3DP first structural prototype'
            o['selected_print_material']='PA12';o['print_process_recommendation']='MJF; supplier final process acceptance pending'
            o['physical_material_status']='NOT_TESTED';o['paint_note']='Warm-white cosmetic finish after dimensional/assembly verification; protect fits from paint.'

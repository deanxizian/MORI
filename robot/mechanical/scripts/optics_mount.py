"""Fixed optical mount transforms, separate from mechanical head pitch."""
from common import *
def display_transform():
    s=P.get('layout_cleanup',{});hz=D['head_z']
    if s.get('display_surface_mount')=='radial_on_mother_sphere':
        # A circle at radial distance r intersects a true sphere at this plane.
        # Keep flat source CAD unscaled; align the mask FRONT rim, not its centre.
        plane=math.sqrt(D['head_radius']**2-(P['display']['mask_outer_diameter_mm']/2)**2)
        shift=plane-(D['face_y']+.5)
        return Matrix.Translation((0,0,hz))@Matrix.Rotation(math.radians(s['display_mount_pitch_deg']),4,'X')@Matrix.Translation((0,shift,-hz))
    c=Vector((0,P['display']['vendor_front_y_from_head_mm'],hz+P['display']['z_from_head_mm']))
    return Matrix.Translation((0,s.get('display_translation_y_mm',0),0))@Matrix.Translation(c)@Matrix.Rotation(math.radians(s.get('display_mount_pitch_deg',0)),4,'X')@Matrix.Translation(-c)
def camera_transform():
    s=P.get('layout_cleanup',{});c=Vector(P['camera']['pupil_from_head_mm'])+Vector((0,0,D['head_z']))
    return Matrix.Translation(c)@Matrix.Rotation(math.radians(s.get('camera_mount_pitch_deg',0)),4,'X')@Matrix.Translation(-c)
def camera_pupil():
    """Physical reconstructed module datum; the shell/window datum stays fixed."""
    c=Vector(P['camera']['pupil_from_head_mm'])+Vector((0,0,D['head_z']))
    s=P.get('assembly_completion',{})
    if s.get('enabled'):
        c-=camera_transform().to_3x3()@Vector((0,s['camera'].get('optical_recess_mm',0),0))
    return c
def apply_mount(o,tr):
    o.matrix_world=tr@o.matrix_world;SOLIDS.pop(o.name,None);bpy.context.view_layer.update();return o

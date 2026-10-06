"""Fixed optical mount transforms, separate from mechanical head pitch."""
from common import *
def display_transform():
    s=P.get('layout_cleanup',{});c=Vector((0,P['display']['vendor_front_y_from_head_mm'],D['head_z']+P['display']['z_from_head_mm']))
    return Matrix.Translation((0,s.get('display_translation_y_mm',0),0))@Matrix.Translation(c)@Matrix.Rotation(math.radians(s.get('display_mount_pitch_deg',0)),4,'X')@Matrix.Translation(-c)
def camera_transform():
    s=P.get('layout_cleanup',{});c=Vector(P['camera']['pupil_from_head_mm'])+Vector((0,0,D['head_z']))
    return Matrix.Translation(c)@Matrix.Rotation(math.radians(s.get('camera_mount_pitch_deg',0)),4,'X')@Matrix.Translation(-c)
def apply_mount(o,tr):
    o.matrix_world=tr@o.matrix_world;SOLIDS.pop(o.name,None);bpy.context.view_layer.update();return o

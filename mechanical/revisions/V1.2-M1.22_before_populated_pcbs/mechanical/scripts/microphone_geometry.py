"""Nominal photo-registered mic positions and the existing open acoustic path.

These coordinates are design/inspection aids, not measured MEMS port geometry.
"""
from common import P, D, Vector


def microphone_paths():
    s=P['detail_fit']['mic_photo_estimate'];q=P['microphone_acoustics']
    _,cy,cz=P['layout']['cam_board_center_from_head_mm'];cz+=D['head_z']
    rows=[]
    for side,sign in [('L',-1),('R',1)]:
        x=sign*s['center_x_mm'];z=cz+s['z_from_board_center_mm']
        package=Vector((x,cy+s['package_y_from_board_center_mm'],z))
        port=Vector((x,cy+s['port_y_from_board_center_mm'],z+s['port_z_from_package_center_mm']))
        start=port+Vector((0,q['probe_start_from_mic_port_y_mm'],0))
        inner=Vector((sign*q['shell_port_abs_x_mm'],q['inner_approach_y_mm'],D['head_z']+q['shell_port_z_from_head_mm']))
        outside=Vector((inner.x,q['shell_port_y_mm']-q['shell_port_cut_length_mm']/2,inner.z))
        rows.append({'side':side,'package':package,'port':port,'start':start,'inner':inner,'outside':outside})
    return rows

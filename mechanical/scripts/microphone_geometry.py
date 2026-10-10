"""Nominal photo-registered mic positions and the existing open acoustic path.

These coordinates are design/inspection aids, not measured MEMS port geometry.
"""
from common import P, D, Vector


def microphone_paths(installed=False):
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
    if installed and P.get('cam_orientation',{}).get('enabled'):
        from cam_orientation import transform
        tr=transform(); original={row['side']:dict(row) for row in rows}
        for row in rows:
            for key in ['package','port','start']:
                point=row[key];row[key]=Vector(tuple(sum(tr[i,j]*point[j] for j in range(3))+tr[i,3] for i in range(3)))
            # These are open-air diagnostic curves only; no ducts/holes are made.
            probe=P['cam_orientation']['air_probes'][row['side']]
            dst=original[probe['shell_port']]; y=probe['intermediate_y_mm']
            fraction=(y-dst['start'].y)/(dst['inner'].y-dst['start'].y)
            approach=dst['start']+fraction*(dst['inner']-dst['start'])
            row['probe_points']=[row['start'],Vector((row['start'].x,y,row['start'].z)),approach,dst['inner'],dst['outside']]
            row['inner']=dst['inner'];row['outside']=dst['outside']
    return rows

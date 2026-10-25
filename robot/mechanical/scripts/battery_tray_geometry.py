"""Derived removable-tray dimensions; the shared JSON is the editable source."""
from common import P,battery_z_mm


def tray_datums():
    q=P['battery_tray'];s=P['structure']['simple_modules'];r=P['battery_retention']
    inner=s['side_plate_abs_x_mm']-s['side_plate_thickness_mm']/2
    outer=s['side_plate_abs_x_mm']+s['side_plate_thickness_mm']/2
    half=inner-q['side_slide_clearance_mm']
    if half<=q['rail_inner_half_width_mm'] or q['side_slide_clearance_mm']<=0:
        raise ValueError('Battery tray needs positive side-wall width and sliding clearance')
    if s['side_plate_thickness_mm']-r['head_pocket_depth_mm']<r['minimum_head_backing_mm']:
        raise ValueError('Side plate is too thin behind battery screw recess')
    floor=battery_z_mm(q['floor_center_from_battery_bottom_mm'])
    head_seat=outer-r['head_pocket_depth_mm']
    return {'half_width':half,'width':2*half,'frame_inner':inner,'frame_outer':outer,
            'floor_center':floor,'floor_bottom':floor-q['floor_thickness_mm']/2,
            'floor_top':floor+q['floor_thickness_mm']/2,
            'rail_width':half-q['rail_inner_half_width_mm'],
            'rail_center':(half+q['rail_inner_half_width_mm'])/2,
            'retainer_z':battery_z_mm(q['retainer_z_from_battery_bottom_mm']),
            'head_seat':head_seat,'screw_center':head_seat-r['screw_length_mm']/2,
            'insert_center':half-r['insert_outer_inset_mm']-r['insert_length_mm']/2}

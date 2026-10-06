"""M1.15: two flush underside joints, within the existing yaw bridge legs."""
from common import *
from structural_simplification import hardware

S=P.get('yaw_bridge_mount',{})

def sites():
    b=P['belly_relayout']
    x=b['yaw_bridge_half_width_mm']-b['yaw_bridge_leg_thickness_mm']/2
    y=b['yaw_bridge_depth_mm']/2-S['bolt_y_edge_margin_mm']
    return [(sign,sign*x,-y) for sign in [-1,1]]

def datums():
    top=P['layout']['deck_z_mm']+P['layout']['deck_thickness_mm']/2
    bottom=top-P['layout']['deck_thickness_mm']
    return top,bottom,bottom+S['head_recess_depth_mm']

def bridge_joints(base):
    top,bottom,head=datums();joints=[]
    for sign,x,y in sites():
        boolean(base,cyl('blind_insert_pilot',(x,y,top+(S['insert_pilot_depth_mm']-.2)/2),S['insert_pilot_diameter_mm']/2,S['insert_pilot_depth_mm']+.2))
        boolean(base,cyl('blind_screw_tip_clear',(x,y,top+(S['blind_clearance_depth_mm']-.2)/2),S['screw_clearance_diameter_mm']/2,S['blind_clearance_depth_mm']+.2))
        iz=top+S['insert_inset_from_foot_mm']+S['insert_length_mm']/2
        insert=ring('Yaw_Base_'+str(sign)+'_Insert',(x,y,iz),S['insert_outer_diameter_mm']/2,S['insert_inner_diameter_model_mm']/2,S['insert_length_mm'])
        hardware(insert,'承重桥脚M2盲孔嵌件 / 试配')
        insert['interface_status']='M2 heat-set insert nominal envelope; supplier OD, length and hole compensation require a coupon'
        screw=cyl('Yaw_Base_'+str(sign)+'_Screw',(x,y,head+S['screw_length_mm']/2),S['screw_shank_diameter_model_mm']/2,S['screw_length_mm'])
        union(screw,cyl('recessed_M2_head',(x,y,head-S['head_height_mm']/2),S['head_diameter_mm']/2,S['head_height_mm']))
        hardware(screw,'板底向上M2×8 / 承重桥固定')
        joints.append({'id':'Yaw_Base_'+str(sign),'axis':'Z','xy_mm':[x,y],'head_base_mm':head,'head_height_mm':S['head_height_mm'],'access_direction':'-Z','group':'body','upper':'Yaw_Base','lower':'Load_Frame','prerequisite_removed':['Battery','Battery_Tray'],'prerequisite_removed_prefixes':['Battery_Retainer'],'fastener_type':'M2 screw into blind heat-set insert','screw_length_mm':S['screw_length_mm']})
    base['mounting_note']='Straight exterior side faces and feet; recessed underside fasteners. No projecting ear or outside vertical screwdriver groove.'
    return joints

def deck_holes(deck):
    top,bottom,head=datums()
    for sign,x,y in sites():
        boolean(deck,cyl('underside_bridge_M2_clear',(x,y,(top+bottom)/2),S['screw_clearance_diameter_mm']/2,top-bottom+1))
        boolean(deck,cyl('underside_bridge_head_recess',(x,y,(bottom-.2+head)/2),S['head_recess_diameter_mm']/2,head-bottom+.2))

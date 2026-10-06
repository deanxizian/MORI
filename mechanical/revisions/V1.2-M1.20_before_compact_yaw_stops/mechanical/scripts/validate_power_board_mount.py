"""Actual local seat, screw access and PCB removal checks; no strength claim."""
from common import *
from power_board_mount import mount_sites


def validate_power_board_mount(solids,Solid,iv,check):
    bay=P['layout_cleanup']['power_bay'];s=bay['local_mount'];z=bay['pcb_bottom_z_mm']
    deck=solids['Load_Frame'];board=solids['Power_Module'];rows=[]
    decktop=P['layout']['deck_z_mm']+P['layout']['deck_thickness_mm']/2
    native=mount_sites()
    # These are the actual objects present during the stated bench sequence.
    target_names=['Load_Frame','Power_Module','MCU_Carrier','MCU_Motion','Body_IMU','Drive_Bridge','Motor_Retainer','Drive_Motor_L','Drive_Motor_R']
    target_names += [n for n in solids if n.startswith(('Carrier_','IMU_','Power_Board_'))]
    for site in native:
        x,y=site['xy_mm'];rinner=1.7 if site['fastened'] else 1.2
        outer=manifold.Manifold.cylinder(.2,2.6,2.6,96,True).translate([x,y,z-.1])
        inner=manifold.Manifold.cylinder(.4,rinner,rinner,96,True).translate([x,y,z-.1])
        annulus=outer-inner
        missing=max(0,(annulus-deck.m).volume())
        row={**site,'support_missing_mm3':missing,'tool_obstacles':[],'insertion_obstacles':[]}
        if site['fastened']:
            name='Power_Board_'+site['ref']+'_Screw';a=solids[name];screw_xy=(a.lo+a.hi)[:2]/2
            row['screw_axis_error_mm']=float(np.max(np.abs(screw_xy-np.array([x,y]))))
            row['insert_engagement_mm']=min(float(a.hi[2]),z-s['insert_top_inset_mm'])-max(float(a.lo[2]),z-s['insert_top_inset_mm']-s['insert_length_mm'])
            tool=cyl('power_driver_shaft',(x,y,float(a.hi[2])+15.2),2.1,30);ts=Solid(tool)
            for n in target_names:
                if n==name:continue
                v=iv(ts,solids[n])
                if v>.01:row['tool_obstacles'].append({'part':n,'volume_mm3':v})
            bpy.data.objects.remove(tool,do_unlink=True)
            for step in range(26):
                moved=Solid(a.o,a,Matrix.Translation((0,0,step)))
                for n in target_names:
                    if n==name:continue
                    v=iv(moved,solids[n])
                    if v>.01:row['insertion_obstacles'].append({'step_mm':step,'part':n,'volume_mm3':v})
        rows.append(row)
    # Long former rail midsections must now be clear above the unchanged deck.
    old_rail_material=[]
    for sign in [-1,1]:
        probe=manifold.Manifold.cube([1,30,4.2],True).translate([sign*40,3,117.25])
        old_rail_material.append(max(0,(deck.m^probe).volume()))
    removal=[]
    obstacles=[n for n in target_names if n!='Power_Module' and not(n.startswith('Power_Board_') and n.endswith('_Screw'))]
    for step in range(0,41,2):
        moved=Solid(board.o,board,Matrix.Translation((0,0,step)))
        for n in obstacles:
            vol=iv(moved,solids[n])
            if vol>.01:removal.append({'travel_mm':step,'part':n,'volume_mm3':vol})
    good=all(r['support_missing_mm3']<.001 and not r['tool_obstacles'] and not r['insertion_obstacles'] and r.get('screw_axis_error_mm',0)<.01 and r.get('insert_engagement_mm',4)>=3 for r in rows) and max(old_rail_material)<.001 and not removal
    data={'revision':P['revision'],'status':'PASS' if good else 'FAIL','sites':rows,
          'old_rail_midsection_material_mm3':old_rail_material,'PCB_lift_failures':removal,
          'seat_height_mm':z-decktop,'component_underside_gap_mm':z-bay['component_below_mm']-decktop,
          'nominal_insert_side_wall_mm':(s['support_diameter_mm']-s['pilot_diameter_mm'])/2,
          'method':'Actual closed triangle solids; seat bearing annuli0.2mm deep; M2 screw lift25mm step1; driver shaft diameter4.2 x30; PCB lift40mm step2; old rail middle-volume probes.',
          'prerequisites':'Install board and screws BEFORE fixed yaw bridge/head. For service remove upper shell/speaker and bridge/head; disconnect leads and remove two board screws.',
          'limits':['Power_Module is a capacity envelope with PROPOSED local component keepouts, not verified populated hardware.','P4 native hole coordinates only; P5 in progress. Top/underside keepouts, plugs and leads require hardware-owner review.','Two diagonal screw retention and nominal1.2mm insert wall are unqualified for vibration/creep/pullout; print coupon and real board required.','Finite samples only; hand/driver handle and real cable movement NOT_TESTED.']}
    save_json(ROOT/'reports/power_board_mount_validation.json',data)
    check('short_power_board_mounts',data['status'],'取消两条长托边，四个一体矮座与对角双螺钉；板底间隙及规定台面装配路径',data,data['method'])

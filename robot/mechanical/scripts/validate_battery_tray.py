"""Wide tray, flat cheeks and actual bottom-bearing checks on generated solids."""
from common import *
from battery_tray_geometry import tray_datums


def validate_battery_tray(solids,check):
    td=tray_datums();q=P['battery_tray'];frame=solids['Load_Frame'];tray=solids['Battery_Tray']
    flat=[];gaps=[];support=[]
    for sign in [-1,1]:
        for y in [-16,-8,0,8,16]:
            for z in [75,84.5,90,100]:
                hits=frame.m.ray_cast([0,y,z],[sign*60,y,z])
                x=abs(float(hits[0].position[0])) if hits else None
                flat.append({'side':sign,'y_mm':y,'z_mm':z,'inner_x_abs_mm':x})
        for y in [-20,-12,12,20]:
            for z in [76,82]:
                fh=frame.m.ray_cast([0,y,z],[sign*60,y,z]);th=tray.m.ray_cast([sign*60,y,z],[0,y,z])
                gap=abs(float(fh[0].position[0]))-abs(float(th[0].position[0])) if fh and th else None
                gaps.append({'side':sign,'y_mm':y,'z_mm':z,'gap_mm':gap})
        for x in [41,43.5,46]:
            for y in [-18,-12,0,12,18]:
                hits=frame.m.ray_cast([sign*x,y,td['floor_bottom']+.1],[sign*x,y,td['floor_bottom']-5])
                seat=float(hits[0].position[2]) if hits else None
                support.append({'side':sign,'x_mm':sign*x,'y_mm':y,'seat_z_mm':seat,'vertical_gap_mm':None if seat is None else float(tray.lo[2])-seat})
    # Press down0.1mm solely as a contact-area probe, never an assembly transform.
    contact=(tray.m.translate([0,0,-.1])^frame.m)
    areas=[]
    for sign in [-1,1]:
        region=manifold.Manifold.cube([100,200,200],True).translate([sign*50,0,100])
        areas.append(float((contact^region).volume())/.1)
    ok=(abs(float(tray.hi[0]-tray.lo[0])-td['width'])<.01
        and all(r['inner_x_abs_mm'] is not None and abs(r['inner_x_abs_mm']-td['frame_inner'])<.01 for r in flat)
        and all(r['gap_mm'] is not None and abs(r['gap_mm']-q['side_slide_clearance_mm'])<.01 for r in gaps)
        and all(r['vertical_gap_mm'] is not None and abs(r['vertical_gap_mm'])<.01 for r in support)
        and min(areas)>200)
    result={'revision':P['revision'],'status':'PASS' if ok else 'FAIL','width_before_mm':90,
            'width_after_mm':float(tray.hi[0]-tray.lo[0]),'side_clearance_mm':q['side_slide_clearance_mm'],
            'inside_battery_channel_mm':2*q['rail_inner_half_width_mm'],
            'frame_side_thickness_mm':P['structure']['simple_modules']['side_plate_thickness_mm'],
            'flat_inner_faces':flat,'actual_slide_gaps':gaps,'bearing_plane_samples':support,
            'equivalent_bearing_area_each_side_mm2':areas,'new_parts':0,'new_fasteners':0,
            'method':'40 actual-solid cheek rays away from bores;16 tray/frame side gap ray pairs;30 downward bearing-plane rays;0.1mm downward diagnostic overlap divided by0.1 estimates nominal flat contact area.',
            'load_path':'Battery/pad -> tray floor -> existing raised lower shelves -> drive frame. Two lateralM2 screws retain extraction; no inward local retention land.',
            'related_checks':['battery_retention_closed_edges','battery_extraction','module_screwdriver_access','static_rigid_solids'],
            'limits':'Nominal candidate surfaces, no preload/deflection/strength model.0.3mm trial slides, inserts and actual pack/strap fit require printing/measurement. The full report covers extraction/tool paths; no continuous-space proof.'}
    save_json(ROOT/'reports/battery_tray_fit.json',result)
    check('wide_battery_tray_flat_sides',result['status'],'加宽托盘配合平侧板，取消局部凸块；底部实际承托与抽取间隙',result,result['method'])

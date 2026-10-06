"""Keep the screened outer/upper geometry and lift only the lower R8 start."""
from pathlib import Path
import sys,json,math
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from native_context import *
ctx=Context();rows=[];selected=[];saved={}
R=8.;radius=37.6;upper_z=160.;ez=np.array([0.,0.,1.])
for sector in [45,135,225,315]:
    found=False
    for shift in [0.,-2.5,2.5,-5.,5.,-7.5,7.5,-10.,10.,-15.,15.]:
      angle=sector+shift
      er=np.array([math.cos(math.radians(angle)),math.sin(math.radians(angle)),0.])
      # The lower original start was individually clear but blocked its
      # upstream descent at J4. Prefer the higher unchanged-part corridors.
      for lower_z in [140.,141.,139.,138.]:
        ts=np.linspace(0,math.pi/2,101)
        lower=np.array([er*(radius-R+R*math.sin(t))+ez*(lower_z+R*(1-math.cos(t))) for t in ts])
        upper=np.array([er*(radius-R*(1-math.cos(t)))+ez*(upper_z+R*math.sin(t)) for t in ts])
        vertical=np.linspace(lower[-1],upper[0],math.ceil((upper_z-lower_z-R)/.15)+1)
        points=np.vstack([lower,vertical[1:-1],upper])
        error=R*(1-math.cos(math.pi/400));hit=ctx.clear(points,error)
        row=dict(sector_deg=sector,angle_deg=angle,outer_radius_mm=radius,lower_z_mm=lower_z,upper_bend_start_z_mm=upper_z,
                 radius_mm=R,error_bound_mm=error,status='BLOCKED' if hit else 'PASS',failure=hit,
                 analytic_length_mm=R*math.pi+upper_z-lower_z-R)
        rows.append(row)
        if hit is None:
            row['curve_key']=str(angle);saved[str(angle)]=points;selected.append(row);found=True;break
      if found:break
    print('NECK_LOWER_START',sector,rows[-1],flush=True)
np.savez_compressed(HERE/'selected_necks.npz',**saved)
result=dict(status='PASS' if len(selected)==4 else 'BLOCKED',scope='Local neck curves with all main solids, plugs and fourteen wire allocations',
    **ctx.evidence(),script_sha256=sha(__file__),trials=rows,selected=selected,
    main_applied=False,whole_harness='BLOCKED',new_head_pose_check='NOT_TESTED',body_connection='NOT_TESTED')
ctx.assert_unchanged();(HERE/'selected_necks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('SELECT_NECKS',result['status'],len(selected),flush=True)

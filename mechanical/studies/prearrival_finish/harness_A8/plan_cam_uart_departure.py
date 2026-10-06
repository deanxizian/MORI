"""Find a bend-respecting four-wire departure from the conditional CAM mate.

This is only the pitch-fixed end, not a complete yaw-to-pitch service loop.
Actual CAM supplier, pin view and crimp retention remain unresolved.
"""
from pathlib import Path
LEAD_SCRIPT=Path(__file__).resolve();LEAD_DIR=LEAD_SCRIPT.parent
LEAD_HELPER=LEAD_DIR/'check_cam_uart_mating_allocation.py';__file__=str(LEAD_HELPER)
exec(compile(LEAD_HELPER.read_text().split('\nrows=[];minimum_noncontact_gap',1)[0],str(LEAD_HELPER),'exec'),globals())
__file__=str(LEAD_SCRIPT);START=time.time()
from mathutils.kdtree import KDTree
motion_helper=LEAD_DIR/'check_body_prefix_motion.py'
exec(compile('def check_one'+motion_helper.read_text().split('def check_one',1)[1].split('\nfor yaw in yaws:',1)[0],str(motion_helper),'exec'),globals())

ob=[]
for name,group,m in reference_sources:
    a=m.to_mesh64();b=np.array(m.bounding_box())
    ob.append((name,group,m,b[:3],b[3:],BVHTree.FromPolygons(a.vert_properties[:,:3],a.tri_verts.tolist(),all_triangles=True)))
def line(a,b):
    return np.linspace(a,b,max(1,math.ceil(np.linalg.norm(b-a)/.1))+1)
def make_case(direction,R,extension):
    paths=[];rad=[];length=[];errors=[]
    for i,e in enumerate(slots):
        r=R+i if direction=='left' else R
        c=e+np.array([0,0,-5.]);t=np.linspace(0,math.pi/2,257)
        out=np.array([-1.,0,0]) if direction=='left' else np.array([0,1. if direction=='forward' else -1.,0])
        p=c+r*(1-np.cos(t))[:,None]*out+np.array([0,0,-1.])*r*np.sin(t)[:,None]
        end=p[-1]+out*extension
        paths.append(np.vstack([line(e,c)[:-1],p[:-1],line(p[-1],end)]))
        errors.append(float(r*(1-math.cos(math.pi/1024))))
        rad.append(r);length.append(float(5+math.pi*r/2+extension))
    return paths,rad,length,errors
def check_paths(paths,errors,full=False):
    # Co-moving parts are tested once; yaw-only obstacles require pitch poses;
    # body parts require all130 relative poses. No transform of equal frames.
    for i,(points,error) in enumerate(zip(paths,errors)):
        for name,group,m,lo,hi,tree in ob:
            poses=[(0,0)] if not full or group=='pitch' else ([(0,p) for p in range(-20,26,5)] if group=='yaw' else [(y,p) for y in range(-60,61,10) for p in range(-20,26,5)])
            for yaw,pitch in poses:
                if group=='pitch':p=points
                else:
                    tr=np.asarray(rigidtr(0 if group=='yaw' else yaw,pitch))
                    p=points@tr[:3,:3].T+tr[:3,3]
                hit=check_one(p,error,lo,hi,m,tree)
                if hit:return {'slot_index':i,'obstacle':name,'yaw_deg':yaw,'pitch_deg':pitch,**hit}
    return None
def pair_gap(paths,errors):
    fine=[];trees2=[]
    for points in paths:
        p=np.vstack([np.linspace(a,b,max(1,math.ceil(np.linalg.norm(b-a)/.01))+1)[:-1] for a,b in zip(points,points[1:])]+[points[-1:]])
        kd=KDTree(len(p))
        for j,pt in enumerate(p):kd.insert(Vector(pt),j)
        kd.balance();fine.append(p);trees2.append(kd)
    minimum=math.inf
    for i,j in itertools.combinations(range(4),2):
        d=min(float(trees2[j].find(Vector(p))[2]) for p in fine[i])
        minimum=min(minimum,d-.01-errors[i]-errors[j]-OD-1e-4)
    return minimum

trials=[];selected=[];stored={}
for direction in ['back','left','forward']:
    winner=None
    for R,extension in itertools.product([7.,8.,10.],[4.,8.,12.]):
        paths,radii,lengths,errors=make_case(direction,R,extension)
        hit=check_paths(paths,errors)
        row={'direction':direction,'base_radius_mm':R,'extension_mm':extension,'zero_pose':'PASS' if hit is None else 'BLOCKED','hit':hit}
        if hit is None:
            hit=check_paths(paths,errors,True);row.update(full130_relative_poses='PASS' if hit is None else 'BLOCKED',hit=hit)
        if hit is None:
            gap=pair_gap(paths,errors);row['pair_surface_gap_bound_mm']=gap
            if gap<.3:hit={'reason':'four_wire_gap','gap_bound_mm':gap};row['hit']=hit
        row['status']='PASS' if hit is None else 'BLOCKED';trials.append(row)
        if hit is None:
            winner={**row,'arc_radii_mm':radii,'analytic_partial_lengths_mm':lengths,'curve_error_bounds_mm':errors,
                    'endpoints_mm':[p[-1].tolist() for p in paths],'scope':'CAM mating datum and pitch-fixed departure only'}
            for i,p in enumerate(paths):stored[f'{direction}_slot{i}']=p
            selected.append(winner);break
    print('CAM_LEAD_DIRECTION',direction,'PASS' if winner else 'BLOCKED',round(time.time()-START,2),flush=True)

np.savez_compressed(OUT/'departure_curves.npz',**stored)
result={'status':'PASS' if selected else 'BLOCKED','scope':'Conditional pitch-fixed CAM end only; no yaw-pitch flexible segment or final cut lengths',
    'source_main_sha256':source_hash,'source_script_sha256':sha(LEAD_SCRIPT),'source_helper_sha256':sha(LEAD_HELPER),
    'source_mating_allocation_sha256':sha(OUT/'mating_allocation.json'),
    'source_motion_checker_sha256':sha(motion_helper),'source_candidate_sha256':sha(candidate/'candidate.blend'),
    'source_curves_sha256':sha(OUT/'departure_curves.npz'),'required_bend_radius_mm':REQUIRED_R,'wire_OD_mm':OD,
    'head_pose_set':{'yaw_deg':list(range(-60,61,10)),'pitch_deg':list(range(-20,26,5))},
    'selected':selected,'trials':trials,'minimum_surface_gap_required_mm':.3,
    'pin_order':'No physical pin-number assertion; all four geometric slots included',
    'source_objects_or_components_checked':len(ob),'other4_yaw_UART_segments':'NOT_TESTED',
    'photo_uncertainty_and_actual_mating':'NOT_TESTED','retention':'NOT_TESTED','continuous_head_motion':'NOT_TESTED',
    'yaw_pitch_service_loop':'NOT_TESTED','whole_harness':'BLOCKED','manufacturing_release':False,
    'main_applied':False,'elapsed_s':time.time()-START}
(OUT/'departure_screen.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('CAM_DEPARTURE_DONE',result['status'],len(selected),'families',flush=True)

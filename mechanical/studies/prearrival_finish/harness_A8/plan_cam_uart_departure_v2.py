"""Revisit CAM end radii after the two earlier families crossed the yaw wires."""
from pathlib import Path
V2_SCRIPT=Path(__file__).resolve();V2_DIR=V2_SCRIPT.parent
V2_HELPER=V2_DIR/'plan_cam_uart_departure.py';__file__=str(V2_HELPER)
exec(compile(V2_HELPER.read_text().split('\ntrials=[];selected=[];stored={}',1)[0],str(V2_HELPER),'exec'),globals())
__file__=str(V2_SCRIPT);OUT=V2_DIR/'cam_pitch_port/departure_v2';OUT.mkdir(exist_ok=True);V2_START=time.time()
body=np.load(V2_DIR/'body_prefix_v2/body_to_yaw_curves.npz')
body_meta=json.loads((V2_DIR/'body_prefix_v2/body_to_yaw_motion.json').read_text())
body_trees={}
for yaw in range(-60,61,10):
    for pin in range(1,5):
        p=body[f'pin{pin}_yaw{yaw}'];fine=np.vstack([np.linspace(a,b,max(1,math.ceil(np.linalg.norm(b-a)/.02))+1)[:-1] for a,b in zip(p,p[1:])]+[p[-1:]])
        kd=KDTree(len(fine))
        for j,q in enumerate(fine):kd.insert(Vector(q),j)
        kd.balance();err=next(r['curve_error_bound_mm'] for r in body_meta['rows'] if r['pin']==pin and r['yaw_deg']==yaw)
        body_trees[(yaw,pin)]=(kd,err,float(np.linalg.norm(np.diff(fine,axis=0),axis=1).max()))
def make_v2(angle,R,reverse):
    paths=[];radii=[];lengths=[];errors=[]
    a=math.radians(angle);out=np.array([-math.cos(a),math.sin(a),0.]);t=np.linspace(0,math.pi/2,257)
    for i,e in enumerate(slots):
        r=R+math.cos(a)*((3-i) if reverse else i)
        c=e+np.array([0,0,-5.]);p=c+r*(1-np.cos(t))[:,None]*out+np.array([0,0,-1.])*r*np.sin(t)[:,None]
        paths.append(np.vstack([line(e,c)[:-1],p[:-1],line(p[-1],p[-1]+4*out)]))
        radii.append(r);lengths.append(float(9+math.pi*r/2));errors.append(float(r*(1-math.cos(math.pi/1024))))
    return paths,radii,lengths,errors
def body_clear(paths,errors):
    worst=None;minimum=math.inf
    samples=[]
    for p in paths:
        fine=np.vstack([np.linspace(a,b,max(1,math.ceil(np.linalg.norm(b-a)/.02))+1)[:-1] for a,b in zip(p,p[1:])]+[p[-1:]])
        samples.append((fine,float(np.linalg.norm(np.diff(fine,axis=0),axis=1).max())))
    for yaw in range(-60,61,10):
        for pitch in range(-20,26,5):
            tr=np.asarray(rigidtr(yaw,pitch))
            for i,(p,hs) in enumerate(samples):
                points=p@tr[:3,:3].T+tr[:3,3]
                for pin in range(1,5):
                    kd,err,bs=body_trees[(yaw,pin)]
                    distance=min(float(kd.find(Vector(q))[2]) for q in points)
                    gap=distance-(hs+bs)/2-errors[i]-err-OD-1e-4
                    if gap<minimum:minimum=gap;worst={'head_slot':i,'body_pin':pin,'yaw_deg':yaw,'pitch_deg':pitch,'surface_gap_bound_mm':gap}
                    if gap<.3:return {'status':'BLOCKED','worst':worst,'minimum_gap_bound_mm':minimum}
    return {'status':'PASS','worst':worst,'minimum_gap_bound_mm':minimum}
trials=[];selected=None;stored={}
for angle,R,reverse in itertools.product([0.,-30.,30.,-45.,45.],[7.,8.,10.],[True,False]):
    paths,radii,lengths,errors=make_v2(angle,R,reverse)
    hit=check_paths(paths,errors);row={'angle_from_left_toward_front_deg':angle,'base_radius_mm':R,'reverse_radius_order':reverse,
        'zero_pose':'PASS' if hit is None else 'BLOCKED','hit':hit}
    if hit is None:
        hit=check_paths(paths,errors,True);row.update(head_pose_solids='PASS' if hit is None else 'BLOCKED',hit=hit)
    if hit is None:
        gap=pair_gap(paths,errors);row['four_wire_pair_gap_bound_mm']=gap
        if gap<.3:hit={'reason':'pair_gap'}
    if hit is None:
        co=body_clear(paths,errors);row['body_yaw_coexistence']=co
        if co['status']!='PASS':hit={'reason':'body_yaw_coexistence'}
    row['status']='PASS' if hit is None else 'BLOCKED';trials.append(row)
    print('CAM_V2_CASE',angle,R,reverse,row['status'],round(time.time()-V2_START,2),flush=True)
    if hit is None:
        selected={**row,'arc_radii_mm':radii,'analytic_partial_lengths_mm':lengths,'curve_error_bounds_mm':errors,
            'endpoints_mm':[p[-1].tolist() for p in paths]}
        for i,p in enumerate(paths):stored[f'slot{i}']=p
        break
np.savez_compressed(OUT/'curves.npz',**stored)
result={'status':'PASS' if selected else 'BLOCKED','scope':'Conditional four-wire CAM departure with source solids and four previous yaw wires; service loop still missing',
    'source_main_sha256':source_hash,'source_script_sha256':sha(V2_SCRIPT),'source_helper_sha256':sha(V2_HELPER),
    'source_mating_allocation_sha256':sha(V2_DIR/'cam_pitch_port/mating_allocation.json'),
    'source_prior_failure_sha256':sha(V2_DIR/'cam_pitch_port/coexistence_screen.json'),
    'source_body_curves_sha256':sha(V2_DIR/'body_prefix_v2/body_to_yaw_curves.npz'),
    'source_body_motion_sha256':sha(V2_DIR/'body_prefix_v2/body_to_yaw_motion.json'),
    'source_candidate_sha256':sha(candidate/'candidate.blend'),'source_curves_sha256':sha(OUT/'curves.npz'),
    'selected':selected,'trials':trials,'head_poses':130,'wire_OD_mm':OD,'required_bend_radius_mm':REQUIRED_R,
    'photo_uncertainties':'NOT_TESTED','physical_mate':'BLOCKED','anchoring':'NOT_TESTED','yaw_pitch_service_loop':'NOT_TESTED',
    'main_applied':False,'hardware_changed':False,'whole_harness':'BLOCKED','manufacturing_release':False,'elapsed_s':time.time()-V2_START}
(OUT/'screen.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('CAM_DEPARTURE_V2_DONE',result['status'],flush=True)

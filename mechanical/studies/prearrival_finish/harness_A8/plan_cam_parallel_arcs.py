"""Analytic constant-length parallel pitch loops, independent of main CAD.

One upper semicircle, one lower turning arc, and tangent straight spans.
The upper arc translates vertically to keep the exact same wire length.
This prescribes a geometric path; it is not a prediction of an unrestrained
wire or a qualified dynamic cable. Physical anchors remain to be designed.
"""
from pathlib import Path
ARC_SCRIPT=Path(__file__).resolve();ARC_ROOT=ARC_SCRIPT.parent
ARC_HELPER=ARC_ROOT/'plan_cam_pitch_flex.py';__file__=str(ARC_HELPER)
exec(compile(ARC_HELPER.read_text().split('\nall_rows=[];saved={}',1)[0],str(ARC_HELPER),'exec'),globals())
__file__=str(ARC_SCRIPT)
OUT=ARC_ROOT/'cam_parallel_pitch/arc_service';OUT.mkdir(exist_ok=True)
tr=json.loads((ARC_ROOT/'cam_parallel_pitch/shifted_tail_screen.json').read_text())
assert tr['status']=='PASS' and tr['source_main_sha256']==source_hash
td=np.load(ARC_ROOT/'cam_parallel_pitch/shifted_tails.npz')
tails=[td[f'slot{i}'] for i in range(4)]
xx=np.array([p[-1,0] for p in tails]);xc=float(xx.mean())
for name,solid in [('CAM_UART_4P',components['UART_4P']),('CAM_catalogue_housing',housing)]:
    mesh=solid.to_mesh64();bb=np.array(solid.bounding_box())
    ob.append((name,'pitch',solid,bb[:3],bb[3:],BVHTree.FromPolygons(mesh.vert_properties[:,:3],mesh.tri_verts.tolist(),all_triangles=True)))

def line_points(a,b):
    return np.linspace(a,b,max(1,math.ceil(float(np.linalg.norm(b-a))/.02))+1)
def route(ay,az,column,rb,pitch,target=None):
    angle=math.radians(pitch);rt=(column-ay)/2
    if rt<REQUIRED_R+.1:return None
    mat=np.asarray(rigidtr(0,pitch));b=tails[0][-1]@mat[:3,:3].T+mat[:3,3];b[0]=xc
    end_length=(column-b[1]-rb*(1-math.sin(angle)))/math.cos(angle)
    if end_length<0:return None
    zturn=b[2]+end_length*math.sin(angle)+rb*math.cos(angle)
    base=math.pi*rt+(az-zturn)+rb*(math.pi/2-angle)+end_length
    if target is None:return base
    height=(target-base)/2
    if height<5.-1e-6 or az+height<zturn:return None
    a=np.array([xc,ay,az]);top=a+np.array([0.,0.,height]);endtop=np.array([xc,column,az+height])
    t=np.linspace(math.pi,0,max(1,math.ceil(math.pi*rt/.02))+1)
    upper=np.c_[np.full_like(t,xc),ay+rt+rt*np.cos(t),az+height+rt*np.sin(t)]
    tt=np.linspace(0.,-math.pi/2+angle,max(1,math.ceil(rb*(math.pi/2-angle)/.02))+1)
    lower=np.c_[np.full_like(tt,xc),column-rb+rb*np.cos(tt),zturn+rb*np.sin(tt)]
    points=np.vstack([line_points(a,top)[:-1],upper[:-1],line_points(endtop,lower[0])[:-1],lower[:-1],line_points(lower[-1],b)])
    error=max(rt,rb)*(1-math.cos(.02/(2*min(rt,rb))))
    return points,{'pitch_deg':pitch,'upper_arc_lift_mm':height,'top_radius_mm':rt,'lower_radius_mm':rb,
        'bottom_straight_mm':end_length,'vertical_span_mm':az+height-zturn,
        'exact_length_mm':base+2*height,'curve_error_bound_mm':error}

def check_curve(points,error,pitch,full=True):
    for name,group,m,lo,hi,tree in ob:
        yaws=list(range(-60,61,10)) if full and group=='body' else [0]
        for yaw in yaws:
            if group=='pitch':
                mat=np.linalg.inv(np.asarray(rigidtr(0,pitch)));q=points@mat[:3,:3].T+mat[:3,3]
            elif group=='yaw':q=points
            else:
                mat=np.asarray(rigidtr(yaw,0));q=points@mat[:3,:3].T+mat[:3,3]
            hit=check_one(q,error,lo,hi,m,tree)
            if hit:return {'obstacle':name,'yaw_deg':yaw,'pitch_deg':pitch,**hit}
    return None

counts=Counter();failures=Counter();examples={};found=[];stored={};started=time.time()
order=[0,-20,25,-15,20,-10,15,-5,10,5]
grid=itertools.product([24.,23.75,24.25,24.5],[10.,9.,8.,7.,6.],[210.,208.,205.,212.],[7.5,7.,8.])
for aycol,ay,az,rb in grid:
    counts['tried']+=1
    bases=[route(ay,az,aycol,rb,p) for p in order]
    if any(b is None for b in bases):counts['no_tangent_solution']+=1;continue
    target=max(bases)+10.00001;rows=[];curves={};reason=None
    for pitch in order:
        built=route(ay,az,aycol,rb,pitch,target)
        if built is None:reason='height_range';break
        pts,row=built
        for slot,x in enumerate(xx):
            q=pts+np.array([x-xc,0,0]);hit=check_curve(q,row['curve_error_bound_mm'],pitch,True)
            if hit:
                reason=hit['obstacle'];examples.setdefault(reason,{'slot':slot,'params':[ay,az,aycol,rb],**hit});break
            curves[slot,pitch]=q
        if reason:break
        rows.append(row)
    if reason:
        failures[reason]+=1
        if counts['tried']%50==0:print('ARC_SEARCH',dict(counts),dict(failures),round(time.time()-started,1),flush=True)
        continue
    idx=len(found)
    for (slot,pitch),q in curves.items():stored[f'candidate{idx}_slot{slot}_pitch{pitch}']=q
    found.append({'parameters':{'anchor_y_mm':ay,'anchor_z_mm':az,'column_y_mm':aycol,'lower_radius_mm':rb},
        'anchor_slots_mm':[[float(x),ay,az] for x in xx],'exact_length_mm':target,'poses':sorted(rows,key=lambda r:r['pitch_deg'])})
    print('ARC_FOUND',idx,found[-1]['parameters'],target,round(time.time()-started,1),flush=True)
    if len(found)>=4:break
np.savez_compressed(OUT/'curves.npz',**stored)
result={'status':'PASS' if found else 'BLOCKED','scope':'Four parallel service loops versus nominal source geometry only; no complete harness',
    'source_main_sha256':source_hash,'source_script_sha256':sha(ARC_SCRIPT),'source_helper_sha256':sha(ARC_HELPER),
    'tail_report_sha256':sha(ARC_ROOT/'cam_parallel_pitch/shifted_tail_screen.json'),
    'tail_curves_sha256':sha(ARC_ROOT/'cam_parallel_pitch/shifted_tails.npz'),'curves_sha256':sha(OUT/'curves.npz'),
    'wire_OD_mm':OD,'minimum_radius_required_mm':REQUIRED_R,'surface_gap_required_mm':.3,
    'interplane_surface_gap_mm':float(np.diff(xx).min())-OD,'counts':dict(counts),'failures':dict(failures),'examples':examples,
    'selected':found,'joint_angle_samples':130,'whole_partial_wire_self_and_mutual':'NOT_TESTED','body_prefix_coexistence':'NOT_TESTED',
    'fan_in':'NOT_TESTED','anchors':'NOT_TESTED','continuous_joint_motion':'NOT_TESTED','physical_wire_behavior':'NOT_TESTED',
    'whole_harness':'BLOCKED','main_applied':False,'manufacturing_release':False,'elapsed_s':time.time()-started}
(OUT/'screen.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('ARC_DONE',result['status'],dict(counts),dict(failures),flush=True)

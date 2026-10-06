"""Join four packed body prefixes to the yaw segment and verify full poses.

This ends at the existing yaw-frame staging points, not at the CAM connector.
J2 source edits stay in memory. Actual wires, retained clamps and full assembly
sequence are separate work; no supplier cutting lengths are emitted.
"""
from pathlib import Path
MOTION_SCRIPT=Path(__file__).resolve();MOTION_DIR=MOTION_SCRIPT.parent
MOTION_HELPER=MOTION_DIR/'plan_h06_documented_mates.py';__file__=str(MOTION_HELPER)
exec(compile(MOTION_HELPER.read_text().split('\nports=json.loads',1)[0],str(MOTION_HELPER),'exec'),globals())
__file__=str(MOTION_SCRIPT)
from validate import rigidtr
from mathutils.kdtree import KDTree
OUT=MOTION_DIR/'body_prefix_v2'
pack=json.loads((OUT/'packing.json').read_text());joined=json.loads((MOTION_DIR/'joined_entry_screen.json').read_text())
assert pack['status']=='PASS' and pack['source_blend_sha256']==source_hash
rows=[];curves={};start=time.time();yaws=sorted(set(r['yaw_deg'] for r in joined['rows']))

def check_one(points,error,lo,hi,m,tree,offset=0):
    ds=np.linalg.norm(np.diff(points,axis=0),axis=1)
    allowance=.3302+.3+np.maximum(np.r_[ds[0],ds],np.r_[ds,ds[-1]])/2+error+1e-4
    indices=np.where(np.all(points>=lo-allowance[:,None],axis=1)&np.all(points<=hi+allowance[:,None],axis=1))[0]
    indices=indices[indices>=offset]
    for i in indices:
        p=points[i];distance=float(tree.find_nearest(Vector(p))[3])
        if distance<allowance[i]:return {'point_index':int(i),'point_mm':p.tolist(),'distance_mm':distance,'required_mm':float(allowance[i])}
    starts=indices[np.r_[True,np.diff(indices)>1]] if len(indices) else []
    for i in starts:
        p=points[i]
        if np.all(p>=lo) and np.all(p<=hi):
            tiny=manifold.Manifold.sphere(.01,16).translate(p.tolist())
            if (tiny^m).volume()>tiny.volume()/2:return {'point_index':int(i),'point_mm':p.tolist(),'inside':True}
    return None

for yaw in yaws:
    for pr in pack['selected']:
        old=next(r for r in joined['rows'] if r['yaw_deg']==yaw and r['azimuth_deg']==pr['azimuth_deg'])
        first=np.asarray(pr['curve_mm']);tail=np.asarray(old['curve_mm'])
        ix=np.flatnonzero(np.linalg.norm(tail-first[-1],axis=1)<1e-7)
        assert len(ix)==1 and int(ix[0])==344
        points=np.vstack([first,tail[int(ix[0])+1:]])
        error=max(pr['error_bound_mm'],old['error_bound_mm'])
        hits=[]
        for n,s in obstacles.items():
            pitches=range(-20,26,5) if s.group=='pitch' else [0]
            for pitch in pitches:
                if s.group in ['yaw','pitch']:
                    inv=np.linalg.inv(np.asarray(rigidtr(yaw,pitch if s.group=='pitch' else 0)))
                    local=points@inv[:3,:3].T+inv[:3,3]
                else:local=points
                # Only the first outward, pin-normal5mm portion deliberately
                # meets its own mating housing at the wire exit.
                offset=101 if n=='Plug_motion_J5' else 0
                hit=check_one(local,error,s.lo,s.hi,s.m,trees[n],offset)
                if hit:hits.append({'object':n,'pitch_deg':pitch,**hit});break
        for n,s in fixed.items():
            hit=check_one(points,error,s['lo'],s['hi'],s['m'],s['tree'])
            if hit:hits.append({'object':n,**hit})
        key=f'pin{pr["pin"]}_yaw{yaw}';curves[key]=points
        rows.append({'array_key':key,'pin':pr['pin'],'yaw_deg':yaw,'azimuth_deg':pr['azimuth_deg'],
            'status':'BLOCKED' if hits else 'PASS','hits':hits,'curve_error_bound_mm':error,
            'analytic_partial_length_mm':pr['analytic_prefix_length_mm']+joined['analytic_staging_length_mm']-17.2,
            'minimum_bend_radius_mm':min(pr['minimum_curvature_radius_mm'],old['minimum_sampled_central_bend_mm']),
            'scope':'Motion J5 allocated exit to yaw-frame upper staging; pitch/CAM continuation absent'})
    print('H06_PREFIX_MOTION',yaw,'failures',sum(r['status']!='PASS' for r in rows),'seconds',round(time.time()-start,1),flush=True)

# Curve-to-curve and self-return checks include analytic chord-error bounds.
# Resample each chord more finely without pretending it is exact CAD.
STEP=.04;NEED=.6604+.3;pair_rows=[];self_rows=[]
def fine(points):
    out=[]
    for a,b in zip(points,points[1:]):
        n=max(1,math.ceil(float(np.linalg.norm(b-a))/STEP));out.append(np.linspace(a,b,n+1)[:-1])
    p=np.vstack(out+[points[-1:]]);s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    kd=KDTree(len(p))
    for i,pt in enumerate(p):kd.insert(Vector(pt),i)
    kd.balance();return p,s,kd,float(np.linalg.norm(np.diff(p,axis=0),axis=1).max())
for yaw in yaws:
    samples={}
    for r in [q for q in rows if q['yaw_deg']==yaw]:
        key=r['array_key'];p,s,t,step=fine(curves[key]);samples[r['pin']]=(p,s,t,step,r)
        bound=NEED+step+2*r['curve_error_bound_mm']+1e-5;hit=None
        for i,pt in enumerate(p):
            near=[(j,d) for _,j,d in t.find_range(Vector(pt),bound) if abs(s[j]-s[i])>2.]
            if near:
                j,d=min(near,key=lambda x:x[1]);hit={'sample_indices':[i,j],'distance_mm':float(d)};break
        self_rows.append({'pin':r['pin'],'yaw_deg':yaw,'status':'BLOCKED' if hit else 'PASS','hit':hit,'local_neighbours_excluded_arclength_mm':2.})
    for a,b in itertools.combinations(range(1,5),2):
        pa,_,_,sa,ra=samples[a];pb,_,tb,sb,rb=samples[b];minimum=math.inf
        for p in pa:
            _,j,dist=tb.find(Vector(p));minimum=min(minimum,float(dist))
            if minimum<NEED:break
        gap=minimum-(sa+sb)/2-ra['curve_error_bound_mm']-rb['curve_error_bound_mm']-1e-5-.6604
        pair_rows.append({'a':a,'b':b,'yaw_deg':yaw,'status':'PASS' if gap>=.3 else 'BLOCKED','surface_gap_lower_bound_mm':gap})
    print('H06_PREFIX_MUTUAL',yaw,flush=True)
np.savez_compressed(OUT/'body_to_yaw_curves.npz',**curves)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
result={'status':'PASS' if all(r['status']=='PASS' for r in rows+pair_rows+self_rows) else 'BLOCKED',
    'scope':'Packed body prefixes plus yaw local path, 130 finite head poses; not complete11-conductor or pitch harness',
    'source_blend_sha256':source_hash,'source_script_sha256':sha(MOTION_SCRIPT),'source_helper_sha256':sha(MOTION_HELPER),
    'source_packing_sha256':sha(OUT/'packing.json'),'source_yaw_route_sha256':sha(MOTION_DIR/'joined_entry_screen.json'),
    'source_fixed_wires_sha256':sha(fixed_path),'source_cleaned_J2_sha256':sha(MOTION_DIR/'terminal_threading/cleaned/candidate.blend'),
    'curves_file':'body_to_yaw_curves.npz','curves_sha256':sha(OUT/'body_to_yaw_curves.npz'),
    'source_objects':209,'mating_allocations':29,'fixed_wire_count':14,'head_pose_count':130,'wire_pose_instances':520,
    'rows':rows,'mutual_checks':pair_rows,'self_checks':self_rows,
    'minimum_pair_surface_gap_bound_mm':min(r['surface_gap_lower_bound_mm'] for r in pair_rows),
    'main_model_applied':False,'whole_harness':'BLOCKED','supplier_cut_lengths':'BLOCKED',
    'temporary_threading':'NOT_TESTED','anchor_design':'NOT_TESTED','body_assembly':'NOT_TESTED',
    'electrical_pinmap_modified':False,'elapsed_s':time.time()-start,
    'limits':['Both prints are unapproved J2 candidate solids; mainM1.47 remains unchanged.',
      'Only4 UART wires and14 earlier fixed candidates; other7 moving head conductors not integrated.',
      'AMASS solder/heatshrink/lead departure allocations are not complete; SH/actualCAM interface unresolved.',
      'Pose samples and prescribed wire motion are nominal geometry, not bending lifetime, strain or physical validation.']}
(OUT/'body_to_yaw_motion.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('BODY_TO_YAW_COMPLETE',result['status'],len(rows),len(pair_rows),result['minimum_pair_surface_gap_bound_mm'],flush=True)

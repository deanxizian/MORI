"""Independent CAM pitch-anchor route candidate; no main-model edits.

Keep the accepted yaw endpoint and first 5 mm unchanged. Smoothly offset the
pitch endpoint in X using a quintic of the planar loop's exact arclength.
The same arclength function at every pose preserves one common 3D length.
Catalogue/photo geometry remains conditional, and this is not a wire solver.
"""
from pathlib import Path
PW_SCRIPT=Path(__file__).resolve();PW_ROOT=PW_SCRIPT.parent
PW_HELPER=PW_ROOT/'screen_CAM_anchor_support.py';__file__=str(PW_HELPER)
exec(compile(PW_HELPER.read_text().split('\nhost=ss[',1)[0],str(PW_HELPER),'exec'),globals())
__file__=str(PW_SCRIPT)
PW_OUT=PW_ROOT/'cam_pitch_anchor/warp_v1';PW_OUT.mkdir(parents=True,exist_ok=True)
PW_TAIL_HELPER=PW_ROOT/'screen_parallel_shifted_tails.py'
exec(compile('def shifted_tails'+PW_TAIL_HELPER.read_text().split('def shifted_tails',1)[1].split('\ntrials=[];selected=None',1)[0],str(PW_TAIL_HELPER),'exec'),globals())

def pw_readsolid(path):
    a=np.load(path);m=manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles']))
    assert m.status()==manifold.Error.NoError and m.volume()>0
    return m

def pw_obstacle(name,group,m):
    a=m.to_mesh64();b=np.array(m.bounding_box())
    return (name,group,m,b[:3],b[3:],BVHTree.FromPolygons(a.vert_properties[:,:3],a.tri_verts.tolist(),all_triangles=True))

PW_SOURCE_FILES={
 'Pitch_Yoke':PW_ROOT/'cam_anchors/candidate_v3/cleaned/Pitch_Yoke.npz',
 'Yaw_Base':PW_ROOT/'cam_anchors/candidate_v3/cleaned/Yaw_Base.npz',
 'CAM_Tie_Head':PW_ROOT/'cam_tie_install/oriented_head.npz',
 'CAM_Tie_Band':PW_ROOT/'cam_tie_install/oriented_band.npz'}
pw_replacements={n:pw_obstacle(n,'body' if n=='Yaw_Base' else 'yaw',pw_readsolid(p)) for n,p in PW_SOURCE_FILES.items()}
ob=[pw_replacements.get(r[0],r) for r in ob]
ob.extend(pw_replacements[n] for n in ['CAM_Tie_Head','CAM_Tie_Band'])
assert len({r[0] for r in ob})==len(ob)
pw_host=next(r[2] for r in ob if r[0]=='Display_Frame')
PW_OLD_TAILS=[p.copy() for p in tails]
PW_L=float(chosen['exact_length_mm']);PW_WARP_SPAN=PW_L-10.
pw_fan_data=np.load(PW_ROOT/'cam_fan_in/four_bend_transition/curves.npz')
pw_fan_meta=json.loads((PW_ROOT/'cam_fan_in/four_bend_transition/pool.json').read_text())
pw_fans=[fine(pw_fan_data[f'pin{i+1}_candidate0'],.02) for i in range(4)]
pw_fan_errors=[pw_fan_meta['rows'][i]['candidates'][0]['curve_error_bound_mm'] for i in range(4)]

def pw_core(pitch,offset):
    angle=math.radians(pitch);mat=np.asarray(rigidtr(0,pitch))
    b=PW_OLD_TAILS[0][-1]@mat[:3,:3].T+mat[:3,3]
    ay=-1.5;az=230.;rb=7.5;end=.5
    column=b[1]+end*math.cos(angle)+rb*(1-math.sin(angle))
    rt=(column-ay)/2;zt=b[2]+end*math.sin(angle)+rb*math.cos(angle)
    base=math.pi*rt+az-zt+rb*(math.pi/2-angle)+end
    height=(PW_L-base)/2
    lengths=np.array([height,math.pi*rt,az+height-zt,rb*(math.pi/2-angle),end])
    bounds=np.r_[0.,np.cumsum(lengths)]
    assert abs(bounds[-1]-PW_L)<1e-10 and min(lengths)>0
    knots=sorted(set(bounds.tolist()+[5.,PW_L-5.,4.3]))
    s=np.r_[np.concatenate([np.linspace(a,c,max(1,math.ceil((c-a)/.02))+1)[:-1] for a,c in zip(knots,knots[1:])]),PW_L]
    q=np.zeros((len(s),3));q[:,0]=xx[0]
    for k in range(5):
        ids=np.flatnonzero((s>=bounds[k]-1e-12)&(s<=bounds[k+1]+1e-12));t=s[ids]-bounds[k]
        if k==0:q[ids,1]=ay;q[ids,2]=az+t
        elif k==1:
            th=math.pi-t/rt;q[ids,1]=ay+rt+rt*np.cos(th);q[ids,2]=az+height+rt*np.sin(th)
        elif k==2:q[ids,1]=column;q[ids,2]=az+height-t
        elif k==3:
            th=-t/rb;q[ids,1]=column-rb+rb*np.cos(th);q[ids,2]=zt+rb*np.sin(th)
        else:
            rem=end-t;q[ids,1]=b[1]+rem*math.cos(angle);q[ids,2]=b[2]+rem*math.sin(angle)
    u=np.clip((s-5.)/PW_WARP_SPAN,0.,1.)
    q[:,0]-=offset*(10*u**3-15*u**4+6*u**5)
    max_xpp=(10*math.sqrt(3)/3)*abs(offset)/PW_WARP_SPAN**2
    # Planar base has unit speed. Adding X(s) yields |r'| >= 1 and
    # kappa_3D <= sqrt(kappa_planar**2 + max(X'')**2).
    curvature_bound=math.sqrt(1/min(rt,rb)**2+max_xpp**2)
    error=curvature_bound*.02**2/8
    assert np.max(np.abs(q[s<=5.,0]-xx[0]))<1e-12
    assert np.linalg.norm(q[-1]-(b+[-offset,0.,0.]))<1e-8
    return s,q,{'pitch_deg':pitch,'minimum_radius_bound_mm':1/curvature_bound,'curve_error_bound_mm':error,
      'segment_lengths_mm':lengths.tolist(),'planar_length_mm':float(lengths.sum()),'all_knots_mm':knots}

def pw_curve_source(points,error,pitch,core_s=None,tail_parameter=None):
    for name,group,m,lo,hi,tree in ob:
        local=points
        # Reuse only the already-checked unchanged straight contact at the
        # yaw support/tie. Everything after that exact straight is rechecked.
        if core_s is not None and name in ['Pitch_Yoke','CAM_Tie_Head','CAM_Tie_Band']:
            local=points[core_s>=4.3]
        # The first 5 mm of the CAM plug departure is unchanged and its own
        # housing intentionally meets the wire at the exit face.
        if tail_parameter is not None and name in ['CAM_UART_4P','CAM_catalogue_housing']:
            local=points[tail_parameter>=5.]
        for yaw in (range(-60,61,10) if group=='body' else [0]):
            if group=='pitch':mat=np.linalg.inv(np.asarray(rigidtr(0,pitch)))
            elif group=='body':mat=np.asarray(rigidtr(yaw,0))
            else:mat=np.eye(4)
            p=local@mat[:3,:3].T+mat[:3,3]
            hit=check_one(p,error,lo,hi,m,tree)
            if hit:return {'obstacle':name,'pitch_deg':pitch,'yaw_deg':yaw,**hit}
    return None

def pw_pack(samples,error,slot,pitch):
    own=own_prefix_check(samples,pw_fans[slot],error,pw_fan_errors[slot])
    if own['status']!='PASS':return {'type':'own_fan',**own}
    minimum=math.inf
    for other in range(4):
        if other==slot:continue
        result=pair(samples,pw_fans[other],error,pw_fan_errors[other]);minimum=min(minimum,result['gap_bound_mm'])
        if result['status']!='PASS':return {'type':'other_fan','other_slot':other,**result}
    result=self_check(samples,error)
    if result['status']!='PASS':return {'type':'self',**result}
    for yaw in range(-60,61,10):
        mat=np.asarray(rigidtr(yaw,0));q=samples[0]@mat[:3,:3].T+mat[:3,3]
        qs=(q,samples[1],None,samples[3])
        for pin in range(1,5):
            result=pair(qs,body_samples[pin,yaw],error,body_error);minimum=min(minimum,result['gap_bound_mm'])
            if result['status']!='PASS':return {'type':'body_prefix','pin':pin,'yaw_deg':yaw,**result}
    return {'status':'PASS','minimum_fan_body_gap_bound_mm':minimum}

def pw_prism(poly,xmin,xmax):
    area=sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(poly,poly[1:]+poly[:1]))
    if area<0:poly=poly[::-1]
    m=manifold.CrossSection([poly]).extrude(xmax-xmin).transform(np.array([[0,0,1,xmin],[1,0,0,0],[0,1,0,0]]))
    assert m.volume()>0 and len(m.decompose())==1
    return m

def pw_support(offset):
    wire_z=float(PW_OLD_TAILS[0][-1,2]);xs=xx-offset
    lo=float(xs.min()-1.2);hi=float(xs.max()+1.2)
    bed=box([lo,6.3,wire_z+.25],[hi,9.3,wire_z+3.25])
    grooves=manifold.Manifold.batch_boolean([manifold.Manifold.cylinder(4.,.35,circular_segments=64).rotate([90.,0.,0.]).translate([float(x),9.8,wire_z]) for x in xs],manifold.OpType.Add)
    beam=pw_prism([[8.8,wire_z+1.],[31.8,209.],[31.8,212.],[8.8,wire_z+4.]],lo,hi)
    return (bed-grooves)+beam

def pw_support_source(addition):
    nearest={'gap_mm':2.};count=0
    for pitch in range(-20,26,5):
        inv=np.linalg.inv(np.asarray(rigidtr(0,pitch)))
        for name,group,target,lo,hi,tree in ob:
            if name=='Display_Frame':continue
            for yaw in (range(-60,61,10) if group=='body' else [0]):
                mat=np.eye(4) if group=='pitch' else inv
                if group=='body':mat=inv@np.asarray(rigidtr(-yaw,0))
                other=target.transform(mat[:3,:4]);count+=1
                if not overlap_boxes(addition,other,2.):continue
                volume=max(0.,float((addition^other).volume()))
                if volume>1e-6:return {'status':'BLOCKED','object':name,'pitch_deg':pitch,'yaw_deg':yaw,'volume_mm3':volume,'checks':count}
                gap=float(addition.min_gap(other,2.))
                if gap<nearest['gap_mm']:nearest={'gap_mm':gap,'object':name,'pitch_deg':pitch,'yaw_deg':yaw}
                if gap<.3-1e-5:return {'status':'BLOCKED',**nearest,'checks':count}
    return {'status':'PASS','nearest_below_2mm':nearest,'checks':count}

pw_rows=[];pw_stored={};pw_started=time.time()
for pw_offset in [1.5,2.,2.5]:
    pw_tail,pw_errors,pw_sample_R,pw_tail_s,pw_v=shifted_tails(7.5,1.8875-pw_offset,16.,9.5)
    pw_tail_ddx=(10*math.sqrt(3)/3)*abs(1.8875-pw_offset)/16.**2
    pw_tail_R=1/math.sqrt(1/7.5**2+pw_tail_ddx**2)
    pw_row={'offset_x_mm':-pw_offset,'tail_radius_bound_mm':pw_tail_R,'poses':[],'status':'PASS'}
    pw_pose_cache={};pw_local={};pw_failure=None
    for pw_pitch in [0,-20,25,-15,20,-10,15,-5,10,5]:
        pw_s,pw_q,pw_meta=pw_core(pw_pitch,pw_offset);pw_mat=np.asarray(rigidtr(0,pw_pitch));pw_pose_min=math.inf
        if min(pw_tail_R,pw_meta['minimum_radius_bound_mm'])<REQUIRED_R:
            pw_failure={'type':'radius','pitch_deg':pw_pitch};break
        for pw_slot in range(4):
            pw_core_pts=pw_q+[xx[pw_slot]-xx[0],0.,0.]
            pw_tail_pts=pw_tail[pw_slot]@pw_mat[:3,:3].T+pw_mat[:3,3]
            assert np.linalg.norm(pw_core_pts[-1]-pw_tail_pts[-1])<1e-8
            pw_failure=pw_curve_source(pw_core_pts,pw_meta['curve_error_bound_mm'],pw_pitch,core_s=pw_s)
            if pw_failure:pw_failure={'type':'core_source',**pw_failure};break
            pw_failure=pw_curve_source(pw_tail_pts,pw_errors[pw_slot],pw_pitch,tail_parameter=pw_tail_s)
            if pw_failure:pw_failure={'type':'tail_source',**pw_failure};break
            pw_joined=np.vstack([pw_core_pts,pw_tail_pts[-2::-1]])
            pw_sample=fine(pw_joined,.02);pw_err=max(pw_meta['curve_error_bound_mm'],pw_errors[pw_slot])
            pw_check=pw_pack(pw_sample,pw_err,pw_slot,pw_pitch)
            if pw_check['status']!='PASS':pw_failure={'pitch_deg':pw_pitch,'slot':pw_slot,**pw_check};break
            pw_pose_min=min(pw_pose_min,pw_check['minimum_fan_body_gap_bound_mm'])
            pw_pose_cache[pw_slot,pw_pitch]=(pw_sample,pw_err)
            pw_local[f'slot{pw_slot}_core_pitch{pw_pitch}']=pw_core_pts
            pw_local[f'slot{pw_slot}_joined_pitch{pw_pitch}']=pw_joined
        if pw_failure:break
        for a,b in itertools.combinations(range(4),2):
            aa,ea=pw_pose_cache[a,pw_pitch];bb,eb=pw_pose_cache[b,pw_pitch];pw_check=pair(aa,bb,ea,eb)
            pw_pose_min=min(pw_pose_min,pw_check['gap_bound_mm'])
            if pw_check['status']!='PASS':pw_failure={'type':'mutual_loop','slots':[a,b],'pitch_deg':pw_pitch,**pw_check};break
        if pw_failure:break
        pw_row['poses'].append({**pw_meta,'minimum_pack_gap_bound_mm':pw_pose_min})
        print('WARP_POSE',pw_offset,pw_pitch,round(pw_pose_min,6),round(time.time()-pw_started,1),flush=True)
    if pw_failure:pw_row.update(status='BLOCKED',failure=pw_failure)
    else:
        n,w=np.polynomial.legendre.leggauss(128);u=(n+1)/2;xp=-pw_offset/PW_WARP_SPAN*(30*u*u-60*u**3+30*u**4)
        pw_row['constant_core_length_mm']=float(10.+PW_WARP_SPAN*np.dot(w,np.sqrt(1+xp*xp))/2)
        pw_add=pw_support(pw_offset);pw_combined=pw_host+pw_add
        pw_row['root_overlap_mm3']=float((pw_host^pw_add).volume());pw_row['combined_components']=len(pw_combined.decompose())
        assert pw_row['root_overlap_mm3']>1 and pw_row['combined_components']==1
        pw_row['support_source']=pw_support_source(pw_add)
        pw_row['status']=pw_row['support_source']['status']
        for i,p in enumerate(pw_tail):pw_local[f'slot{i}_tail']=p
        pw_local['tail_parameter_mm']=pw_tail_s
        for k,p in pw_local.items():pw_stored[f'offset{pw_offset}_{k}']=p
        cache(PW_OUT/f'offset{pw_offset}_support.npz',pw_add)
        cache(PW_OUT/f'offset{pw_offset}_Display_Frame.npz',pw_combined)
    pw_rows.append(pw_row)
    print('WARP_TRIAL',pw_offset,pw_row['status'],pw_failure or pw_row.get('support_source'),round(time.time()-pw_started,1),flush=True)
    np.savez_compressed(PW_OUT/'curves.npz',**pw_stored)
    pw_report={'status':'PASS' if any(r['status']=='PASS' for r in pw_rows) else 'BLOCKED','scope':'Independent nominal offset-route and support screen; support-to-wire and tie design pending',
      'source_main_sha256':source_hash,'script_sha256':sha(PW_SCRIPT),'source_helper_sha256':sha(PW_HELPER),
      'source_tail_helper_sha256':sha(PW_TAIL_HELPER),'source_assets':{str(p.relative_to(PW_ROOT)):sha(p) for p in PW_SOURCE_FILES.values()},
      'source_pose_report_sha256':sha(upper/'screen.json'),'rows':pw_rows,'obstacle_count':len(ob),'obstacle_names':[r[0] for r in ob],
      'wire_OD_mm':OD,'minimum_required_radius_mm':REQUIRED_R,'minimum_required_surface_gap_mm':.3,'head_pose_samples':130,
      'length_method':'Planar unit-arclength s in [0,L]; x=old_x-offset*smoothstep5(clamp((s-5)/(L-10))). Exact common 3D length is integral sqrt(1+xprime(s)^2) ds, same at every pose; numeric value uses 128-point Gauss-Legendre.',
      'contact_scope':'Unchanged yaw grip first4.3mm and CAM connector first5mm reuse prior contact check only; all changed portions screened anew',
      'support_wire_fit':'NOT_TESTED','pitch_tie':'NOT_TESTED','installation':'NOT_TESTED','physical_behavior':'NOT_TESTED',
      'continuous_motion':'NOT_TESTED','whole_harness':'BLOCKED','main_applied':False,'manufacturing_release':False,'elapsed_s':time.time()-pw_started}
    (PW_OUT/'screen.json').write_text(json.dumps(pw_report,ensure_ascii=False,indent=2)+'\n')
    if pw_row['status']=='PASS':break
assert sha(source)==source_hash
print('WARP_DONE',pw_report['status'],flush=True)

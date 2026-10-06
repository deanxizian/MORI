"""Current-main tool work and a finite search for a bent loose tie tail.

The prescribed tail is a work-space candidate, not a nylon constitutive model.
Optics/shells are explicitly not installed at this assembly step.
"""
from pathlib import Path
import sys,json,math,time,itertools
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from current_context import RetentionContext,PROJECT,np,manifold,sha,stored,cache,overlap_boxes
from mathutils.bvhtree import BVHTree
from mathutils import Vector
ctx=RetentionContext();started=time.time();A8=HERE.parent/'harness_A8'
source_report=A8/'cam_profiled_tool/both_anchors.json'
prior=json.loads(source_report.read_text());excluded=set(prior['not_yet_fitted'])
assert all(n in ctx.base for n in excluded),sorted(excluded-set(ctx.base))
targets={n:m for n,m in ctx.targets.items() if n not in excluded}
for n in ['Pitch_Yoke','Pitch_Cradle']:
    targets[n]=ctx.read(HERE/(n+'.npz'))
for key in ['yaw','connector']:
    for kind in ['band','head']:
        targets[key+'_'+kind]=ctx.read(HERE/(key+'_'+kind+'.npz'))
curves={pin:ctx.curves[f'pin{pin}_y0_p0'] for pin in range(1,5)}

def rigid_check(m,contact=()):
    hits=[];minimum=dict(gap_mm=.301,part=None);operations=[]
    for n,t in targets.items():
        if not overlap_boxes(m,t,.301):continue
        v=float((m^t).volume());g=float(m.min_gap(t,.301)) if v<1e-7 else 0.
        row=dict(part=n,volume_mm3=v,gap_mm=g)
        if n in contact:
            operations.append(row)
            # This is an intended tool/tie interface, separately reported.
            if v>1e-5:hits.append({**row,'reason':'unexpected_overlap_in_contact_interface'})
        elif v>1e-6 or g<.3-1e-5:hits.append(row)
        if n not in contact and g<minimum['gap_mm']:minimum=dict(gap_mm=g,part=n)
    return dict(status='BLOCKED' if hits else 'PASS',hits=hits,minimum_air_gap=minimum,intended_operation_interfaces=operations)

def wire_check(m):
    bb=np.asarray(m.bounding_box());a=m.to_mesh64()
    tree=BVHTree.FromPolygons(a.vert_properties[:,:3],a.tri_verts.tolist(),all_triangles=True)
    hits=[];minimum=1e9
    for pin,p in curves.items():
        ds=np.linalg.norm(np.diff(p,axis=0),axis=1)
        errors=np.maximum(np.r_[ds[0],ds],np.r_[ds,ds[-1]])/2+.0003+.0001
        allow=.3302+.3+errors
        ids=np.flatnonzero(np.all(p>=bb[:3]-allow[:,None],axis=1)&np.all(p<=bb[3:]+allow[:,None],axis=1))
        for i in ids:
            d=float(tree.find_nearest(Vector(p[i]))[3]);minimum=min(minimum,d-.3302-errors[i])
            if d<allow[i]:hits.append(dict(pin=pin,point_mm=p[i].tolist(),distance_mm=d,required_mm=float(allow[i])));break
    return dict(status='BLOCKED' if hits else 'PASS',hits=hits,nearest_surface_bound_mm=minimum if minimum<1e9 else None)

tool_rows=[]
for key,angles in [('yaw',[30,45]),('connector',[0])]:
    for angle in angles:
        path=A8/'cam_profiled_tool'/f'{key}_{angle}_sweep.npz'
        sweep=ctx.read(path)
        r=rigid_check(sweep,contact={key+'_head',key+'_band'})
        w=wire_check(sweep)
        row=dict(anchor=key,angle_deg=angle,rigid=r,wires=w,status='PASS' if r['status']==w['status']=='PASS' else 'BLOCKED')
        tool_rows.append(row);cache(HERE/f'{key}_{angle}_cutter_sweep.npz',sweep)
        print('CURRENT_CUTTER',key,angle,row['status'],r['hits'],w['hits'],flush=True)

# Derive the tail's starting line from the existing oriented allocation.
ref=ctx.read(A8/'cam_profiled_tool/connector_tail_corridor.npz')
bb=np.asarray(ref.bounding_box());start=np.array([(bb[0]+bb[3])/2,bb[1],(bb[2]+bb[5])/2])
W=2.7;T=1.3;LENGTH=80.
def ribbon_curve(first,radius,turn_sign,turn_deg,bend_plane_deg):
    # Keep the same outlet section. Parallel-transport the section around the
    # selected bending-plane axis; do not rotate the latch or fake a twist at
    # the outlet. Edgewise bending remains a physical assumption, not a rating.
    theta=math.radians(turn_deg);phi=math.radians(bend_plane_deg)
    v=turn_sign*np.array([math.cos(phi),0.,math.sin(phi)])
    forward=np.array([0.,1.,0.]);axis=np.cross(forward,v)
    centerline=[];tangents=[];parameters=[]
    def put(q,d,t):
        if centerline and np.linalg.norm(np.asarray(q)-centerline[-1])<1e-9:return
        centerline.append(np.asarray(q,float));tangents.append(np.asarray(d,float));parameters.append(t)
    for f in np.linspace(0,first,max(2,int(first/.15)+1)):put([0,f,0],[0,1,0],0.)
    for t in np.linspace(0,theta,max(2,int(radius*theta/.1)+1)):
        put(v*radius*(1-math.cos(t))+forward*(first+radius*math.sin(t)),v*math.sin(t)+forward*math.cos(t),t)
    remaining=LENGTH-first-radius*theta
    if remaining<=15:return None
    base=centerline[-1].copy();direction=tangents[-1]
    for t in np.linspace(0,remaining,max(2,int(remaining/.2)+1)):put(base+direction*t,direction,theta)
    c=np.array(centerline);d=np.array(tangents)
    def rotate(vector,t):
        return vector*math.cos(t)+np.cross(axis,vector)*math.sin(t)+axis*np.dot(axis,vector)*(1-math.cos(t))
    n=np.array([rotate(np.array([1.,0.,0.]),t) for t in parameters])
    widths=np.array([rotate(np.array([0.,0.,1.]),t) for t in parameters])
    v=[]
    for p,normal,width in zip(c,n,widths):
        v.extend([p-T/2*normal-W/2*width,p+T/2*normal-W/2*width,p+T/2*normal+W/2*width,p-T/2*normal+W/2*width])
    v=np.asarray(v)+start;f=[[0,2,1],[0,3,2]]
    for i in range(len(c)-1):
        for j in range(4):
            a=4*i+j;b=4*i+(j+1)%4;cc=b+4;dd=a+4
            f.extend([[a,b,cc],[a,cc,dd]])
    end=4*(len(c)-1);f.extend([[end,end+1,end+2],[end,end+2,end+3]])
    # The (thickness normal, width) frame has normal opposite to the tangent;
    # reverse this strip winding so the solid has positive oriented volume.
    m=manifold.Manifold(manifold.Mesh64(v,np.asarray(f,dtype=np.uint64)[:,::-1]))
    if m.status()!=manifold.Error.NoError:return None
    assert m.volume()>0 and len(m.decompose())==1
    return m,c+start,dict(exact_centerline_length_mm=LENGTH,nominal_minimum_radius_mm=radius,
                             geometric_path_error_bound_mm=radius*(1-math.cos(theta/max(1,int(radius*theta/.1))/2)))

trials=[];passing=[]
for first,radius,sgn,angle,plane in itertools.product([.6,1.,2.],[5.,8.,10.],[-1,1],[60.,90.,120.],[90.,45.,-45.]):
    made=ribbon_curve(first,radius,sgn,angle,plane)
    if made is None:continue
    tail,c,meta=made
    r=rigid_check(tail,contact={'connector_head','connector_band'})
    w=wire_check(tail) if r['status']=='PASS' else dict(status='NOT_TESTED')
    row=dict(first_straight_mm=first,radius_mm=radius,side=sgn,turn_deg=angle,bend_plane_deg=plane,**meta,
             rigid=r,wires=w,status='PASS' if r['status']==w['status']=='PASS' else 'BLOCKED')
    trials.append(row)
    if row['status']=='PASS':
        idx=len(passing);cache(HERE/f'connector_tail_{idx}.npz',tail)
        np.savez_compressed(HERE/f'connector_tail_{idx}_curve.npz',points_mm=c)
        passing.append(dict(index=idx,**row))
        print('BENT_TAIL_PASS',idx,first,radius,sgn,angle,plane,flush=True)
    if len(passing)>=6:break
ctx.assert_unchanged()
result=dict(status='PASS' if passing and all(any(r['anchor']==k and r['status']=='PASS' for r in tool_rows) for k in ['yaw','connector']) else 'BLOCKED',
    scope='Finite cutter-approach and loose tail-shape screening at zero pose, before listed optics/shell parts are installed',
    **ctx.evidence(),script_sha256=sha(__file__),context_sha256=sha(HERE/'current_context.py'),
    old_stage_source_sha256=sha(source_report),not_yet_installed=sorted(excluded),fixture_count=len(targets),
    tool_rows=tool_rows,tail_start_mm=start.tolist(),tail_allocation_length_mm=LENGTH,tail_width_mm=W,tail_thickness_mm=T,
    tail_length_basis='Conservative 80 mm workspace, above 105 mm flat maximum minus the approximately 26.7 mm formed clamp route; no cut length',
    tail_trials=trials,accepted_tails=passing,
    actual_tie_latch_bending_and_tightening='NOT_TESTED',hand_and_jaw_motion='NOT_TESTED',
    full_tail_threading_and_shrinking='NOT_TESTED',complete_wire_assembly='NOT_TESTED',
    elapsed_s=time.time()-started)
(HERE/'tools_and_tail.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('CURRENT_TOOL_TAIL_DONE',result['status'],'tail_trials',len(trials),'passing',len(passing),flush=True)

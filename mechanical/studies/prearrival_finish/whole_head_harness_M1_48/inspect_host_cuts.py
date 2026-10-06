"""Build explicitly unadopted, finite-sweep host candidates for review.

Cut brushes have extra geometric clearance; neither this margin nor discrete
motion samples certify a printable fit, strength, or continuous motion.
"""
from pathlib import Path
import sys,json,time,math
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent/'outer_harness_M1_48'))
from native_context import Context,np,manifold,sha
from validate import rigidtr
ctx=Context();started=time.time()
pack=json.loads((HERE/'packing.json').read_text())
assert pack['status']=='PASS' and pack['source_main_sha256']==ctx.source_hash
data=np.load(HERE/'packed_curves.npz')
assert sha(HERE/'packed_curves.npz')==pack['output_curves_sha256']

def save(path,m):
    mesh=m.to_mesh64()
    np.savez_compressed(path,vertices_mm=np.asarray(mesh.vert_properties[:,:3]),triangles=np.asarray(mesh.tri_verts))

def tube(points,radius,step=.16,sides=24):
    p=np.asarray(points)
    # Retain every corner/seam by selecting a subsequence with small arc length.
    cumulative=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    ids=np.unique(np.r_[0,np.searchsorted(cumulative,np.arange(0,cumulative[-1],step)),len(p)-1])
    p=p[ids]
    t=np.gradient(p,axis=0);t/=np.linalg.norm(t,axis=1)[:,None]
    u=np.cross(t,np.array([0.,1.,0.]));u/=np.linalg.norm(u,axis=1)[:,None]
    v=np.cross(t,u)
    q=np.linspace(0,2*math.pi,sides,endpoint=False)
    r=radius/math.cos(math.pi/sides)
    vertices=(p[:,None,:]+r*(np.cos(q)[None,:,None]*u[:,None,:]+np.sin(q)[None,:,None]*v[:,None,:])).reshape(-1,3)
    faces=[]
    for j in range(len(p)-1):
        for k in range(sides):
            a=j*sides+k;b=j*sides+(k+1)%sides;c=(j+1)*sides+k;d=(j+1)*sides+(k+1)%sides
            faces.extend([(a,b,c),(b,d,c)])
    for k in range(1,sides-1):faces.append((0,k+1,k))
    last=(len(p)-1)*sides
    for k in range(1,sides-1):faces.append((last,last+k,last+k+1))
    m=manifold.Manifold(manifold.Mesh64(vertices,np.asarray(faces,dtype=np.uint64)))
    assert m.status()==manifold.Error.NoError
    if m.volume()<0:
        m=manifold.Manifold(manifold.Mesh64(vertices,np.asarray(faces,dtype=np.uint64)[:,::-1].copy()))
    assert m.status()==manifold.Error.NoError and m.volume()>0
    return m

rows=[]
for name,group in [('Yaw_Base','body'),('Pitch_Yoke','yaw')]:
    original=ctx.ss[name].m;bb=np.asarray(original.bounding_box());brushes=[]
    for i,slot in enumerate(pack['selected']):
        per_wire=[]
        for yaw in range(-60,61,10):
            p=data[f'wire{i}_y{yaw}']
            if group=='yaw':
                tr=np.linalg.inv(np.asarray(rigidtr(yaw,0)));p=p@tr[:3,:3].T+tr[:3,3]
            keep=np.flatnonzero((p[:,2]>=bb[2]-2)&(p[:,2]<=bb[5]+2))
            if not len(keep):continue
            a=max(0,int(keep[0])-1);b=min(len(p),int(keep[-1])+2)
            brush=tube(p[a:b],slot['OD_mm']/2+.352)
            if (brush^original).volume()>1e-7:per_wire.append(brush)
        if per_wire:
            joined=manifold.Manifold.batch_boolean(per_wire,manifold.OpType.Add)
            brushes.append(joined)
        print('HOST_BRUSH',name,i,'poses',len(per_wire),'seconds',round(time.time()-started,1),flush=True)
    cutter=manifold.Manifold.batch_boolean(brushes,manifold.OpType.Add)
    candidate=original-cutter
    components=[float(m.volume()) for m in candidate.decompose()]
    removed=original-candidate
    save(HERE/(name+'_trial.npz'),candidate);save(HERE/(name+'_removed.npz'),removed)
    # Recheck every sampled curve against the actual candidate, including the
    # originally omitted host; this is not inferred from brush construction.
    prior=ctx.targets;ctx.targets={name:ctx.target(candidate)};hits=[]
    for i,slot in enumerate(pack['selected']):
        for yaw in range(-60,61,10):
            p=data[f'wire{i}_y{yaw}']
            if group=='yaw':
                tr=np.linalg.inv(np.asarray(rigidtr(yaw,0)));p=p@tr[:3,:3].T+tr[:3,3]
            hit=ctx.clear(p,chord_error=.0001,radius=slot['OD_mm']/2)
            if hit:hits.append(dict(wire=i,yaw_deg=yaw,**hit))
    ctx.targets=prior
    rows.append(dict(name=name,group=group,kernel=str(candidate.status()),component_volumes_mm3=components,
        native_volume_mm3=float(original.volume()),removed_mm3=float(removed.volume()),
        added_mm3=float((candidate-original).volume()),
        source=str((HERE/(name+'_trial.npz')).relative_to(PROJECT)),source_sha256=sha(HERE/(name+'_trial.npz')),
        wire_tests=143,wire_hits=hits,wire_clearance_status='BLOCKED' if hits else 'PASS',
        connected_status='PASS' if len([x for x in components if x>1e-7])==1 else 'BLOCKED',
        minimum_wall='NOT_TESTED',retention_support_material='NOT_TESTED',strength='NOT_TESTED'))
    print('HOST_RESULT',rows[-1],flush=True)
ctx.assert_unchanged()
result=dict(status='PASS' if all(r['wire_clearance_status']=='PASS' and r['connected_status']=='PASS' for r in rows) else 'BLOCKED',
    scope='Finite-sweep two-host construction and nominal local wire clearance only',
    source_main_sha256=ctx.source_hash,script_sha256=sha(__file__),packing_sha256=sha(HERE/'packing.json'),
    curves_sha256=sha(HERE/'packed_curves.npz'),geometric_brush_margin_mm=.352,
    host_rows=rows,whole_harness='BLOCKED',main_applied=False,manufacturing_release=False,
    continuous_yaw='NOT_TESTED',all_printed_wall_thickness='NOT_TESTED',strength='NOT_TESTED',
    shape_simplification='NOT_TESTED',full_port_paths='NOT_TESTED',elapsed_s=time.time()-started)
(HERE/'host_cuts.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('HOST_CUTS_DONE',result['status'],'seconds',round(time.time()-started,1),flush=True)

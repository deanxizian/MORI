"""Planar camera-FPC corridor requirement, not an invented compatible cable.

Origin direction comes from the received official installed photo. Camera-tail
side, slot height, widths and radii are explicit allocations. No extension or
new hole is adopted; whole factory FPC length is still unknown.
"""
from pathlib import Path
import itertools,json,math,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes/static_flex';OUT=BASE/'camera_corridor';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import manifold
ctx=Context();started=time.time()
ports=json.loads((BASE/'endpoints.json').read_text())['ports']
row=next(r for r in ports if r['reference']=='CAMERA_FPC_24');bb=np.asarray(row['bounds_mm'])
start=bb.mean(0);start[0]=0.;start[2]=bb[1,2]+.6
camera=ctx.ss['Camera_PCB'];c=(camera.lo+camera.hi)/2
down=np.array([0,math.sin(math.radians(10)),-math.cos(math.radians(10))])
end=c+down*(4.1+.6);end[0]=0.

def path(rear_radius,front_radius,offset,width,step=.15):
    pos=start[1:].copy();angle=math.pi/2;p=[];t=[];pieces=[];length=0
    def line(L):
        nonlocal pos,length
        if L<-1e-8:raise ValueError('negative straight')
        vec=np.array([math.cos(angle),math.sin(angle)])
        for u in np.linspace(0,1,max(1,math.ceil(L/step))+1)[:-1]:p.append(pos+L*u*vec);t.append(vec)
        pieces.append(dict(kind='line',length_mm=L));pos=pos+L*vec;length+=L
    def arc(R,turn):
        nonlocal pos,angle,length
        a=angle;A=pos.copy();sign=1 if turn>0 else -1
        n=max(2,math.ceil(R*abs(turn)/step))
        for u in np.linspace(0,turn,n+1)[:-1]:
            p.append(A+R/sign*np.array([math.sin(a+u)-math.sin(a),-math.cos(a+u)+math.cos(a)]))
            t.append(np.array([math.cos(a+u),math.sin(a+u)]))
        pos=A+R/sign*np.array([math.sin(a+turn)-math.sin(a),-math.cos(a+turn)+math.cos(a)])
        angle+=turn;length+=R*abs(turn);pieces.append(dict(kind='arc',radius_mm=R,turn_deg=math.degrees(turn),length_mm=R*abs(turn)))
    # Gentle back-offset, preserving the initial +Z tangent and vertical width-X strip.
    R=5.;theta=math.acos(1-offset/(2*R));arc(R,theta);arc(R,-theta)
    final_turn=math.radians(100)
    upper_run_z=end[2]-front_radius*(1-math.cos(final_turn))
    vertical_top_z=upper_run_z-rear_radius
    line(vertical_top_z-pos[1]);arc(rear_radius,-math.pi/2)
    front_start_y=end[1]-front_radius*math.sin(final_turn)
    line(front_start_y-pos[0]);arc(front_radius,final_turn)
    p.append(pos.copy());t.append(np.array([math.cos(angle),math.sin(angle)]))
    points=np.column_stack([np.zeros(len(p)),np.array(p)]);T=np.column_stack([np.zeros(len(t)),np.array(t)])
    W=np.repeat([[1.,0,0]],len(p),axis=0);N=np.cross(T,W);thickness=.15
    v=np.stack([points-W*width/2-N*thickness/2,points+W*width/2-N*thickness/2,
        points+W*width/2+N*thickness/2,points-W*width/2+N*thickness/2],axis=1).reshape(-1,3)
    f=[]
    for i in range(len(p)-1):
        for j in range(4):
            a=4*i+j;b=4*i+(j+1)%4;f.extend([[a,b,b+4],[a,b+4,a+4]])
    f.extend([[0,2,1],[0,3,2]]);a=4*(len(p)-1);f.extend([[a,a+1,a+2],[a,a+2,a+3]])
    f=np.array(f,dtype=np.uint64)
    if np.einsum('ij,ij->i',v[f[:,0]],np.cross(v[f[:,1]],v[f[:,2]])).sum()<0:f=f[:,::-1].copy()
    assert np.linalg.norm(points[-1]-end)<1e-8
    minimum=min(rear_radius,front_radius,5.);error=(minimum+thickness/2)*(1-math.cos(step/minimum/2))
    return dict(points_mm=points,tangents=T,width_vectors=W,vertices_mm=v,triangles=f,
        metadata=dict(length_mm=length,width_mm=width,thickness_mm=thickness,rear_radius_mm=rear_radius,
            front_radius_mm=front_radius,rearward_offset_mm=offset,minimum_radius_mm=minimum,
            chord_error_bound_mm=error,start_mm=start.tolist(),end_mm=end.tolist(),pieces=pieces,
            start_tangent=T[0].tolist(),end_tangent=T[-1].tolist(),planar=True,twist_deg=0.,
            width_source='6.6 is a prior photo visible narrow tail estimate; 12.5 is a wide contact-end capacity hypothesis, not a selected full FPC profile.',
            source_FPC_length_mm=None,source_FPC_compatibility='BLOCKED',classification='PLACEHOLDER',data_status='ASSUMED'))
rows=[]
for rear,front,offset,width in itertools.product([3.,3.5],[2.5,3.],[1.4,1.8],[6.6,12.5]):
    g=path(rear,front,offset,width);m=manifold.Manifold(manifold.Mesh64(g['vertices_mm'],g['triangles']));assert m.status()==manifold.Error.NoError
    lo=g['vertices_mm'].min(0);hi=g['vertices_mm'].max(0);near=[];fails=[]
    threshold=.3+g['metadata']['chord_error_bound_mm'];name=f'R{rear:g}_F{front:g}_O{offset:g}_W{width:g}'
    for n,target in ctx.targets.items():
        if np.any(lo>target['hi']+1) or np.any(hi<target['lo']-1):continue
        overlap=float((m^target['m']).volume());gap=float(m.min_gap(target['m'],1.))
        row=dict(target=n,overlap_mm3=overlap,gap_mm=gap,gap_search_cap_mm=1.)
        near.append(row)
        if overlap>1e-7 or gap<threshold:fails.append(row)
    np.savez_compressed(OUT/(name+'.npz'),**{k:v for k,v in g.items() if k!='metadata'})
    rows.append(dict(id=name,status='FAIL' if fails else 'PASS',parameters=g['metadata'],
        nearby_targets=near,failures=fails,required_model_gap_mm=threshold,volume_mm3=float(m.volume())))
    print('CAMERA_FPC_CORRIDOR',name,rows[-1]['status'],fails,flush=True)
ctx.assert_unchanged()
r=dict(status='PASS' if any(x['status']=='PASS' for x in rows) else 'BLOCKED',
    scope='Candidate corridor requirements only; not proof that supplied OV3660 FPC reaches or that an extension is compatible',
    sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in [BASE/'endpoints.json',BASE/'connector_faces/direction_receipt.json']},
    rows=rows,main_changed=False,adopted=False,
    assumed_port_basis='CAM: package Y-center at X0 and top+0.6. Camera: existing carrier lower edge+0.6 along modeled down direction. Actual flexible-tail side and no-bend regions require drawing.',
    full_factory_FPC_length_mm=None,new_extension_selected=False,physical_validation='NOT_TESTED',
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('CAMERA_FPC_CORRIDOR_DONE',r['status'],flush=True)

"""Screen a plain integral sliding window on the current yaw yoke, independently."""
from pathlib import Path
import itertools,json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=HERE/'remaining_routes';OUT=BASE/'cam_restraints/sliding_guide_v3';OUT.mkdir(parents=True,exist_ok=True)
JOIN=BASE/'cam_side_fans/c6_join';CON=BASE/'cam_restraints/connector'
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from common import manifold
from validate import rigidtr
from sliding_cam_guide_v3_geometry import build
from mathutils import Vector
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text());jr=read(JOIN/'join_review.json')
assert jr['status']=='PASS'
for f,h in {**jr['sources'],**jr['inputs']}.items():assert sha(ROOT/f)==h,f
assert sha(JOIN/'candidate_curves.npz')==jr['curve_sha256'];curves=np.load(JOIN/'candidate_curves.npz')
def stored(path):
    a=np.load(path);m=manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles'].astype(np.uint64)));assert m.status()==manifold.Error.NoError;return m
def cache(path,m):
    a=m.to_mesh64();np.savez_compressed(path,vertices_mm=a.vert_properties[:,:3],triangles=a.tri_verts)
def overlap(a,b,pad=.3):
    aa=np.asarray(a.bounding_box());bb=np.asarray(b.bounding_box());return bool(np.all(aa[:3]<=bb[3:]+pad) and np.all(bb[:3]<=aa[3:]+pad))
host=ctx.ss['Pitch_Yoke'].m;guide,meta=build();combined=host+guide
construction=dict(**meta,root_overlap_mm3=float((host^guide).volume()),removed_mm3=float((host-combined).volume()),
                  added_mm3=float((combined-host).volume()),components=[float(m.volume()) for m in combined.decompose()])
construction['status']='PASS' if construction['root_overlap_mm3']>1 and len(construction['components'])==1 and abs(construction['removed_mm3'])<1e-7 else 'BLOCKED'
targets=dict(ctx.targets);targets['Yaw_Base']=ctx.target(stored(BASE/'c6_left_slot_entry/Yaw_Base_candidate.npz'))
groups={n:s.group if s.group in ['yaw','pitch'] else 'body' for n,s in ctx.ss.items()}
connector_paths=[]
if (CON/'review.json').exists():
    cr=read(CON/'review.json')
    for n,h in cr['output_geometry'].items():assert sha(CON/n)==h,n
    for n in ['addition','band','head']:
        path=CON/(n+'.npz');connector_paths.append(path);name='connector_'+n;targets[name]=ctx.target(stored(path));groups[name]='pitch'
hits=[];close=[];checks=0
for group in ['body','yaw','pitch']:
    angles=range(-60,61,10) if group=='body' else range(-20,26,5) if group=='pitch' else [0]
    for angle in angles:
        tr=np.asarray(rigidtr(angle,0)) if group=='body' else np.linalg.inv(np.asarray(rigidtr(0,angle))) if group=='pitch' else np.eye(4)
        m=guide.transform(tr[:3,:])
        for name,target in targets.items():
            if groups.get(name,'body')!=group or name=='Pitch_Yoke':continue
            checks+=1;t=target['m']
            if not overlap(m,t):continue
            vol=float((m^t).volume());gap=float(m.min_gap(t,.31)) if abs(vol)<1e-7 else 0.
            row=dict(target=name,group=group,angle=angle,overlap_mm3=vol,gap_mm=gap,status='PASS' if abs(vol)<1e-6 and gap>=.3-1e-5 else 'BLOCKED');close.append(row)
            if row['status']!='PASS':hits.append(row)
    print('SLIDING_GUIDE_NATIVE',group,len(hits),flush=True)
t=ctx.target(guide);wire_hits=[];wire_count=0
for yaw,pitch in itertools.product(range(-60,61,10),range(-20,26,5)):
    inv=np.linalg.inv(np.asarray(rigidtr(yaw,0)))
    for name in ['CAM_1','CAM_2','CAM_3','CAM_4','P_J9_1','P_J9_2','P_J9_3','P_J18_1','P_J18_2','SPK_reservation_3','SPK_reservation_6']:
        key=f'{name}_y{yaw}'+(f'_p{pitch}' if name.startswith('CAM_') else '');p=curves[key]@inv[:3,:3].T+inv[:3,3]
        radius=.3302 if name.startswith('CAM_') else .4445 if name.startswith('SPK_') else .5842
        ds=np.linalg.norm(np.diff(p,axis=0),axis=1);allow=radius+.3+np.maximum(np.r_[ds[0],ds],np.r_[ds,ds[-1]])/2+.0003+.0001
        ids=np.flatnonzero(np.all(p>=t['lo']-allow[:,None],axis=1)&np.all(p<=t['hi']+allow[:,None],axis=1));hit=None
        for i in ids:
            d=float(t['tree'].find_nearest(Vector(p[i]))[3])
            if d<allow[i]:hit=dict(point_mm=p[i].tolist(),distance_mm=d,required_mm=float(allow[i]));break
        if hit:wire_hits.append(dict(wire=name,yaw=yaw,pitch=pitch,**hit))
        wire_count+=1
    if pitch==25:print('SLIDING_GUIDE_WIRES',yaw,len(wire_hits),flush=True)
assert wire_count==1430;ctx.assert_unchanged()
cache(OUT/'addition.npz',guide);cache(OUT/'Pitch_Yoke_candidate.npz',combined)
inputs=[JOIN/'join_review.json',JOIN/'candidate_curves.npz',BASE/'c6_left_slot_entry/Yaw_Base_candidate.npz',HERE/'sliding_cam_guide_v3_geometry.py',HERE/'sliding_cam_guide_geometry.py',*connector_paths]
if connector_paths:inputs.append(CON/'review.json')
r=dict(status='PASS' if construction['status']=='PASS' and not hits and not wire_hits else 'BLOCKED',scope='Integral sliding guide candidate, current native and11route finite-pose screen; no main adoption.',
       sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},construction=construction,native_checks=checks,close_checks=close,native_hits=hits,head_poses=130,
       wire_checks=wire_count,wire_hits=wire_hits,connector_candidate_included=bool(connector_paths),main_changed=False,approved=False,C6_main_applied=False,
       output_geometry={p.name:sha(p) for p in OUT.glob('*.npz')},physical_sliding_and_wear='NOT_TESTED',terminal_feed='NOT_TESTED',assembly='NOT_TESTED',strength='NOT_TESTED',
       full_harness='BLOCKED',script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(r,indent=2)+'\n');print('SLIDING_GUIDE_DONE',r['status'],construction,hits[:3],wire_hits[:3],flush=True)

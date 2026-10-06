"""Recheck the unadopted CAM-return anchor on current solids and eleven routes."""
from pathlib import Path
import itertools,json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=HERE/'remaining_routes';OUT=BASE/'cam_restraints/return_clamp';OUT.mkdir(parents=True,exist_ok=True)
A8=HERE.parent/'harness_A8';OLD=A8/'cam_pitch_anchor/connector_anchor';JOIN=BASE/'cam_side_fans/c6_join'
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from common import manifold
from validate import rigidtr
from mathutils import Vector
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text())
jr=read(JOIN/'join_review.json');assert jr['status']=='PASS' and not jr['approved']
for f,h in {**jr['sources'],**jr['inputs']}.items():assert sha(ROOT/f)==h,f
assert sha(JOIN/'candidate_curves.npz')==jr['curve_sha256'];curves=np.load(JOIN/'candidate_curves.npz')
def stored(path):
    a=np.load(path);m=manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles'].astype(np.uint64)));assert m.status()==manifold.Error.NoError;return m
def cache(path,m):
    a=m.to_mesh64();np.savez_compressed(path,vertices_mm=a.vert_properties[:,:3],triangles=a.tri_verts)
paths={'addition':OLD/'addition.npz','band':OLD/'z212.0_band.npz','head':OLD/'z212.0_head.npz'}
pieces={n:stored(p).translate([-18.+(.03 if n!='addition' else 0),0,0]) for n,p in paths.items()};host=ctx.ss['Pitch_Cradle'].m;joined=host+pieces['addition'];tie=pieces['band']+pieces['head']
construction=dict(host='Pitch_Cradle',root_overlap_mm3=float((host^pieces['addition']).volume()),added_mm3=float((joined-host).volume()),
    removed_mm3=float((host-joined).volume()),components=[float(m.volume()) for m in joined.decompose()],tie_host_overlap_mm3=float((tie^joined).volume()))
construction['status']='PASS' if construction['root_overlap_mm3']>1 and len(construction['components'])==1 and abs(construction['removed_mm3'])<1e-7 and abs(construction['tie_host_overlap_mm3'])<1e-6 else 'BLOCKED'
original=ctx.targets;targets=dict(original);targets['Yaw_Base']=ctx.target(stored(BASE/'c6_left_slot_entry/Yaw_Base_candidate.npz'))
groups={n:s.group if s.group in ['yaw','pitch'] else 'body' for n,s in ctx.ss.items()}
GUIDE=BASE/'cam_restraints/sliding_guide_v4'
gr=read(GUIDE/'review.json');assert gr['status']=='PASS'
assert sha(GUIDE/'addition.npz')==gr['output_geometry']['addition.npz']
targets['Sliding_guide']=ctx.target(stored(GUIDE/'addition.npz'));groups['Sliding_guide']='yaw'
def overlap(a,b,pad=.3):
    aa=np.asarray(a.bounding_box());bb=np.asarray(b.bounding_box());return bool(np.all(aa[:3]<=bb[3:]+pad) and np.all(bb[:3]<=aa[3:]+pad))
native_checks=0;close=[];hits=[]
for group in ['body','yaw','pitch']:
    poses=list(itertools.product(range(-60,61,10),range(-20,26,5))) if group=='body' else [(0,p) for p in range(-20,26,5)] if group=='yaw' else [(0,0)]
    for yaw,pitch in poses:
        tr=np.asarray(rigidtr(yaw,pitch));moving={n:m.transform(tr[:3,:]) for n,m in pieces.items()}
        for name,target in targets.items():
            if groups.get(name,'body')!=group or name=='Pitch_Cradle':continue
            for part,m in moving.items():
                native_checks+=1;t=target['m']
                if not overlap(m,t):continue
                vol=float((m^t).volume());gap=float(m.min_gap(t,.31)) if abs(vol)<1e-7 else 0.
                row=dict(feature=part,target=name,group=group,yaw=yaw,pitch=pitch,overlap_mm3=vol,gap_mm=gap,
                    status='PASS' if abs(vol)<1e-6 and gap>=.3-1e-5 else 'BLOCKED')
                close.append(row)
                if row['status']!='PASS':hits.append(row)
    print('CONNECTOR_RESTRAINT_NATIVE',group,len(hits),flush=True)
trees={n:ctx.target(m) for n,m in pieces.items()};wire_rows=[];grips=[];wire_count=0
def wirecheck(p,radius,target,contact_x=None):
    ds=np.linalg.norm(np.diff(p,axis=0),axis=1);err=np.maximum(np.r_[ds[0],ds],np.r_[ds,ds[-1]])/2+.0003+.0001;allow=radius+.3+err
    grip=np.zeros(len(p),bool)
    if contact_x is not None:grip=(np.abs(p[:,0]-contact_x)<1e-4)&(np.abs(p[:,1]+20.800000190734863)<1e-4)&(p[:,2]>=209.6000061-1e-4)&(p[:,2]<=224.6000061+1e-4)
    ids=np.flatnonzero(np.all(p>=target['lo']-allow[:,None],axis=1)&np.all(p<=target['hi']+allow[:,None],axis=1)&~grip)
    for i in ids:
        d=float(target['tree'].find_nearest(Vector(p[i]))[3])
        if d<allow[i]:return dict(status='BLOCKED',point_mm=p[i].tolist(),distance_mm=d,required_mm=float(allow[i]))
    starts=ids[np.r_[True,np.diff(ids)>1]] if len(ids) else []
    for i in starts:
        q=manifold.Manifold.sphere(.005,12).translate(p[i].tolist())
        if (q^target['m']).volume()>q.volume()/2:return dict(status='BLOCKED',point_mm=p[i].tolist(),inside=True)
    return dict(status='PASS',noncontact_candidate_samples=len(ids))
for yaw,pitch in itertools.product(range(-60,61,10),range(-20,26,5)):
    inv=np.linalg.inv(np.asarray(rigidtr(yaw,pitch)))
    for name in ['CAM_1','CAM_2','CAM_3','CAM_4','P_J9_1','P_J9_2','P_J9_3','P_J18_1','P_J18_2','SPK_reservation_3','SPK_reservation_6']:
        key=f'{name}_y{yaw}'+(f'_p{pitch}' if name.startswith('CAM_') else '')
        p=curves[key]@inv[:3,:3].T+inv[:3,3];radius=.3302 if name.startswith('CAM_') else .4445 if name.startswith('SPK_') else .5842
        x=(-26.600000143051147-int(name[-1])+1) if name.startswith('CAM_') else None
        for part,t in trees.items():
            row=wirecheck(p,radius,t,x);wire_count+=1
            if row['status']!='PASS':wire_rows.append(dict(wire=name,feature=part,yaw=yaw,pitch=pitch,**row))
    if pitch==25:print('CONNECTOR_RESTRAINT_WIRES',yaw,len(wire_rows),flush=True)
for pin in range(1,5):
    x=-26.600000143051147-pin+1;r=(.3302+.001)/np.cos(np.pi/64)
    tube=manifold.Manifold.cylinder(15.,r,circular_segments=64).translate([x,-20.800000190734863,209.6000061])
    vol=float((tube^(pieces['addition']+tie)).volume());grips.append(dict(pin=pin,overlap_mm3=vol,status='PASS' if abs(vol)<1e-6 else 'BLOCKED'))
assert wire_count==4290;ctx.assert_unchanged()
for n,m in {**pieces,'Pitch_Cradle_candidate':joined}.items():cache(OUT/(n+'.npz'),m)
inputs=[GUIDE/'review.json',GUIDE/'addition.npz',JOIN/'join_review.json',JOIN/'candidate_curves.npz',BASE/'c6_left_slot_entry/Yaw_Base_candidate.npz',*paths.values(),A8/'cam_tie_install/sources/dimensions.json',HERE.parent/'cam_retention_M1_48/anchors.json']
r=dict(status='PASS' if construction['status']=='PASS' and not hits and not wire_rows and all(x['status']=='PASS' for x in grips) else 'BLOCKED',
    scope='Unadopted pitch-frame anchor on the existing fixed15mm return straight with catalogue-bounded tie, rechecked on current C6 conditional assembly and11routes.',sources=ctx.sources,
    inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},construction=construction,native_checks=native_checks,close_checks=close,native_hits=hits,
    head_poses=130,wire_feature_checks=wire_count,wire_hits=wire_rows,nominal_straight_grip_sweeps=grips,
    output_geometry={p.name:sha(p) for p in OUT.glob('*.npz')},main_changed=False,approved=False,C6_main_applied=False,
    added_printed_parts=0,proposed_ties=1,anchor_translation_x_mm=-18.,tie_relative_translation_x_mm=.03,sliding_guide_included=True,assembly='NOT_TESTED',physical_grip='NOT_TESTED',strength='NOT_TESTED',full_harness='BLOCKED',
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(r,indent=2)+'\n');print('CONNECTOR_RESTRAINT_DONE',r['status'],r['elapsed_s'],flush=True)

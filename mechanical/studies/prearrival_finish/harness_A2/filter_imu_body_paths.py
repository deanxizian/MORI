# -*- coding: utf-8 -*-
"""Filter existing IMU curve pools against body-shell/bridge assembly poses."""
from pathlib import Path
import json,hashlib,time,sys
STAGE=Path(__file__).resolve().parent
code=(STAGE/'check_fourteen_body_sequence.py').read_text().split('paths=[]')[0]
exec(compile(code,str(STAGE/'check_fourteen_body_sequence.py'),'exec'),globals())
LATE_REAR='--late-rear' in sys.argv
SIDE_PATH='--side-path' in sys.argv
NOTCH_PATH='--notch-path' in sys.argv
SLOT_PATH='--deck-slot' in sys.argv
REFINED='--refined' in sys.argv
OUT_STEM='imu_refined_assembly' if REFINED else 'imu_slot_assembly' if SLOT_PATH else 'imu_notch_assembly' if NOTCH_PATH else 'imu_side_late_rear' if SIDE_PATH and LATE_REAR else 'imu_side_assembly' if SIDE_PATH else 'imu_late_rear' if LATE_REAR else 'imu_assembly'
INPUT_POOL=STAGE/('imu_refined_pools.json' if REFINED else 'imu_slot_pools.json' if SLOT_PATH else 'imu_notch_pools.json' if NOTCH_PATH else 'imu_side_pools.json' if SIDE_PATH else 'imu_wide_pools.json')
if '--pool' in sys.argv:
    INPUT_POOL=STAGE/sys.argv[sys.argv.index('--pool')+1]
    assert INPUT_POOL.parent==STAGE
if '--output-prefix' in sys.argv:
    OUT_STEM=sys.argv[sys.argv.index('--output-prefix')+1]
    assert Path(OUT_STEM).name==OUT_STEM
omitted=[]
if LATE_REAR:
    omitted=[n for n in up_solids if n in ['Rear_Interface_PCB','Power_Switch','USB_Receptacle','Plug_rear_J2','Plug_rear_J3'] or n.startswith('Rear_Interface_Screw_')]
    up_solids={n:m for n,m in up_solids.items() if n not in omitted}
steps=[(shellpose(15,0,14),Matrix.Translation((0,0,z))) for z in np.arange(0,18.01,.5)]
steps += [(shellpose(15,y,14),Matrix.Translation((0,y,18))) for y in np.linspace(0,-14,57)]
steps += [(shellpose(15,-14,z),Matrix.Translation((0,-14,z+4))) for z in np.arange(14.5,140.01,.5)]
steps += [(shellpose(15*u,0,14*u),Matrix.Identity(4)) for u in np.linspace(0,1,61)]
states=[];seen=set()
for sample,(u,b) in enumerate(steps):
    for group,tr in [(up_solids,u),(bridge_solids,b)]:
        mat=np.array(tr);inv=np.linalg.inv(mat)
        for name,m in group.items():
            key=(name,tuple(mat.round(8).ravel()))
            if key in seen:continue
            seen.add(key);bb=m.bounding_box();corners=np.array(list(itertools.product(*[(bb[i],bb[i+3]) for i in range(3)])))
            corners=corners@mat[:3,:3].T+mat[:3,3]
            states.append(dict(name=name,solid=m,inv=inv,lo=corners.min(0),hi=corners.max(0),sample=sample))
# Common early collision states reject candidates cheaply; all unique states
# remain in the screen. Results are finally checked with solid intersections.
states.sort(key=lambda r:(0 if r['name']=='Body_Upper' and r['sample']==0 else 1 if r['name'] in ['Rear_Interface_PCB','Plug_rear_J2','Plug_rear_J3'] else 2,r['sample']))
data=json.loads(INPUT_POOL.read_text());pools={};counts=[];t0=time.time()
def sample_path(points,step=.16):
    p=np.array(points);ds=np.linalg.norm(np.diff(p,axis=0),axis=1);cum=np.r_[0.,ds.cumsum()]
    arc=np.linspace(0,cum[-1],int(math.ceil(cum[-1]/step))+1)
    return np.array([np.interp(arc,cum,p[:,i]) for i in range(3)]).T,float(np.max(np.diff(arc))/2)
for pin,rows in data['pools'].items():
    passed=[];rejects=[]
    for idx,row in enumerate(rows):
        pts,coverage=sample_path(row['curve_mm']);clear=row['wire_OD_max_mm']/2+.02+.3+coverage+.0001
        lo=pts.min(0);hi=pts.max(0);fail=None
        for st in states:
            if np.any(hi+clear<st['lo']) or np.any(st['hi']+clear<lo):continue
            mask=np.all(pts>=st['lo']-clear,axis=1)&np.all(pts<=st['hi']+clear,axis=1)
            if not np.any(mask):continue
            inv=st['inv'];local=pts[mask]@inv[:3,:3].T+inv[:3,3]
            tree=trees[st['name']]
            for p in local:
                pos,norm,_,dist=tree.find_nearest(Vector(p))
                if dist<clear:
                    fail=dict(candidate_index=idx,object=st['name'],sample=st['sample'],point_local_mm=p.tolist(),reason='surface_clearance',distance_mm=float(dist),required_mm=clear);break
            if not fail and np.all(pts>=st['lo']) and np.all(pts<=st['hi']):
                p=pts[0]@inv[:3,:3].T+inv[:3,3]
                probe=manifold.Manifold.sphere(.01,16).translate(p.tolist())
                if (probe^st['solid']).volume()>probe.volume()*.5:
                    fail=dict(candidate_index=idx,object=st['name'],sample=st['sample'],point_local_mm=p.tolist(),reason='closed_solid_containment')
            if fail:break
        if fail:rejects.append(fail)
        else:passed.append(dict(row,source_candidate_index=idx))
    pools[pin]=passed
    counts.append(dict(pin=pin,input=len(rows),passed=len(passed),left=sum(r['route_side']=='left' for r in passed),right=sum(r['route_side']=='right' for r in passed),rejects=rejects))
    print('IMU_ASSEMBLY_FILTER',pin,len(rows),len(passed),counts[-1]['left'],counts[-1]['right'],time.time()-t0,flush=True)
    (STAGE/(OUT_STEM+'_filter_progress.json')).write_text(json.dumps(counts,ensure_ascii=False,indent=2)+'\n')
out=dict(revision=P['revision'],source_blend_sha256=source_hash,source_six_wire_sha256=data['source_six_wire_sha256'],
    source_pool_file=INPUT_POOL.name,source_pool_sha256=hashlib.sha256(INPUT_POOL.read_bytes()).hexdigest(),
    status='PASS' if all(pools.values()) else 'BLOCKED',scope='Individual curves screened against407 body positions; joint packing and full-solid recheck pending',
    pools=pools,search=counts,elapsed_s=time.time()-t0,main_modified=False,cut_lengths_released=False,
    late_rear_trial=LATE_REAR,components_deferred_to_later_installation=omitted,late_rear_installation='NOT_TESTED' if LATE_REAR else 'NOT_APPLICABLE',
    method='Surface-distance lower bound on connected complete curve; true closed-solid containment probe only when its entire AABB fits. Nearest-face-normal sign is not used.',
    limits=['Finite pre-existing candidate pool only; rejection is not proof no route exists.',
        'Wire shapes held fixed; no temporary flex, strain-relief or unmodeled branches approved.'])
if SLOT_PATH:out['candidate']=data['candidate']
(STAGE/(OUT_STEM+'_pools.json')).write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('IMU_ASSEMBLY_FILTER_DONE',out['status'],len(states),time.time()-t0,flush=True)

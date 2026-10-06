"""Combine two existing local anchor features with the current channel trial.

Read the feature solids explicitly, not historical host assemblies. Screen all
current source objects, connectors and fixed candidate wires at 130 poses.
"""
from pathlib import Path
import sys, json, time, itertools
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from current_context import RetentionContext, PROJECT, np, manifold, sha, cache, move, overlap_boxes, pose
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ctx=RetentionContext();started=time.time();A8=HERE.parent/'harness_A8'
specs={
 'yaw':dict(host='Pitch_Yoke',group='yaw',addition='cam_anchors/candidate_v3/addition.npz',
            band='cam_tie_install/oriented_band.npz',head='cam_tie_install/oriented_head.npz',
            zlow=229.9,zhigh=234.3,y=-1.5),
 'connector':dict(host='Pitch_Cradle',group='pitch',addition='cam_pitch_anchor/connector_anchor/addition.npz',
            band='cam_pitch_anchor/connector_anchor/z212.0_band.npz',head='cam_pitch_anchor/connector_anchor/z212.0_head.npz',
            zlow=209.6000061,zhigh=214.6000061,y=-20.8000001907)}
pieces={};relations={};construct=[]
for key,spec in specs.items():
    local={k:ctx.read(A8/spec[k]) for k in ['addition','band','head']}
    for k,m in local.items():
        name=key+'_'+k;pieces[name]=m;relations[name]=spec['group'];cache(HERE/(name+'.npz'),m)
    host=ctx.base[spec['host']];joined=host+local['addition']
    comps=[m.volume() for m in joined.decompose() if m.volume()>1e-7]
    row=dict(anchor=key,host=spec['host'],root_overlap_mm3=float((host^local['addition']).volume()),
             added_mm3=float((joined-host).volume()),removed_mm3=float((host-joined).volume()),
             joined_component_volumes_mm3=comps,kernel=str(joined.status()),
             tie_intersection_with_combined_host_mm3=float(((local['band']+local['head'])^joined).volume()))
    row['status']='PASS' if len(comps)==1 and row['root_overlap_mm3']>1. and abs(row['removed_mm3'])<1e-5 and abs(row['tie_intersection_with_combined_host_mm3'])<1e-5 else 'BLOCKED'
    construct.append(row);cache(HERE/(spec['host']+'.npz'),joined)

# Relative transforms remove redundant checks, but every one of the 130 poses
# is enumerated and mapped to the checked relative pose.
seen={};checked=[];pose_rows=[]
for yaw,pitch in itertools.product(range(-60,61,10),range(-20,26,5)):
    hits=[]
    for name,m in pieces.items():
        anchor=name.split('_')[0];host=specs[anchor]['host'];group=relations[name]
        inverse=np.linalg.inv(pose(group,yaw,pitch))
        for target,t in ctx.targets.items():
            if target==host:continue  # host contact checked explicitly above
            tg=ctx.groups[target];relative=inverse@pose(tg,yaw,pitch)
            key=(name,target,tuple(np.round(relative.flatten(),6)))
            if key in seen:
                if seen[key]:hits.append(seen[key])
                continue
            other=t if np.allclose(relative,np.eye(4),atol=1e-8) else t.transform(relative[:3,:])
            if not overlap_boxes(m,other,.3):seen[key]=None;continue
            v=float((m^other).volume());gap=float(m.min_gap(other,.31)) if v<1e-7 else 0.
            rec=dict(feature=name,target=target,yaw_deg=yaw,pitch_deg=pitch,intersection_mm3=v,gap_mm=gap)
            rec['status']='PASS' if v<1e-6 and gap>=.3-1e-5 else 'BLOCKED'
            checked.append(rec);seen[key]=rec if rec['status']=='BLOCKED' else None
            if rec['status']=='BLOCKED':hits.append(rec)
    # Different anchor groups must clear each other too.
    for left,right in itertools.product([n for n in pieces if n.startswith('yaw_')],[n for n in pieces if n.startswith('connector_')]):
        l=move(pieces[left],relations[left],yaw,pitch);r=move(pieces[right],relations[right],yaw,pitch)
        if not overlap_boxes(l,r,.3):continue
        v=float((l^r).volume());gap=float(l.min_gap(r,.31)) if v<1e-7 else 0.
        if v>1e-6 or gap<.3-1e-5:hits.append(dict(feature=left,target=right,intersection_mm3=v,gap_mm=gap))
    pose_rows.append(dict(yaw_deg=yaw,pitch_deg=pitch,status='BLOCKED' if hits else 'PASS',hits=hits))
    if pitch==25:print('ANCHOR_CURRENT_YAW',yaw,'blocked_poses',sum(r['status']=='BLOCKED' for r in pose_rows),flush=True)

# Deliberate clamp contact is restricted to the original straight sections.
# Elsewhere keep the same 0.3 mm nominal air clearance.
trees={n:BVHTree.FromPolygons(m.to_mesh64().vert_properties[:,:3],m.to_mesh64().tri_verts.tolist(),all_triangles=True) for n,m in pieces.items()}
wire_hits=[];grip_checks=[];wire_tests=0
for yaw,pitch in itertools.product(range(-60,61,10),range(-20,26,5)):
    for anchor,spec in specs.items():
        inv=np.linalg.inv(pose(spec['group'],yaw,pitch))
        for pin in range(1,5):
            p=ctx.curves[f'pin{pin}_y{yaw}_p{pitch}']@inv[:3,:3].T+inv[:3,3]
            ds=np.linalg.norm(np.diff(p,axis=0),axis=1)
            allowance=.3302+.3+np.maximum(np.r_[ds[0],ds],np.r_[ds,ds[-1]])/2+.0003+.0001
            grip=(np.abs(p[:,1]-spec['y'])<1e-4)&(p[:,2]>=spec['zlow']-1e-4)&(p[:,2]<=spec['zhigh']+1e-4)
            for name,m in pieces.items():
                if not name.startswith(anchor+'_'):continue
                bb=np.asarray(m.bounding_box());ids=np.flatnonzero(np.all(p>=bb[:3]-allowance[:,None],axis=1)&np.all(p<=bb[3:]+allowance[:,None],axis=1)&~grip)
                for i in ids:
                    distance=float(trees[name].find_nearest(Vector(p[i]))[3])
                    if distance<allowance[i]:
                        wire_hits.append(dict(anchor=anchor,feature=name,pin=pin,yaw_deg=yaw,pitch_deg=pitch,point_mm=p[i].tolist(),distance_mm=distance,required_mm=float(allowance[i])));break
                wire_tests+=1
            if yaw==0 and pitch==0:
                ids=np.flatnonzero(grip);assert len(ids)>1
                x=float(np.median(p[ids,0]));r=(.3302+.001)/np.cos(np.pi/64)
                tube=manifold.Manifold.cylinder(spec['zhigh']-spec['zlow'],r,circular_segments=64).translate([x,spec['y'],spec['zlow']])
                v=float((tube^sum((m for n,m in pieces.items() if n.startswith(anchor+'_')),manifold.Manifold())).volume())
                grip_checks.append(dict(anchor=anchor,pin=pin,straight_x_mm=x,intersection_mm3=v,status='PASS' if abs(v)<1e-6 else 'BLOCKED'))
    if pitch==25:print('ANCHOR_WIRES_YAW',yaw,'hits',len(wire_hits),flush=True)

ctx.assert_unchanged()
ok=not wire_hits and all(r['status']=='PASS' for r in construct+pose_rows+grip_checks)
result=dict(status='PASS' if ok else 'BLOCKED',scope='Two proposed integral anchors and two tie allocations on current channel alternatives',
            **ctx.evidence(),script_sha256=sha(__file__),context_sha256=sha(HERE/'current_context.py'),
            construction=construct,poses=pose_rows,head_poses=130,relative_source_tests=len(seen),close_checks=checked,
            wire_tests=wire_tests,wire_hits=wire_hits,grip_sweep_checks=grip_checks,
            added_printed_parts=0,added_ties=2,physical_tie_grip='NOT_TESTED',strength='NOT_TESTED',
            full_assembly='NOT_TESTED',body_fixed_retention='NOT_TESTED',other_seven_wires_and_FFC='NOT_TESTED',
            elapsed_s=time.time()-started)
(HERE/'anchors.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('ANCHOR_CURRENT_DONE',result['status'],'wire_hits',len(wire_hits),'construct',construct,flush=True)

"""Read back M1.49 against immutable approved C5 and all unmodified parts.

Current local wire clearance, side-wall samples and actual shell gaps are
rechecked. General current-model motion/assembly/stop tests run separately.
"""
import sys,time,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from validate import Solid,rigidtr
from validate_head_cleanup import geometry_record
from neck_reference import references,approved,saved_approved
from neck_capacity import local_curves,make_neck
from export import topology
from mathutils.bvhtree import BVHTree

def run(ss=None,check=None):
    start=time.time();q=P['neck_harness_capacity']
    if ss is None:
        load_collections();assembled();bpy.context.view_layer.update()
        ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.get('group') not in ['dock','coupon']}
    old=references();now={n:geometry_record(s.o) for n,s in ss.items()}
    changed=sorted(n for n in set(now)&set(old) if now[n]!=old[n]['record'])
    added=sorted(set(now)-set(old));removed=sorted(set(old)-set(now));ids=declared_neck_capacity_changes()
    failed=[];report={}
    def emit(key,ok,**data):
        report[key]={'status':'PASS' if ok else 'FAIL',**data}
        if not ok:failed.append(key)
        print('NECK_CHECK',key,report[key]['status'],flush=True)
    emit('scope',set(changed)==ids and not added and not removed,changed=changed,added=added,removed=removed,
         unchanged_count=len(now)-len(changed),compared_count=len(now))
    shapes=[]
    for n in sorted(ids):
        a=saved_approved(n);b=ss[n].m;t=topology(ss[n].v,ss[n].f.tolist())
        delta=max(0,(a-b).volume())+max(0,(b-a).volume())
        shapes.append(dict(id=n,symmetric_difference_mm3=delta,float64_to_saved32_difference_mm3=max(0,(approved(n)-a).volume())+max(0,(a-approved(n)).volume()),components=len(b.decompose()),topology=t))
    emit('approved_solids',all(r['symmetric_difference_mm3']<.003 and r['components']==1 and
         not any(r['topology'][k] for k in ['boundary_edges','nonmanifold_edges','inconsistent_edges','degenerate_triangles']) for r in shapes),
         rows=shapes,comparison_tolerance_mm3=.003,tolerance_scope='Actual saved mesh versus approved mesh quantized to the same float32 representation;5nm cleanup, not fit tolerance')
    pack,data,rows=local_curves(q);source=np.load(PROJECT/q['approved_candidate_directory']/'C4_packed_curves.npz')
    errors={k:float(np.max(np.abs(data[k]-source[k]))) if data[k].shape==source[k].shape else None for k in data}
    emit('config_derived_curves',all(e is not None and e<1e-10 for e in errors.values()),max_coordinate_error_mm=max(e for e in errors.values() if e is not None),count=len(errors))
    # Load explicit mating/route allocations without running historical studies.
    from harness_context import Context
    ctx=Context();original_targets=ctx.targets
    groups={n:s.group if s.group in ['yaw','pitch'] else 'body' for n,s in ss.items()}
    bygroup={g:{n:t for n,t in original_targets.items() if groups.get(n,'body')==g} for g in ['body','yaw','pitch']}
    wire_hits=[];checks=0;chord=max(r['chord_error_mm'] for r in rows)
    for i,slot in enumerate(pack['selected']):
        for yaw in range(-60,61,10):
            p=data[f'wire{i}_y{yaw}']
            for group,targets in bygroup.items():
                ctx.targets=targets
                for pitch in (range(-20,26,5) if group=='pitch' else [0]):
                    tr=np.linalg.inv(np.asarray(rigidtr(yaw,pitch if group=='pitch' else 0)))
                    pts=p if group=='body' else p@tr[:3,:3].T+tr[:3,3]
                    checks+=1;hit=ctx.clear(pts,chord_error=chord,radius=slot['OD_mm']/2)
                    if hit:wire_hits.append(dict(wire=i,yaw=yaw,pitch=pitch,group=group,**hit))
    ctx.targets=original_targets;ctx.assert_unchanged()
    emit('local_wire_clearance',not wire_hits,checks=checks,hits=wire_hits,source_inputs=ctx.sources,
         scope='11 planning conductors; complete endpoint routes and wired assembly incomplete')
    _,outer,inner,params=make_neck(pack,data,q)
    sides=[]
    for name,m in [('inner',inner),('outer',outer)]:
        mesh=m.simplify(q['construction']['simplify_mm']).to_mesh64();v=mesh.vert_properties[:,:3];f=mesh.tri_verts
        f=f[np.ptp(v[f][:,:,2],axis=1)>1e-6]
        sides.append((v,f,BVHTree.FromPolygons(v,f.tolist(),all_triangles=True)))
    wall=[]
    for i,(v,f,tree) in enumerate(sides):
        pts=np.vstack([v[np.unique(f)],np.mean(v[f],axis=1)])
        pts=pts[(pts[:,2]>=157.)&(pts[:,2]<=173.1)]
        best=min((float(sides[1-i][2].find_nearest(Vector(p))[3]),p.tolist()) for p in pts)
        wall.append(dict(direction='inner_to_outer' if i==0 else 'outer_to_inner',samples=len(pts),minimum_mm=best[0],point_mm=best[1]))
    emit('generated_side_wall',min(r['minimum_mm'] for r in wall)>=2.2,rows=wall,qualified_global_minimum=None,
         scope='Finite nearest-side samples of approved generated neck, excludes endcaps; not strength proof')
    gaps=[]
    for shellname in ['Head_Front','Head_Rear']:
        for pitch in range(-20,26,5):
            shell=ss[shellname].m.transform(np.asarray(rigidtr(0,pitch))[:3,:])
            gaps.append(dict(part='Pitch_Yoke',shell=shellname,yaw=0,pitch=pitch,gap_mm=float(ss['Pitch_Yoke'].m.min_gap(shell,5))))
            for yaw in range(-60,61,10):
                shell=ss[shellname].m.transform(np.asarray(rigidtr(yaw,pitch))[:3,:])
                for part in ['Yaw_Base','Yaw_Anti_Lift_Keeper']:
                    gaps.append(dict(part=part,shell=shellname,yaw=yaw,pitch=pitch,gap_mm=float(ss[part].m.min_gap(shell,5))))
    emit('head_shell_gaps',min(r['gap_mm'] for r in gaps)>=.3,minimum=min(gaps,key=lambda r:r['gap_mm']),rows=gaps)
    receipt=json.loads((PROJECT/q['approval_record']).read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    drift=[n for n,h in receipt['protected_hardware'].items() if sha(PROJECT/n)!=h]
    emit('hardware_preserved',not drift,count=len(receipt['protected_hardware']),changed=drift)
    report.update(revision=P['revision'],status='PASS' if not failed else 'FAIL',failed=failed,
                  source_blend_sha256=sha(Path(bpy.data.filepath)),elapsed_s=time.time()-start,
                  full_harness='BLOCKED',physical_fit='NOT_TESTED',strength='NOT_TESTED',manufacturing_release=False)
    save_json(ROOT/'reports/neck_capacity_validation.json',report)
    if check:check('approved_neck_capacity',report['status'],'已采用6806轴承和三件颈部支撑；范围、局部走线、孔壁与头壳净距检查',{'report':'neck_capacity_validation.json','failed':failed})
    return report

if __name__=='__main__':
    if run()['status']!='PASS':raise SystemExit(1)

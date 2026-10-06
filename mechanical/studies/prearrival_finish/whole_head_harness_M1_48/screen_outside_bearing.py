"""Bounded alternate local corridor, preserving the central socket and journal.

This only screens mathematical curves. Preserved material is an explicit
geometric design constraint, not a new strength acceptance rule. All source
solids and hardware-owned files are read-only.
"""
from pathlib import Path
import sys,json,time,collections
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent/'outer_harness_M1_48'));sys.path.insert(0,str(HERE))
from native_context import Context,np,sha,manifold
from validate import rigidtr
from neck_family import family,rotate
ctx=Context();started=time.time();native=ctx.targets.copy();hosts={'Yaw_Base','Pitch_Yoke'}
groups={n:s.group if s.group in ['yaw','pitch'] else 'body' for n,s in ctx.ss.items()}
targets={g:{n:t for n,t in native.items() if n not in hosts and groups.get(n,'body')==g} for g in ['body','yaw','pitch']}
# Keep every native bit inside R18 mm, including the D socket and entire yaw
# journal. Prospective channels elsewhere still require their own host review.
protected=manifold.Manifold.cylinder(300,18,18,144).translate([0,0,0])
for name in sorted(hosts):
    material=ctx.ss[name].m^protected
    targets[groups[name]]['PRESERVE_'+name+'_R18']=ctx.target(material)

rows=[];curves={};refs=[]
for radius in [19.5,20.5]:
    middle=family(120.,195.,radius)
    minimum=min(r['sampled_min_radius_mm'] for r in middle)
    assert minimum>=14.9352
    refs.append(dict(radius_mm=radius,z_mm=[120.,195.],length_mm=middle[0]['model_length_mm'],minimum_sampled_bend_mm=minimum))
    for row in middle:curves[f'r{radius}_y{row["yaw_deg"]}']=row['points']
    for kind,od in [('signal',.6604),('power_sample',1.4224)]:
        for angle in range(0,360,5):
            hit=None;tests=0
            for row in middle:
                yaw=row['yaw_deg'];p=rotate(row['points'],angle)
                for group,objects in targets.items():
                    ctx.targets=objects
                    for pitch in (range(-20,26,5) if group=='pitch' else [0]):
                        if group=='body':local=p
                        else:
                            tr=np.linalg.inv(np.asarray(rigidtr(yaw,pitch)))
                            local=p@tr[:3,:3].T+tr[:3,3]
                        tests+=1;hit=ctx.clear(local,row['chord_error_mm'],radius=od/2)
                        if hit:
                            hit.update(yaw_deg=yaw,pitch_deg=pitch,frame=group+'_zero_pose');break
                    if hit:break
                if hit:break
            rows.append(dict(radius_mm=radius,kind=kind,OD_mm=od,angle_deg=angle,
                status='BLOCKED' if hit else 'PASS',relative_group_checks=tests,hit=hit))
        print('OUTSIDE_BEARING',radius,kind,'passes',sum(r['status']=='PASS' for r in rows if r['radius_mm']==radius and r['kind']==kind),flush=True)
ctx.targets=native;ctx.assert_unchanged()
np.savez_compressed(HERE/'outside_bearing_curves.npz',**curves)
out=dict(status='PASS' if any(r['status']=='PASS' for r in rows) else 'BLOCKED',
    scope='Bounded local alternate corridor only, not an eleven-wire assembled harness',
    source_main_sha256=ctx.source_hash,script_sha256=sha(__file__),helper_sha256=sha(HERE/'neck_family.py'),
    source_context_sha256=sha(HERE.parent/'outer_harness_M1_48/native_context.py'),
    protected_native_material_radius_mm=18.,prospective_channel_hosts=sorted(hosts),
    native_parts=209,mates=29,static_candidate_wires=14,head_poses=130,
    references=refs,rows=rows,blockers=dict(collections.Counter(r['hit']['object'] for r in rows if r['hit'])),
    curves_sha256=sha(HERE/'outside_bearing_curves.npz'),
    unchanged_material_constraint='Every native point inside R18 of both possible channel hosts is retained.',
    wire_selection='BLOCKED',simultaneous_eleven_routes='NOT_TESTED',host_design='NOT_TESTED',
    full_paths='NOT_TESTED',anchors='NOT_TESTED',installation='NOT_TESTED',
    dynamic_wire_qualification='NOT_TESTED',main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,
    limitations=['Power_sample is only a planning OD, not a selected or GH-compatible conductor.',
        'Both endpoints remain staging points. All native hardware and mating allocations remain obstacles.',
        'Failure of these finite families is not proof that all outer routes are impossible.'],elapsed_s=time.time()-started)
(HERE/'outside_bearing_screen.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('OUTSIDE_DONE',out['status'],out['blockers'],round(out['elapsed_s'],1),flush=True)

"""Screen local up-shifted flex curves through the existing keeper's rear gap.

No changes to main. Two explicitly named possible channel hosts may be altered
only outside R18. All native material inside R18, the entire keeper, bearing,
reaction hardware, servos, electronics and other prints remain obstacles.
"""
from pathlib import Path
import sys,json,time,collections
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent/'outer_harness_M1_48'))
sys.path.insert(0,str(HERE.parent/'whole_head_harness_M1_48'))
from native_context import Context,np,sha,manifold
from validate import rigidtr
from neck_family import family,rotate
ctx=Context();started=time.time();native=ctx.targets.copy();hosts={'Yaw_Base','Pitch_Yoke'}
groups={n:s.group if s.group in ['yaw','pitch'] else 'body' for n,s in ctx.ss.items()}
targets={g:{n:t for n,t in native.items() if n not in hosts and groups.get(n,'body')==g} for g in ['body','yaw','pitch']}
protected=manifold.Manifold.cylinder(300,18,18,192)
protected_solids={}
for name in sorted(hosts):
    material=ctx.ss[name].m^protected
    protected_solids[name]=material
    targets[groups[name]]['PRESERVE_'+name+'_R18']=ctx.target(material)
inverse={(group,yaw,pitch):np.linalg.inv(np.asarray(rigidtr(yaw,pitch if group=='pitch' else 0)))
    for group in ['yaw','pitch'] for yaw in range(-60,61,10) for pitch in range(-20,26,5)}
rows=[];curves={};refs=[]
for bottom in [130.,135.,140.]:
    for radius in [19.5,22.5,25.5]:
        fid=f'Z{int(bottom)}_R{radius}'
        middle=family(bottom,bottom+85.,radius)
        minimum=min(r['sampled_min_radius_mm'] for r in middle);assert minimum>=14.9352
        refs.append(dict(id=fid,radius_mm=radius,z_mm=[bottom,bottom+85.],
            length_mm=middle[0]['model_length_mm'],minimum_sampled_bend_mm=minimum,
            chord_error_mm=max(r['chord_error_mm'] for r in middle)))
        for row in middle:curves[f'{fid}_y{row["yaw_deg"]}']=row['points']
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
                                tr=inverse[group,yaw,pitch];local=p@tr[:3,:3].T+tr[:3,3]
                            tests+=1;hit=ctx.clear(local,row['chord_error_mm'],radius=od/2)
                            if hit:
                                hit.update(yaw_deg=yaw,pitch_deg=pitch,frame=group+'_zero_pose');break
                        if hit:break
                    if hit:break
                rows.append(dict(family=fid,kind=kind,OD_mm=od,angle_deg=angle,
                    status='BLOCKED' if hit else 'PASS',relative_group_checks=tests,hit=hit))
            print('KEEPER_SCREEN',fid,kind,'passes',sum(r['status']=='PASS' for r in rows if r['family']==fid and r['kind']==kind),
                'seconds',round(time.time()-started,1),flush=True)
ctx.targets=native;ctx.assert_unchanged()
np.savez_compressed(HERE/'curves.npz',**curves)
out=dict(status='PASS' if any(r['status']=='PASS' for r in rows) else 'BLOCKED',
    scope='Bounded local flex paths through native keeper opening, not a complete harness',
    source_main_sha256=ctx.source_hash,sources=ctx.sources,script_sha256=sha(__file__),
    helper_sha256=sha(HERE.parent/'whole_head_harness_M1_48/neck_family.py'),
    candidate_channel_hosts=sorted(hosts),preserved_native_material_radius_mm=18.,
    native_parts=209,mates=29,static_candidate_wires=14,head_poses=130,
    references=refs,rows=rows,blockers=dict(collections.Counter(r['hit']['object'] for r in rows if r['hit'])),
    curves_sha256=sha(HERE/'curves.npz'),
    relevant_bounds_mm={n:list(s.m.bounding_box()) for n,s in ctx.ss.items() if n in hosts or n in [
        'Yaw_Anti_Lift_Keeper','Yaw_Bearing','Yaw_Reaction_Link','Yaw_Servo','Pitch_Servo','CAM_Board','Power_Module','Head_Rear','Pitch_Cradle']},
    source_geometry_changed=False,main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,
    simultaneous_eleven_paths='NOT_TESTED',channels='NOT_TESTED',endpoints='NOT_TESTED',
    strength='NOT_TESTED',installation='NOT_TESTED',wire_selection='BLOCKED',
    limitations=['Only local curves with temporary end planes, not final connector paths.',
        'The other seven conductor sizes remain an explicit1.4224mm planning OD, not GH-compatible wire selection.',
        'Native keeper is wholly retained; no print is edited by this script.',
        'Finite pose and nominal curve checks do not prove continuous motion or flex fatigue.'],elapsed_s=time.time()-started)
(HERE/'screen.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('KEEPER_SCREEN_DONE',out['status'],out['blockers'],round(out['elapsed_s'],1),flush=True)

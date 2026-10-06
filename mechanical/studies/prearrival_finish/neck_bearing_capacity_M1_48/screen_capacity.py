"""Independent capacity comparison for a larger documented yaw bearing.

Native hardware is never scaled. The old bearing is replaced *in this screen*
by a separate 30x42x7 catalogue boundary. Three print hosts are explicitly
prospective designs, constrained by preserved socket/web and trial interfaces.
This is not an adopted or fully designed four-part replacement.
"""
from pathlib import Path
import sys,json,time,math,collections
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent/'outer_harness_M1_48'));sys.path.insert(0,str(HERE))
from native_context import Context,np,sha,manifold
from validate import rigidtr
from tapered_family import family,rotate
ctx=Context();started=time.time();native=ctx.targets.copy()
hosts={'Yaw_Base','Pitch_Yoke','Yaw_Anti_Lift_Keeper'}
groups={n:s.group if s.group in ['yaw','pitch'] else 'body' for n,s in ctx.ss.items()}
targets={g:{n:t for n,t in native.items() if n not in hosts|{'Yaw_Bearing'} and groups.get(n,'body')==g} for g in ['body','yaw','pitch']}
def cyl(r,a,b):return manifold.Manifold.cylinder(b-a,r,r,192).translate([0,0,a])
def box(a,b):return manifold.Manifold.cube(tuple(np.array(b)-a)).translate(a)
def ring(ro,ri,a,b):return cyl(ro,a,b)-cyl(ri,a-.01,b+.01)

socket=ctx.ss['Yaw_Base'].m^cyl(9.5,137.,147.01)
web=ctx.ss['Yaw_Base'].m^box((-4,-36,137.),(4,36,148.5))
outside_base=ctx.ss['Yaw_Base'].m-cyl(33,137.,170.)
outside_yoke=ctx.ss['Pitch_Yoke'].m-cyl(22,148.9,195.)
bearing=ring(21,15,149,156)
journal=ring(14.95,12.6,149.4,156)+ring(16,12.6,156,156.85)
housing=ring(27,21.05,149,156.3)+ring(27,20,147.,149)
keeper=(ctx.ss['Yaw_Anti_Lift_Keeper'].m-cyl(17.45,159.5,163.7)
    -box((-17.45,-40,159.5),(17.45,0,163.7)))
constraints={
    'body':{'PRESERVE_SOCKET':socket,'PRESERVE_TWO_WEBS':web,'PRESERVE_OUTSIDE_BASE':outside_base,
        'CANDIDATE_6806ZZ_BOUNDARY':bearing,'CANDIDATE_HOUSING':housing,'CANDIDATE_KEEPER':keeper},
    'yaw':{'PRESERVE_UPPER_YOKE':outside_yoke,'CANDIDATE_JOURNAL':journal}}
for g,objects in constraints.items():
    for n,m in objects.items():targets[g][n]=ctx.target(m)
inverse={(group,yaw,pitch):np.linalg.inv(np.asarray(rigidtr(yaw,pitch if group=='pitch' else 0)))
    for group in ['yaw','pitch'] for yaw in range(-60,61,10) for pitch in range(-20,26,5)}
rows=[];curves={};refs=[]
for bottom,radius,flare in [(130.,10.6,173.),(134.,10.6,173.),(138.,10.6,173.),(130.,11.3,173.),(134.,11.3,173.),(138.,11.3,173.)]:
    fid=f'Z{int(bottom)}_R{radius}_F{int(flare)}'
    middle=family(z0=bottom,r0=radius,flare_start=flare)
    minimum=min(r['minimum_sampled_bend_mm'] for r in middle);assert minimum>=14.9352
    refs.append(dict(id=fid,z_mm=[bottom,200.],radii_mm=[radius,15.2],flare_start_mm=flare,flare_bend_radius_mm=30.,
        length_mm=middle[0]['length_mm'],minimum_sampled_bend_mm=minimum,
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
            rows.append(dict(family=fid,kind=kind,OD_mm=od,angle_deg=angle,status='BLOCKED' if hit else 'PASS',
                relative_group_checks=tests,hit=hit))
        print('BEARING_CAPACITY',fid,kind,'passes',sum(r['status']=='PASS' for r in rows if r['family']==fid and r['kind']==kind),
            'seconds',round(time.time()-started,1),flush=True)
ctx.targets=native;ctx.assert_unchanged()
np.savez_compressed(HERE/'curves.npz',**curves)
for group,objects in constraints.items():
    for n,m in objects.items():
        mesh=m.to_mesh64();np.savez_compressed(HERE/(n+'.npz'),vertices_mm=np.asarray(mesh.vert_properties[:,:3]),triangles=np.asarray(mesh.tri_verts))
out=dict(status='PASS' if any(r['status']=='PASS' for r in rows) else 'BLOCKED',
    scope='Local capacity screen with three explicitly provisional print hosts and a separate larger bearing reference',
    source_main_sha256=ctx.source_hash,sources=ctx.sources,script_sha256=sha(__file__),helper_sha256=sha(HERE/'tapered_family.py'),
    bearing_reference=dict(old='NSK6804ZZ20x32x7',candidate='NSK6806ZZ30x42x7',data_status='VENDOR_DOCUMENTED boundary only',
        source='https://www.nsk.com/in-en/engineering/products/bearings/ball-bearings/deep-groove-ball-bearings/single-row-deep-groove-ball-bearings/6806zz-apn.html'),
    candidate_print_hosts=sorted(hosts),preserved_socket_radius_mm=9.5,preserved_web_width_mm=8.,
    proposed_journal_outer_inner_r_mm=[14.95,12.6],prospective_journal_wall_mm=2.35,
    native_parts=209,mates=29,static_candidate_wires=14,head_poses=130,
    references=refs,rows=rows,blockers=dict(collections.Counter(r['hit']['object'] for r in rows if r['hit'])),
    curves_sha256=sha(HERE/'curves.npz'),constraint_names={g:list(v) for g,v in constraints.items()},
    candidate_solids_full_design='NOT_TESTED',candidate_parts_motion='NOT_TESTED',full_11_wire_packing='NOT_TESTED',
    fixed_stop_relocation='NOT_TESTED',full_paths='NOT_TESTED',installation='NOT_TESTED',strength='NOT_TESTED',
    source_geometry_changed=False,main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,
    limitations=['This changes the bearing model and requires three print redesigns, not scaling the current hardware.',
        'Only local curves. Their endpoints are staging points, not all actual connector exits.',
        'The trial interface shells are explicit constraint geometry, not fully connected printable parts.',
        'Current reaction socket and two original bridge web strips are protected; all other native hardware retained.',
        'The seven larger wires remain unselected planning allocations, not approved conductor/terminal combinations.'],elapsed_s=time.time()-started)
(HERE/'screen.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('BEARING_CAPACITY_DONE',out['status'],out['blockers'],round(out['elapsed_s'],1),flush=True)

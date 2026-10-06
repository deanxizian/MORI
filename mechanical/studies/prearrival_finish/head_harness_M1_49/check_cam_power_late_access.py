"""Screen external approach to J18 for a proposed later-installation stage.

Current housing allocation only. Record mating-board intersections separately;
they remain unresolved, never removed from the complete assembly verdict.
"""
from pathlib import Path
import json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=HERE/'remaining_routes'
OUT=BASE/'cam_restraints/power_late_access';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import manifold
ctx=Context();start=time.time();key='power_J18';plug=ctx.plug[key];port=ctx.port_pins[key]
axis=np.asarray(port['axis']);axis/=np.linalg.norm(axis)
print('J18_PORT',ctx.portrows[key],port,flush=True)
initial=[];board_names=[]
for name,target in ctx.targets.items():
    if name=='Plug_'+key:continue
    if 'Power' in name:board_names.append(name)
    if not(np.all(plug.lo<=target['hi']) and np.all(plug.hi>=target['lo'])):continue
    overlap=float((plug.m^target['m']).volume())
    if abs(overlap)>1e-6:initial.append(dict(target=name,overlap_mm3=overlap))
print('J18_INITIAL',initial,'POWER_OBJECTS',board_names,flush=True)
cases=[]
for stage,deferred in [('body_closed',set()),('body_shells_before_install',{'Body_Upper','Body_Lower'})]:
    rows=[];first=None;board_hits=[];end=0.
    for distance in np.arange(0.,30.,.25):
        vertices=np.vstack([plug.v+distance*axis,plug.v+(distance+.25)*axis])
        hull=manifold.Manifold.hull_points(vertices);box=np.asarray(hull.bounding_box());hits=[]
        for name,target in ctx.targets.items():
            if name in deferred or name=='Plug_'+key:continue
            if not(np.all(box[:3]<=target['hi']+.301) and np.all(box[3:]+.301>=target['lo'])):continue
            v=float((hull^target['m']).volume());gap=float(hull.min_gap(target['m'],.301)) if abs(v)<1e-7 else 0.
            if abs(v)>1e-6 or gap<.3-1e-5:
                hit=dict(target=name,overlap_mm3=v,gap_mm=gap,interval_mm=[float(distance),float(distance+.25)])
                if name in board_names:board_hits.append(hit)
                else:hits.append(hit)
        rows.append(dict(distance_mm=float(distance),external_hits=hits));end=float(distance+.25)
        if hits:
            first=rows[-1];a=hull.to_mesh64();np.savez_compressed(OUT/(stage+'_blocked.npz'),vertices_mm=a.vert_properties[:,:3],triangles=a.tri_verts);break
    cases.append(dict(stage=stage,status='BLOCKED' if first else 'PASS',scope='External approach excluding unresolved mating-board intersection',
        deferred=sorted(deferred),checked_distance_mm=end,planned_distance_mm=30.,first_external_conflict=first,mating_board_hits=board_hits,rows=rows))
    print('J18_APPROACH',stage,first,'distance',end,flush=True)
ctx.assert_unchanged()
r=dict(status='BLOCKED' if all(c['status']=='BLOCKED' for c in cases) else 'PASS',
    scope='Proposed J18 housing external approach screening only; complete later mating/wire installation remains BLOCKED',
    sources=ctx.sources,inputs={},portrow=ctx.portrows[key],axis=axis.tolist(),pins={str(k):v.tolist() for k,v in port['pins'].items()},
    nominal_plug_bounds_mm=np.r_[plug.lo,plug.hi].tolist(),initial_overlaps=initial,mating_board_names=board_names,cases=cases,
    mating_board_contact_qualification='BLOCKED',attached_wires='NOT_TESTED',upper_wire_sequence='NOT_TESTED',
    main_changed=False,full_harness='BLOCKED',Yaw_Reaction_Link_present=True,approved=False,
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-start)
(OUT/'review.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('CAM_POWER_LATE_ACCESS_DONE',r['status'],r['elapsed_s'],flush=True)

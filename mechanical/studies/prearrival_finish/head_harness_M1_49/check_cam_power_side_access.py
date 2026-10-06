"""Screen external approach to J18 for a proposed later-installation stage.

Current housing allocation only. Record mating-board intersections separately;
they remain unresolved, never removed from the complete assembly verdict.
"""
from pathlib import Path
import json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=HERE/'remaining_routes'
OUT=BASE/'cam_restraints/power_side_access';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import manifold
ctx=Context();start=time.time();key='power_J18';plug=ctx.plug[key];port=ctx.port_pins[key]
axis=np.asarray(port['axis']);axis/=np.linalg.norm(axis)
print('J18_PORT',ctx.portrows[key],port,flush=True)
initial=[];board_names=[]
for name,target in ctx.targets.items():
    if name=='Plug_'+key:continue
    if name=='Power_Module':board_names.append(name)
    if not(np.all(plug.lo<=target['hi']) and np.all(plug.hi>=target['lo'])):continue
    overlap=float((plug.m^target['m']).volume())
    if abs(overlap)>1e-6:initial.append(dict(target=name,overlap_mm3=overlap))
print('J18_INITIAL',initial,'POWER_OBJECTS',board_names,flush=True)
cases=[]
for stage,deferred in [('body_closed',set()),('body_shells_before_install',{'Body_Upper','Body_Lower'})]:
 for direction,delta in [('rear',np.array([0.,-60.,0.])),('front',np.array([0.,60.,0.])),('left',np.array([-60.,0.,0.])),('right',np.array([60.,0.,0.]))]:
    waypoints=np.array([np.zeros(3),axis*12,axis*12+delta]);rows=[];first=None;board_hits=[];checked=0
    for segment,(a,b) in enumerate(zip(waypoints,waypoints[1:])):
      points=np.linspace(a,b,int(np.ceil(np.linalg.norm(b-a)/.5))+1)
      for i,(u,v) in enumerate(zip(points,points[1:])):
        hull=manifold.Manifold.hull_points(np.vstack([plug.v+u,plug.v+v]));box=np.asarray(hull.bounding_box());hits=[]
        for name,target in ctx.targets.items():
            if name in deferred or name=='Plug_'+key:continue
            if not(np.all(box[:3]<=target['hi']+.301) and np.all(box[3:]+.301>=target['lo'])):continue
            volume=float((hull^target['m']).volume());gap=float(hull.min_gap(target['m'],.301)) if abs(volume)<1e-7 else 0.
            if abs(volume)>1e-6 or gap<.3-1e-5:
                hit=dict(target=name,overlap_mm3=volume,gap_mm=gap,start_shift_mm=u.tolist(),end_shift_mm=v.tolist())
                if segment==0 and name=='Power_Module':board_hits.append(hit)
                else:hits.append(hit)
        rows.append(dict(segment=segment,step=i,external_hits=hits));checked+=1
        if hits:
            first=rows[-1];m=hull.to_mesh64();np.savez_compressed(OUT/(stage+'_'+direction+'_blocked.npz'),vertices_mm=m.vert_properties[:,:3],triangles=m.tri_verts);break
      if first:break
    cases.append(dict(stage=stage,direction=direction,status='BLOCKED' if first else 'PASS',scope='External approach; only intended mating-board intersection excluded during initial axial withdrawal',
        deferred=sorted(deferred),waypoints_mm=waypoints.tolist(),continuous_translation_intervals=checked,
        first_external_conflict=first,mating_board_hits=board_hits,rows=rows))
    print('J18_SIDE_APPROACH',stage,direction,'BLOCKED' if first else 'PASS',first,flush=True)
ctx.assert_unchanged()
r=dict(status='PASS' if any(c['status']=='PASS' for c in cases) else 'BLOCKED',
    scope='J18 allocation lifted 12 mm then translated sideways; no attached wires or complete mating qualification',
    sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in [HERE/'check_cam_power_late_access.py',BASE/'cam_restraints/power_late_access/review.json']},
    portrow=ctx.portrows[key],axis=axis.tolist(),pins={str(k):v.tolist() for k,v in port['pins'].items()},
    nominal_plug_bounds_mm=np.r_[plug.lo,plug.hi].tolist(),initial_overlaps=initial,cases=cases,
    correction='Only Power_Module is treated as the intended mate, only during initial axial withdrawal; all mounting screws and inserts remain obstacles',
    mating_board_contact_qualification='BLOCKED',attached_wires='NOT_TESTED',upper_wire_sequence='NOT_TESTED',
    main_changed=False,full_harness='BLOCKED',Yaw_Reaction_Link_present=True,approved=False,
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-start)
(OUT/'review.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('CAM_POWER_SIDE_ACCESS_DONE',r['status'],r['elapsed_s'],flush=True)

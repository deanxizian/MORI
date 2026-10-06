"""Look for an open upper-shell pose around the installed inner head.

Rigid bodies only. In particular the rear-board harness is not rigidly fixed
while its shell moves, so the 14 historic wire solids are not a motion proof.
"""
from pathlib import Path
import itertools,json,math,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes';REST=BASE/'cam_restraints';OUT=REST/'inner_head_body_access'
OUT.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import manifold,D
from validate import rigidtr
from interface_completion import axial
from mathutils import Matrix,Vector
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text())
source=REST/'inner_head_lowering/review.json';prior=read(source)
for f,h in {**prior['sources'],**prior['inputs']}.items():assert sha(ROOT/f)==h,f
sf=REST/'head_module_sequence_v2/review.json';stage=read(sf);upper=set(stage['moving_upper_module'])
inputs=[source,sf,ROOT/'mechanical/scripts/interface_completion.py',ROOT/'mechanical/scripts/validate.py']
absent=set(prior['rows'][1]['not_yet_installed'])|{'Body_Lower'}|{n for n in ctx.ss if n.startswith(('Frame_Screw_','Shell_Screw_'))}
geometry={n:s.m for n,s in ctx.ss.items() if n not in absent};groups={n:s.group for n,s in ctx.ss.items()}
for n,p,g in [('Yaw_Base',BASE/'c6_left_slot_entry/Yaw_Base_candidate.npz','body'),
              ('Pitch_Yoke',REST/'sliding_guide_v4/Pitch_Yoke_candidate.npz','yaw'),
              ('Pitch_Cradle',REST/'return_clamp_v3/Pitch_Cradle_candidate.npz','pitch'),
              ('connector_band',REST/'return_clamp_v3/band.npz','pitch'),('connector_head',REST/'return_clamp_v3/head.npz','pitch')]:
    inputs.append(p);a=np.load(p);geometry[n]=manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles'].astype(np.uint64)));groups[n]=g
geometry.update({'Plug_'+n:s.m for n,s in ctx.plug.items()});upper|={'Plug_rear_J2','Plug_rear_J3'}
origin=Vector((0,0,D['body_z']));driver=axial(1.25,100.,[0,60.3,142.5],[0,1,0])
def pose(angle,dy,dz):
    return np.asarray(Matrix.Translation((0,dy,dz))@Matrix.Translation(origin)@Matrix.Rotation(math.radians(angle),4,'X')@Matrix.Translation(-origin))[:3,:]
def collision(m,fixed,boxes):
    bb=np.asarray(m.bounding_box())
    for n,t in fixed.items():
        tb=boxes[n]
        if np.any(bb[3:]<tb[:3]) or np.any(tb[3:]<bb[:3]):continue
        v=float((m^t).volume())
        if abs(v)>1e-5:return dict(target=n,overlap_mm3=v)
    return None
endpoints=[];clear=[];tested=0
params=list(itertools.product([15.,20.,25.,30.,35.,40.],[-16.,-8.,0.,8.,16.],[0.,4.,8.,12.,16.,20.]))
for angle,dy,dz in params:
    tr=pose(angle,dy,dz);moved={n:geometry[n].transform(tr) for n in upper}
    mb={n:np.asarray(m.bounding_box()) for n,m in moved.items()};toolhit=collision(driver,moved,mb)
    if toolhit:
        endpoints.append(dict(angle_deg=angle,y_mm=dy,z_mm=dz,status='BLOCKED',stage='driver_against_upper_module',failure=toolhit));continue
    for yaw in [0.,-60.,60.]:
        yawtr=np.asarray(rigidtr(yaw,0))[:3,:]
        fixed={n:(m.transform(yawtr) if groups.get(n) in ['yaw','pitch'] else m) for n,m in geometry.items() if n not in upper}
        fb={n:np.asarray(m.bounding_box()) for n,m in fixed.items()};first=None;tested+=1
        for n,m in moved.items():
            hit=collision(m,fixed,fb)
            if hit:first=dict(moving=n,**hit);break
        row=dict(angle_deg=angle,y_mm=dy,z_mm=dz,head_yaw_deg=yaw,status='BLOCKED' if first else 'PASS',stage='upper_against_fixed_robot',failure=first)
        endpoints.append(row)
        if not first:clear.append(row);print('BODY_ACCESS_CLEAR',row,flush=True)
    if tested%30==0:print('BODY_ACCESS_PROGRESS',len(endpoints),len(clear),flush=True)
ctx.assert_unchanged()
r=dict(status='PASS' if clear else 'BLOCKED',scope='Finite rigid shell-pose and nominal straight-driver screen, not a connected path or wired assembly',
    sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},upper_module=sorted(upper),absent=sorted(absent),
    parameter_count=len(params),endpoint_records=len(endpoints),upper_robot_tests=tested,clear=clear,rows=endpoints,
    driver='ASSUMED diameter2.5 x100mm; no handle, engagement or torque qualification',
    full_path='NOT_TESTED',wire_deformation='NOT_TESTED',other_body_angles='NOT_TESTED',
    main_changed=False,approved=False,C6_main_applied=False,full_harness='BLOCKED',Yaw_Reaction_Link_present=True,
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('INNER_HEAD_BODY_ACCESS_DONE',r['status'],len(clear),r['elapsed_s'],flush=True)

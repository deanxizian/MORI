"""Inspect the unresolved reaction-link operation in the inner-head sequence.

Read-only candidate studies. Actual screws/nuts are swept at finite samples;
the driver is a nominal straight allocation, not a selected physical tool.
"""
from pathlib import Path
import json, math, sys, time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes';REST=BASE/'cam_restraints';OUT=REST/'reaction_link_order'
OUT.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import manifold,D
from validate import rigidtr
from interface_completion import axial
from mathutils import Matrix,Vector
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text())
source=REST/'inner_head_lowering/review.json';prior=read(source)
for f,h in {**prior['sources'],**prior['inputs']}.items():assert sha(ROOT/f)==h,f
inputs=[source,ROOT/'mechanical/scripts/interface_completion.py',ROOT/'mechanical/scripts/validate.py']
absent=set(prior['rows'][1]['not_yet_installed'])
geometry={n:s.m for n,s in ctx.ss.items()};groups={n:s.group for n,s in ctx.ss.items()}
for n,p,g in [('Yaw_Base',BASE/'c6_left_slot_entry/Yaw_Base_candidate.npz','body'),
              ('Pitch_Yoke',REST/'sliding_guide_v4/Pitch_Yoke_candidate.npz','yaw'),
              ('Pitch_Cradle',REST/'return_clamp_v3/Pitch_Cradle_candidate.npz','pitch'),
              ('connector_band',REST/'return_clamp_v3/band.npz','pitch'),
              ('connector_head',REST/'return_clamp_v3/head.npz','pitch')]:
    inputs.append(p);a=np.load(p);geometry[n]=manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles'].astype(np.uint64)));groups[n]=g

def hits(m,fixed):
    bb=np.asarray(m.bounding_box());out=[]
    for n,t in fixed.items():
        tb=np.asarray(t.bounding_box())
        if np.any(bb[3:]<tb[:3]) or np.any(tb[3:]<bb[:3]):continue
        overlap=m^t;v=float(overlap.volume())
        if abs(v)>1e-5:out.append(dict(target=n,overlap_mm3=v,bounds_mm=list(overlap.bounding_box())))
    return out

# This first diagnostic deliberately isolates the throat and preinstalled
# reaction hardware. A PASS would still require all other parts to be checked.
preinstalled={n:geometry[n] for n in ['Yaw_Reaction_Link','Yaw_Reaction_Clamp_Screw','Yaw_Reaction_Clamp_Nut','Yaw_Horn']}
throat=[];sections={}
for yaw in range(-60,61,10):
    yoke=geometry['Pitch_Yoke'].transform(np.asarray(rigidtr(yaw,0))[:3,:]);first=None;maximum=None
    for dz in np.arange(0,42.01,.5):
        placed=yoke.translate([0,0,float(dz)]);hh=hits(placed,preinstalled)
        if hh:
            row=dict(lift_mm=float(dz),hits=hh)
            if first is None:first=row
            if maximum is None or sum(x['overlap_mm3'] for x in hh)>sum(x['overlap_mm3'] for x in maximum['hits']):maximum=row
    throat.append(dict(yaw_deg=yaw,status='BLOCKED' if first else 'PASS',first_failure=first,maximum_overlap_sample=maximum,samples=85))
    print('REACTION_THROAT',yaw,throat[-1]['status'],first,flush=True)
    if yaw==0 and maximum:
        dz=maximum['lift_mm'];sections['throat']={n:m.transform([[0,1,0,0],[0,0,1,0],[1,0,0,0]]).slice(0.).to_polygons() for n,m in
            {'Pitch_Yoke':yoke.translate([0,0,dz]),'Yaw_Reaction_Link':geometry['Yaw_Reaction_Link']}.items()}
        sections['throat_lift_mm']=dz

extra={n:t['m'] for n,t in ctx.targets.items() if n.startswith(('Plug_','fixed_wire_'))}
origin=Vector((0,0,D['body_z']))
raised=Matrix.Translation((0,0,14))@Matrix.Translation(origin)@Matrix.Rotation(math.radians(15),4,'X')@Matrix.Translation(-origin)
stagefile=REST/'head_module_sequence_v2/review.json';stage=read(stagefile);inputs.append(stagefile)
for f,h in stage['sources'].items():assert sha(ROOT/f)==h,f
upper=set(stage['moving_upper_module'])
access=[]
for shell in ['closed','raised','absent']:
    fixed={n:m for n,m in geometry.items() if n not in absent};fixed.update(extra)
    # Mounted plugs follow their actual upper-body rear PCB. Wires retain
    # their existing candidate poses; no claim of flexible shell motion.
    following=upper|{'Plug_rear_J2','Plug_rear_J3'}
    if shell=='raised':
        for n in following:
            if n in fixed:fixed[n]=fixed[n].transform(np.asarray(raised)[:3,:])
    elif shell=='absent':
        for n in following:fixed.pop(n,None)
    driver=axial(1.25,100.,[0,60.3,142.5],[0,1,0])
    toolhits=hits(driver,fixed)
    rows=[]
    for name,direction,length in [('Yaw_Reaction_Retainer_Screw',1,25.),('Yaw_Reaction_Retainer_Nut',-1,15.)]:
        first=None;checked=0
        for travel in np.arange(0,length+.01,.25):
            h=hits(geometry[name].translate([0,float(travel)*direction,0]),fixed);checked+=1
            if h:first=dict(travel_mm=float(travel),hits=h);break
        rows.append(dict(part=name,status='BLOCKED' if first else 'PASS',first_failure=first,checked_samples=checked,planned_travel_mm=length))
    row=dict(shell=shell,status='BLOCKED' if toolhits or any(x['status']!='PASS' for x in rows) else 'PASS',driver_hits=toolhits,fastener_rows=rows)
    access.append(row);print('REACTION_ACCESS',shell,json.dumps(row),flush=True)
    if shell=='closed':
        show={n:geometry[n] for n in ['Yaw_Base','Body_Upper','Yaw_Reaction_Link','Pitch_Yoke']};show['driver']=driver
        sections['retainer']={n:m.transform([[0,1,0,0],[0,0,1,0],[1,0,0,0]]).slice(0.).to_polygons() for n,m in show.items()}

# Can the upper-body shell be raised after the inner head is seated? This is
# only its collision with the installed inner head, not the whole sequence.
shellrows=[]
for yaw in [-60,0,60]:
    tr=np.asarray(rigidtr(yaw,0))[:3,:]
    inner={n:m.transform(tr) for n,m in geometry.items() if groups[n] in ['yaw','pitch'] and n not in absent}
    first=None;count=0
    for u in np.linspace(0,1,61):
        pose=Matrix.Translation((0,0,14*u))@Matrix.Translation(origin)@Matrix.Rotation(math.radians(15*u),4,'X')@Matrix.Translation(-origin)
        h=hits(geometry['Body_Upper'].transform(np.asarray(pose)[:3,:]),inner);count+=1
        if h:first=dict(fraction=float(u),hits=h);break
    row=dict(yaw_deg=yaw,status='BLOCKED' if first else 'PASS',checked_samples=count,first_failure=first)
    shellrows.append(row);print('INNER_HEAD_SHELL_RAISE',json.dumps(row),flush=True)
ctx.assert_unchanged()
sectionfile=OUT/'sections.json';sectionfile.write_text(json.dumps(sections,default=lambda a:a.tolist())+'\n')
r=dict(status='PASS',scope='Diagnosis completed; individual assembly branches have their own status and may be blocked',
    sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},
    throat_rows=throat,retainer_access=access,shell_against_inner_head=shellrows,
    driver_envelope='Nominal straight diameter2.5 x100mm, +Y, no handle or torque qualification',
    sections_sha256=sha(sectionfile),section_plane='X=0; plotted coordinates Y,Z',actual_transmission_stack='BLOCKED',full_harness='BLOCKED',
    main_changed=False,approved=False,C6_main_applied=False,Yaw_Reaction_Link_present=True,
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('REACTION_LINK_ORDER_DONE',r['status'],r['elapsed_s'],flush=True)

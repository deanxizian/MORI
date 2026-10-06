"""Check access to the bridge and reaction link with candidate halves open.

The final transmission parts remain provisional. This is a tool/screw route
check, not certification of the reaction-link joint or full wired assembly.
"""
from pathlib import Path
import json,math,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes';OUT=BASE/'cam_restraints/body_front_rear_split'
sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import manifold
from interface_completion import axial
ctx=Context();started=time.time();source=OUT/'review.json';r=json.loads(source.read_text())
for f,h in {**r['sources'],**r['inputs']}.items():assert sha(ROOT/f)==h,f
inputs=[source,ROOT/'mechanical/scripts/interface_completion.py']
native={n:s.m for n,s in ctx.ss.items()};forms={}
for n,row in r['parts'].items():
    p=ROOT/row['file'];assert sha(p)==row['sha256'];inputs.append(p);a=np.load(p)
    forms[n]=manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles'].astype(np.uint64)))
fixed={n:m for n,m in native.items() if n not in set(r['omitted']+r['deferred_frame_screws']+['Body_Upper','Body_Lower'])}
fixed.update(forms)
fixed.update({n:t['m'] for n,t in ctx.targets.items() if n.startswith(('Plug_','fixed_wire_'))})
for label,sign in [('front',1),('rear',-1)]:
    for n in r['modules'][label]:
        if n in fixed:fixed[n]=fixed[n].translate([0,220*sign,0])
def collision(m,targets):
    bb=np.asarray(m.bounding_box());hits=[]
    for n,t in targets.items():
        tb=np.asarray(t.bounding_box())
        if np.any(bb[3:]<tb[:3]) or np.any(tb[3:]<bb[:3]):continue
        v=float((m^t).volume())
        if abs(v)>1e-5:hits.append(dict(target=n,overlap_mm3=v))
    return hits
def swept(m,direction):
    v=np.asarray(m.to_mesh64().vert_properties[:,:3])
    return manifold.Manifold.hull_points(np.r_[v,v+np.asarray(direction)*150].tolist())
rows=[]
for name,axis_index,sign,partner in [
 ('Yaw_Reaction_Retainer_Screw',1,1,'Yaw_Reaction_Retainer_Nut'),
 ('Yaw_Base_-1_Screw',0,-1,'Yaw_Base_-1_Nut'),
 ('Yaw_Base_1_Screw',0,1,'Yaw_Base_1_Nut')]:
    s=ctx.ss[name];axis=np.eye(3)[axis_index]*sign;center=(s.lo+s.hi)/2
    face=center.copy();face[axis_index]=s.hi[axis_index] if sign>0 else s.lo[axis_index]
    if axis_index==1:
        tools=[axial(1.25,100,face+axis*50,axis),axial(8,60,face+axis*130,axis)]
        desc='ASSUMED straight driver shaft diameter2.5 x100 and handle diameter16 x60; drive engagement unknown'
    else:
        # Previously received Wera 2 AF,100/5.5 tool dimensions; long leg along
        # bolt axis. Distal short-leg sphere encloses all handle roll angles.
        rad=1.18;elbow=face+axis*100
        tools=[axial(rad,100,face+axis*50,axis),manifold.Manifold.sphere(5.5+rad,48).translate(elbow.tolist())]
        desc='2 AF100/5.5 key; radius1.18 shaft and distal radius6.68 sphere enclose every roll angle; envelope, not exact vendor CAD'
    rr=np.linalg.norm(np.delete(s.v-center,axis_index,axis=1),axis=1)
    axial_position=s.v[:,axis_index]*sign
    shank_radius=1.0 if axis_index==1 else 1.5
    cut=float(axial_position[rr>shank_radius+.0001].min())
    head=manifold.Manifold.hull_points(s.v[axial_position>=cut-1e-7].tolist())
    shank=manifold.Manifold.hull_points(s.v[(axial_position<=cut+1e-7)&(rr<shank_radius+.0001)].tolist())
    missing=float((s.m-(head+shank)).volume());assert abs(missing)<1e-6
    for wheels in ['present','tyres_hubs_deferred']:
        absent={name}
        if wheels!='present':absent|={'Tire_L','Tire_R','Wheel_Hub_L','Wheel_Hub_R','Wheel_End_Washer_L','Wheel_End_Washer_R','Wheel_End_Screw_L','Wheel_End_Screw_R'}
        targets={n:m for n,m in fixed.items() if n not in absent}
        hits=[];threads=[]
        for i,m in enumerate(tools):hits += [dict(piece='tool_'+str(i),**h) for h in collision(swept(m,axis),targets)]
        for i,m in enumerate([head,shank]):
            hull=swept(m,axis)
            for h in collision(hull,targets):
                if h['target']==partner:
                    baseline=s.m^targets[partner];added=(hull^targets[partner])-baseline
                    if abs(added.volume())<1e-6:
                        threads.append(dict(**h,additional_overlap_mm3=float(added.volume()),status='NOT_TESTED',
                            meaning='Existing nominal threaded pair only; not physical thread qualification'))
                        continue
                hits.append(dict(piece='screw_'+str(i),**h))
        row=dict(screw=name,wheels=wheels,status='BLOCKED' if hits else 'PASS',tool=desc,hits=hits,
                 existing_thread_interfaces=threads,native_screw_material_not_enclosed_mm3=missing)
        rows.append(row);print('BODY_SPLIT_CORE_ACCESS',json.dumps(row),flush=True)
ctx.assert_unchanged()
out=dict(status='PASS' if all(x['status']=='PASS' for x in rows if x['wheels']=='tyres_hubs_deferred') else 'BLOCKED',
    scope='Continuous convex-piece axial tool and screw sweeps with front/rear modules displaced220mm; tyres/hubs may be deferred',
    sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},rows=rows,
    original_bridge_and_reaction_link_retained=True,all_head_solids_retained=True,
    source_reaction_nut_host_contact='Existing nominal reaction nut/bridge overlap and final SCS0009 interfaces remain unresolved; not passed by this access check',
    flexible_module_wires='NOT_TESTED',tightening_torque='NOT_TESTED',complete_assembly='BLOCKED',
    main_changed=False,approved=False,C6_main_applied=False,full_harness='BLOCKED',Yaw_Reaction_Link_present=True,
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'core_access.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('BODY_SPLIT_CORE_ACCESS_DONE',out['status'],out['elapsed_s'],flush=True)

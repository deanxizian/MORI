"""Two separate keeper operations: left at +60, right at -60 yaw.

Tool is withdrawn before changing yaw. Exact entry sweeps of convex tool
pieces and bounded angular sweeps are checked. Full flexible assembly and
the SCS0009 mating stack remain separate unresolved requirements.
"""
from pathlib import Path
import itertools,json,math,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes';REST=BASE/'cam_restraints';OUT=REST/'keeper_alternating_yaw'
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from common import manifold
from validate import rigidtr
from interface_completion import axial
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from upper_pack_geometry import refined
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text())
benchfile=REST/'bench_preassembly_v2/review.json';toolfile=REST/'keeper_after_head_long_leg/review.json'
curvefile=BASE/'cam_side_fans/c6_join/candidate_curves.npz';curves=np.load(curvefile)
inputs=[benchfile,toolfile,curvefile,HERE/'upper_pack_geometry.py',ROOT/'mechanical/scripts/validate.py',ROOT/'mechanical/scripts/interface_completion.py']
for r in [read(benchfile),read(toolfile)]:
    for f,h in {**r['sources'],**r['inputs']}.items():assert sha(ROOT/f)==h,f
absent=set(read(benchfile)['not_yet_installed'])
# These transmission parts were absent during detached cradle placement, but
# must be represented when handling an assembled inner head. Their geometry
# is still explicitly provisional pending the SCS0009 supplier drawings.
absent-= {'Pitch_Horn','Pitch_Lock_Screw','Pitch_Output','Pitch_Trunnion_L','Pitch_Trunnion_R'}
stored={}
for n,p in [('Yaw_Base',BASE/'c6_left_slot_entry/Yaw_Base_candidate.npz'),
            ('Pitch_Yoke',REST/'sliding_guide_v4/Pitch_Yoke_candidate.npz'),
            ('Pitch_Cradle',REST/'return_clamp_v3/Pitch_Cradle_candidate.npz'),
            ('connector_band',REST/'return_clamp_v3/band.npz'),('connector_head',REST/'return_clamp_v3/head.npz')]:
    inputs.append(p);a=np.load(p);stored[n]=manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles'].astype(np.uint64)))
wire_names=[*[f'CAM_{i}' for i in range(1,5)],'P_J9_1','P_J9_2','P_J9_3','P_J18_1','P_J18_2','SPK_reservation_3','SPK_reservation_6']
rad=2/math.sqrt(3)+.01;rows=[];saved={};zero_area_hull_faces=0
def key_parts(face,angle,extra=0.):
    a=np.array([0.,0,1.]);b=np.array([math.cos(math.radians(angle)),math.sin(math.radians(angle)),0.])
    p=face+a*(-.8+extra)
    return [axial(rad,100.,p+a*50,a),axial(rad,5.5,p+a*100+b*2.75,b),
            manifold.Manifold.sphere(rad*math.sqrt(3),24).translate((p+a*100).tolist())]
def verts(m):return np.asarray(m.to_mesh64().vert_properties[:,:3])
def check(m,fixed,wires,error=0.,gap=.3):
    global zero_area_hull_faces
    bb=np.asarray(m.bounding_box());hits=[];minimum=.301
    for n,t in fixed.items():
        tb=np.asarray(t.bounding_box())
        if np.any(bb[3:]+gap+error<tb[:3]) or np.any(tb[3:]+gap+error<bb[:3]):continue
        vol=float((m^t).volume());d=0. if abs(vol)>1e-6 else float(m.min_gap(t,gap+error+.001))
        minimum=min(minimum,d-error)
        if abs(vol)>1e-6 or d-error<gap:hits.append(dict(target=n,volume_mm3=vol,gap_lower_bound_mm=d-error))
    if wires:
        mesh=m.to_mesh64();v=np.asarray(mesh.vert_properties[:,:3]);f=np.asarray(mesh.tri_verts)
        face=v[f[:,0]];norm=np.cross(v[f[:,1]]-face,v[f[:,2]]-face)
        area=np.linalg.norm(norm,axis=1);valid=area>1e-12
        zero_area_hull_faces+=int((~valid).sum())
        # Manifold hull triangulation can include zero-area cap triangles.
        # They have no support plane; do not normalise them into NaNs.
        # The collision manifold itself is unchanged.
        f=f[valid];face=face[valid];norm=norm[valid]/area[valid,None]
        tree=BVHTree.FromPolygons(v,f.tolist(),all_triangles=True)
        assert np.max(v@norm.T-np.einsum('ij,ij->i',face,norm))<1e-5
        assert np.max(np.einsum('ij,ij->i',v.mean(0)-face,norm))<1e-5
        for n,w in wires.items():
            margin=w['radius']+gap+error+w['step']/2+.0004
            ids=np.flatnonzero(np.all(w['p']>=bb[:3]-margin,axis=1)&np.all(w['p']<=bb[3:]+margin,axis=1))
            for i in ids:
                p=w['p'][i];inside=np.all(np.einsum('ij,ij->i',p-face,norm)<=0)
                d=0. if inside else float(tree.find_nearest(Vector(p))[3])
                lower=d-w['radius']-error-w['step']/2-.0004
                if lower<gap:
                    hits.append(dict(target='Wire_'+n,point_mm=p.tolist(),gap_lower_bound_mm=lower,inside_hull=bool(inside)));break
    return dict(status='BLOCKED' if hits else 'PASS',native_gap_lower_bound_mm=minimum,hits=hits)
for stage in ['full_head','inner_head_before_optics']:
 for name,yaw in [('Yaw_Keeper_Screw_0',60),('Yaw_Keeper_Screw_1',-60)]:
    tr=np.asarray(rigidtr(yaw,0))[:3,:];s=ctx.ss[name]
    fixed={n:(t.m.transform(tr) if t.group in ['yaw','pitch'] else t.m) for n,t in ctx.ss.items()
           if n!=name and (stage=='full_head' or n not in absent)}
    for n,m in stored.items():fixed[n]=m.transform(tr) if n in ['Pitch_Yoke','Pitch_Cradle','connector_band','connector_head'] else m
    fixed.update({n:t['m'] for n,t in ctx.targets.items() if n.startswith(('Plug_','fixed_wire_'))})
    wires={}
    for n in wire_names:
        key=f'{n}_y{yaw}'+('_p0' if n.startswith('CAM_') else '')
        p=refined(curves[key],.02);wires[n]=dict(p=p,step=float(np.linalg.norm(np.diff(p,axis=0),axis=1).max()),
            radius=.3302 if n.startswith('CAM_') else .4445 if n.startswith('SPK') else .5842)
    face=np.array([(s.lo[0]+s.hi[0])/2,(s.lo[1]+s.hi[1])/2,s.hi[2]]);entry=[]
    # Start with the tool completely above the frame. Translation is exact
    # for each convex key piece; the engaged screw itself is omitted.
    for i,piece in enumerate(key_parts(face,0)):
        v=verts(piece);hull=manifold.Manifold.hull_points(np.vstack([v,v+[0,0,150.]]))
        entry.append(dict(piece=i,**check(hull,fixed,wires)))
    rotation=[]
    if all(r['status']=='PASS' for r in entry):
        # Shaft and elbow do not move around their own vertical axis.
        for angle in range(0,360,5):
            a=key_parts(face,angle)[1];b=key_parts(face,angle+5)[1]
            h=manifold.Manifold.hull_points(np.vstack([verts(a),verts(b)]))
            error=(5.5+rad)*(1-math.cos(math.radians(2.5)))+2e-5
            r=check(h,fixed,wires,error);rotation.append(dict(from_deg=angle,to_deg=angle+5,error_mm=error,**r))
            if r['status']!='PASS':break
    screw=[]
    if all(r['status']=='PASS' for r in entry) and rotation and all(r['status']=='PASS' for r in rotation):
        # Split actual screw at its documented head underside before sweeping;
        # never fill the cone from a wide cap to the narrow shank by one hull.
        # Derive the head/shank boundary from the saved float32 mesh, not
        # subtraction of nominal height: an epsilon of wide head inside the
        # shank clip makes its convex hull falsely expand the entire shaft.
        rv=np.linalg.norm(s.v[:,:2]-face[:2],axis=1)
        cut=float(s.v[rv>1.5,2].min())
        selections={'head':(s.v[:,2]>=cut-1e-7),
                    'shank':(s.v[:,2]<=cut+1e-7)&(rv<1.5)}
        pieces={label:manifold.Manifold.hull_points(s.v[mask]) for label,mask in selections.items()}
        envelope=pieces['head']+pieces['shank']
        missing=float((s.m-envelope).volume())
        assert abs(missing)<1e-5
        for label,m in pieces.items():
            v=verts(m);h=manifold.Manifold.hull_points(np.vstack([v,v+[0,0,8.]]))
            screw.append(dict(piece=label,mesh_head_bottom_z_mm=cut,native_material_not_enclosed_mm3=missing,
                              **check(h,fixed,wires,gap=0.)))
    status='PASS' if all(x['status']=='PASS' for x in entry+rotation+screw) and len(rotation)==72 and len(screw)==2 else 'BLOCKED'
    row=dict(stage=stage,screw=name,yaw_deg=yaw,head_top_mm=face.tolist(),status=status,tool_entry=entry,
             tool_rotation=rotation,screw_entry=screw,checked_wire_candidates=wire_names)
    rows.append(row);print('KEEPER_ALTERNATING_CASE',stage,name,status,[r for r in entry if r['status']!='PASS'],flush=True)
    if stage=='inner_head_before_optics':
        for i,m in enumerate(key_parts(face,0)):
            a=m.to_mesh64();saved[f'{name}_piece{i}_vertices']=a.vert_properties[:,:3];saved[f'{name}_piece{i}_triangles']=a.tri_verts
ctx.assert_unchanged();np.savez_compressed(OUT/'tools.npz',**saved)
usable=all(r['status']=='PASS' for r in rows if r['stage']=='inner_head_before_optics')
r=dict(status='PASS' if usable else 'BLOCKED',scope='Two sequential keeper-fastener access operations with tool entry, rotation and screw sweeps; provisional final wire poses only',
    sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},rows=rows,
    absent_in_inner_head_stage=sorted(absent),provisional_transmission_parts_retained=['Pitch_Horn','Pitch_Lock_Screw','Pitch_Output','Pitch_Trunnion_L','Pitch_Trunnion_R'],
    tool_use=read(toolfile)['tool_use'],tool=read(toolfile)['tool'],tool_entry_travel_mm=150,rotation_intervals_per_operation=72,
    sequence=['Bridge bolts fixed and upper body shell settled before the head subassembly.',
              'With optics and head shells absent, turn the unpowered inner head to +60deg, install left keeper screw, remove tool.',
              'Turn head to -60deg with tool removed, install right keeper screw, remove tool, return to zero.'],
    between_operation_wired_motion='NOT_TESTED',whole_head_lowering='NOT_TESTED',loose_lead_manipulation='NOT_TESTED',
    actual_transmission_stack='BLOCKED',actual_tool_engagement_torque='NOT_TESTED',full_harness='BLOCKED',
    main_changed=False,approved=False,C6_main_applied=False,Yaw_Reaction_Link_present=True,
    tool_geometry_sha256=sha(OUT/'tools.npz'),script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
r['zero_area_hull_faces_omitted_from_halfspace_only']=zero_area_hull_faces
(OUT/'review.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('KEEPER_ALTERNATING_DONE',r['status'],r['elapsed_s'],flush=True)

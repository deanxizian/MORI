"""Independent finite solid, service and retention checks for C5.

Includes full-current hardware, explicit29mate/14wire allocations. Assembly
checks are rigid/unwired and retain the existing incomplete horn interfaces.
"""
from pathlib import Path
import sys,json,math,time,itertools
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent/'outer_harness_M1_48'))
sys.path.insert(0,str(HERE))
from native_context import Context,np,manifold,sha
from validate import rigidtr
from build_candidate import cylinder,ring,box

def load(name):
    d=np.load(HERE/(name+'.npz'))
    return manifold.Manifold(manifold.Mesh64(d['vertices_mm'],d['triangles'].astype(np.uint64)))
def volume(a,b):
    aa=np.asarray(a.bounding_box());bb=np.asarray(b.bounding_box())
    if np.any(aa[:3]>=bb[3:]) or np.any(bb[:3]>=aa[3:]):return 0.
    v=float((a^b).volume());return v if v>.01 else 0.
def rotate(m,yaw,pitch=0):return m.transform(np.asarray(rigidtr(yaw,pitch))[:3,:])

ctx=Context();started=time.time();build=json.loads((HERE/'C5_build.json').read_text())
assert build['source_main_sha256']==ctx.source_hash
original={n:s.m for n,s in ctx.ss.items()}
extra={n:r['m'] for n,r in ctx.targets.items() if n not in original}
original.update(extra)
group={n:s.group if s.group in ['yaw','pitch'] else 'body' for n,s in ctx.ss.items()}
group.update({n:'body' for n in extra})
changes={r['name']:load('C5_'+r['name']) for r in build['parts']}
for r in build['parts']:assert r['mesh_sha256']==sha(HERE/('C5_'+r['name']+'.npz'))
geom=dict(original);geom.update(changes)
allowed={frozenset(('Yaw_Base',n)) for n in changes if 'Insert' in n}
checks=0;hits=[];inherited=[];seen=set()
def compare(a,b,yaw=0,pitch=0):
    global checks
    if a==b or frozenset((a,b)) in allowed:return
    kinds={group[a],group[b]}
    key=(tuple(sorted((a,b))),yaw if 'body' in kinds and len(kinds)>1 else 0,
        pitch if 'pitch' in kinds and len(kinds)>1 else 0)
    if key in seen:return
    seen.add(key);checks+=1
    def pose(m,n):return m if group[n]=='body' else rotate(m,yaw,pitch if group[n]=='pitch' else 0)
    v=volume(pose(geom[a],a),pose(geom[b],b))
    if v:
        old=volume(pose(original[a],a),pose(original[b],b))
        row=dict(a=a,b=b,yaw_deg=yaw,pitch_deg=pitch,candidate_overlap_mm3=v,native_overlap_mm3=old)
        (hits if v>old+.01 else inherited).append(row)

for yaw in range(-60,61,10):
    for pitch in range(-20,26,5):
        for a in changes:
            for b in geom:compare(a,b,yaw,pitch)
    print('C5_MOTION',yaw,'checks',checks,'new overlaps',len(hits),'seconds',round(time.time()-started,1),flush=True)

yoke=geom['Pitch_Yoke'];base=geom['Yaw_Base'];keeper=geom['Yaw_Anti_Lift_Keeper'];bearing=geom['Yaw_Bearing']
stops=[]
for sign in [-1,1]:
    hit=None
    for deg in np.arange(60,66.01,.25):
        v=volume(rotate(yoke,sign*float(deg)),base)
        if v:hit=dict(first_sampled_overlap_deg=sign*float(deg),overlap_mm3=v);break
    stops.append(dict(sign=sign,status='PASS' if hit and 64<=abs(hit['first_sampled_overlap_deg'])<=64.5 else 'BLOCKED',hit=hit))
capture=[]
for yaw in range(-60,61,10):
    for dz in [.39,.41,1.0]:
        v=volume(rotate(yoke,yaw).translate((0,0,dz)),keeper)
        capture.append(dict(yaw_deg=yaw,lift_mm=dz,overlap_mm3=v,
            status='PASS' if (v==0)==(dz==.39) else 'BLOCKED'))

bench=[];bench_checks=0
names={'Pitch_Yoke','Yaw_Servo','Pitch_Servo','Yaw_Output','Pitch_Output','Yaw_Reaction_Link','Yaw_Horn','Yaw_Lock_Screw'}
for dy in np.arange(0,60.01,.5):
    m=keeper.translate((0,float(dy),0))
    for n in names:
        bench_checks+=1;v=volume(m,geom[n])
        if v:bench.append(dict(y_mm=float(dy),other=n,overlap_mm3=v))
yawset={n for n,g in group.items() if g=='yaw'}|{'Yaw_Anti_Lift_Keeper','Yaw_Reaction_Link',
    'Yaw_Reaction_Clamp_Screw','Yaw_Reaction_Clamp_Nut','Yaw_Horn','Yaw_Output','Yaw_Lock_Screw'}
fasteners={n for n in changes if 'Keeper_' in n}
fixture=set(geom)-yawset-{n for n,g in group.items() if g=='pitch'}-fasteners-{'Yaw_Reaction_Retainer_Screw','Yaw_Reaction_Retainer_Nut'}
paths=[];path_checks=0
for dz in np.arange(0,90.01,.5):
    for n in ['Pitch_Yoke','Yaw_Anti_Lift_Keeper']:
        m=geom[n].translate((0,0,float(dz)))
        for other in fixture:
            path_checks+=1;v=volume(m,geom[other])
            if v:paths.append(dict(z_mm=float(dz),moving=n,fixed=other,overlap_mm3=v))

bearing_paths=[]
for dz in np.arange(0,45.01,.25):
    v=volume(bearing.translate((0,0,float(dz))),base)
    if v:bearing_paths.append(dict(z_mm=float(dz),overlap_mm3=v))
# Explicitly demonstrate why the first complete-print proposal was rejected.
c1bearing=load('C1_Yaw_Bearing');c1base=load('C1_Yaw_Base')
c1path=[]
for dz in [.25,.5,.75,1.,2.]:
    v=volume(c1bearing.translate((0,0,dz)),c1base)
    if v:c1path.append(dict(lift_mm=dz,overlap_mm3=v))
print('C5_PATHS','bench',len(bench),'pair',len(paths),'bearing',len(bearing_paths),flush=True)

# Pure axial primitive does not run the historical construction phases.
from interface_completion import axial
tool=[];screw_paths=[];tool_checks=0
tool_fixture={n:m for n,m in geom.items() if group[n]!='pitch'}
for i,x in enumerate([-26,26]):
    name=f'Yaw_Keeper_Screw_{i}'
    tf={n:(rotate(m,60) if group[n]=='yaw' else m) for n,m in tool_fixture.items() if n!=name}
    p=np.array([x,0.,163.55]);axis=np.array([0.,0.,1.])
    shapes=[axial(1.16,70,p+axis*35.04,axis)]
    for deg in range(0,360,5):
        a=math.radians(deg);b=np.array([math.cos(a),math.sin(a),0.])
        shapes.append(axial(1.16,20,p+axis*(70-1.16)+b*10,b))
    for i,m in enumerate(shapes):
        for other,t in tf.items():
            tool_checks+=1;v=volume(m,t)
            if v:tool.append(dict(screw=name,piece=i,other=other,overlap_mm3=v))
    for dz in np.arange(0,35.01,.5):
        m=geom[name].translate((0,0,float(dz)))
        for other,t in tf.items():
            v=volume(m,t)
            if v:screw_paths.append(dict(screw=name,z_mm=float(dz),other=other,overlap_mm3=v))

support=[]
for i,x in enumerate([-26,26]):
    # Probe full nominal material ring around each blind insert pilot.
    probe=(cylinder(3.225,155.4,159.39,x)-cylinder(2.025,155.39,159.4,x))
    lost=float((probe-base).volume())
    support.append(dict(insert=i,trial_pilot_radius_mm=2.025,probe_radial_wall_mm=1.2,
        probe_z_mm=[155.4,159.39],missing_material_mm3=lost,status='PASS' if lost<.01 else 'BLOCKED'))
base_build=build['status']=='PASS'
ok=base_build and not any([hits,bench,paths,bearing_paths,tool,screw_paths]) and all(r['status']=='PASS' for r in capture+stops+support)
ctx.assert_unchanged()
out=dict(status='PASS' if ok else 'BLOCKED',scope='Finite geometry and rigid/unwired local service; no complete harness or physical qualification',
    source_main_sha256=ctx.source_hash,build_sha256=sha(HERE/'C5_build.json'),script_sha256=sha(__file__),
    candidate_build=build['status'],native_parts=209,mates=29,static_candidate_wires=14,head_poses=130,
    distinct_pair_pose_checks=checks,new_overlaps=hits,inherited_overlaps=inherited,
    intentional_interference_exceptions=['Yaw_Base with two nominal heat-set inserts; pilot material checked separately'],
    stop_contacts=stops,axial_capture=capture,keeper_bench_side=dict(samples=121,checks=bench_checks,hits=bench),
    paired_vertical_insertion=dict(samples=181,checks=path_checks,hits=paths),
    bearing_insertion=dict(samples=181,hits=bearing_paths),first_C1_bearing_path=dict(status='BLOCKED' if c1path else 'NOT_TESTED',hits=c1path),
    tool_access=dict(checks=tool_checks,hits=tool),screw_insertion_hits=screw_paths,insert_support=support,
    local_journal_nominal_wall_mm=2.35,all_printed_wall_thickness='NOT_TESTED',
    full_endpoint_routes='NOT_TESTED',wire_selection='BLOCKED',wired_assembly='NOT_TESTED',
    reaction_clamp_initial_assembly='BLOCKED',strength='NOT_TESTED',manufacturing_release=False,main_applied=False,
    limits=['130finiteposes and finite service samples do not prove continuous collision-free movement.',
        'Keeper installed on detached yaw assembly; pitch head absent; released reaction link travels with it.',
        'Bench/install/tool checks exclude new flexible wires and do not close complete head assembly.',
        'Bearing boundary cylinder omits real race/shield/chamfer detail. Fits, shoulders andPA12 process remain trial.',
        'Seven1.4224mm conductors are space samples, not selected or qualifiedSH/GH wires.'],elapsed_s=time.time()-started)
(HERE/'C5_verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('C5_VERIFY_DONE',out['status'],'new',len(hits),'inherited',len(inherited),'tool',len(tool),'screw',len(screw_paths),'seconds',out['elapsed_s'],flush=True)

"""Build a separate 6806 interface candidate from the immutable M1.48 solids.

No original scene object/config/hardware file is changed. Capacity constraints
are replaced here by complete three-print candidate solids. Every dimension
below is a trial design, not an approved supplier fit or load qualification.
"""
from pathlib import Path
import sys, json, math, time
HERE=Path(__file__).resolve().parent; PROJECT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent/'outer_harness_M1_48'))
sys.path.insert(0,str(HERE))
from native_context import Context,np,manifold,sha
from validate import rigidtr
from tapered_family import radial

def cylinder(r,a,b,x=0,y=0):
    return manifold.Manifold.cylinder(b-a,r,r,256).translate((x,y,a))
def ring(ro,ri,a,b):
    return cylinder(ro,a,b)-cylinder(ri,a-.01,b+.01)
def box(a,b):
    return manifold.Manifold.cube(tuple(np.asarray(b)-a)).translate(a)
def sector(ri,ro,a0,a1,z0,z1):
    angles=np.radians(np.linspace(a0,a1,math.ceil((a1-a0)/.5)+1))
    polygon=[(ro*math.cos(a),ro*math.sin(a)) for a in angles]
    polygon +=[(ri*math.cos(a),ri*math.sin(a)) for a in reversed(angles)]
    return manifold.CrossSection([polygon]).extrude(z1-z0).translate((0,0,z0))
def save(name,m):
    m=m.simplify(.0001); d=m.to_mesh64()
    np.savez_compressed(HERE/(name+'.npz'),vertices_mm=np.asarray(d.vert_properties[:,:3]),triangles=np.asarray(d.tri_verts))
    return m
def profile_bore():
    zs=np.r_[148.8,np.arange(173,195.01,.5),195.1]
    r=radial(zs,10.6,15.2,173.,30.)[0]
    # Radial padding also accounts for the sloped bore surface normal.
    r=np.maximum(12.6,r+1.20)
    pieces=[manifold.Manifold.cylinder(float(b-a),float(ra),float(rb),256).translate((0,0,float(a)))
        for a,b,ra,rb in zip(zs,zs[1:],r,r[1:])]
    return manifold.Manifold.batch_boolean(pieces,manifold.OpType.Add),list(zip(zs.tolist(),r.tolist()))

def build(ctx,pack,data):
    # Keep the existing socket, bridge legs and complete upper servo seats.
    # The larger bearing has documented boundaries only; no old hardware scale.
    # Preserve overlap with the existing outer shadow rim (R32.7 join).
    base=ctx.ss['Yaw_Base'].m-cylinder(32.6,147.01,166.)
    base+=ring(27,20,146.9,149.)+ring(27,21.05,149.,156.3)
    base+=ring(32.7,21.05,151.5,156.3)+ring(32.7,20.3,156.3,161.6)
    base+=ring(32.7,30.3,161.5,165.8)
    base+=(box((-4,-27,145.5),(4,27,148.5))-cylinder(8.8,145.4,148.6))
    base+=ctx.ss['Yaw_Base'].m^box((-4,-36,137.),(4,36,148.5))
    # Two broad windows instead of a bundle of scalloped wire-shaped cuts.
    windows=[]
    for indices in [[0,1,2,7],[3,4,5,6,8,9,10]]:
        angles=[]
        ref=pack['selected'][indices[0]]['angle_deg']
        for i in indices:
            for yaw in range(-60,61,10):
                p=data[f'wire{i}_y{yaw}'];p=p[(p[:,2]>=136.9)&(p[:,2]<=149.1)]
                a=np.degrees(np.arctan2(p[:,1],p[:,0]));a=ref+(a-ref+180)%360-180
                pad=math.degrees(math.asin((pack['selected'][i]['OD_mm']/2+.37)/10.6))
                angles.extend([float(a.min()-pad),float(a.max()+pad)])
        a0=math.floor(min(angles)*2)/2;a1=math.ceil(max(angles)*2)/2
        window=sector(9.55,11.7,a0,a1,136.9,149.1)-box((-4,-40,136.8),(4,40,149.2))
        base-=window
        windows.append(dict(indices=indices,angles_deg=[a0,a1],radii_mm=[9.55,11.7],z_mm=[136.9,149.1]))
    fixed=[]
    for a0,a1 in [(-96,-76),(76,96)]:
        # Root clears the larger bearing shield by0.5mm and joins the housing.
        root=sector(16.5,22,a0,a1,156.5,158.5)
        stop=sector(18.1,19.95,a0,a1,158.3,161.2)
        fixed.append(root+stop);base+=root+stop
    keeper=ring(30,15.25,161.6,165.6)-box((-15.25,-40,161.5),(15.25,0,165.7))
    hardware={}
    for i,x in enumerate([-26,26]):
        keeper-=cylinder(1.7,161.5,165.7,x)
        keeper-=cylinder(3.,163.9,165.7,x)
        base-=cylinder(2.025,155.6,161.7,x)
        for typ in ['Screw','Insert']:
            name=f'Yaw_Keeper_{typ}_{i}'
            hardware[name]=ctx.ss[name].m.translate((0,0,2.))
    yoke=ctx.ss['Pitch_Yoke'].m-cylinder(22,148.8,173.55)
    yoke+=ring(14.95,12.6,149.4,156.)
    yoke+=(manifold.Manifold.cylinder(.4,14.7,14.95,256).translate((0,0,149.))-cylinder(12.6,148.9,149.5))
    yoke+=ring(16.,12.6,156.,156.85)+ring(14.8,12.6,156.5,173.6)
    collar=ring(17.5,12.6,158.8,161.2)
    key=sector(17.1,19.85,-12,12,158.8,161.2)
    yoke+=collar+key
    bore,bore_profile=profile_bore();yoke-=bore
    candidates=dict(Yaw_Base=base,Pitch_Yoke=yoke,Yaw_Anti_Lift_Keeper=keeper,
        Yaw_Bearing=ring(21.,15.,149.,156.),**hardware)
    features=dict(collar=collar,key=key,fixed_negative=fixed[0],fixed_positive=fixed[1])
    params=dict(bearing='NSK6806ZZ boundary reference',bearing_d_D_B_mm=[30,42,7],
        bearing_z_mm=[149,156],journal_outer_r_mm=14.95,journal_inner_r_mm=12.6,
        shaft_shoulder_outer_r_mm=16,housing_bore_r_mm=21.05,housing_shoulder_r_mm=20,
        keeper_z_mm=[161.6,165.6],keeper_inner_outer_r_mm=[15.25,30],keeper_hardware_shift_z_mm=2,
        fixed_stop_z_mm=[158.3,161.2],fixed_root_z_mm=[156.5,158.5],
        fixed_root_inner_outer_r_mm=[16.5,22],moving_collar_key_z_mm=[158.8,161.2],
        capture_radial_overlap_mm=2.25,capture_axial_gap_mm=.4,windows=windows,bore_profile=bore_profile,
        socket_support_webs=dict(width_mm=8,z_mm=[145.5,148.5],inner_outer_r_mm=[8.8,27]))
    return candidates,features,params

if __name__=='__main__':
    started=time.time();ctx=Context();pack=json.loads((HERE/'packing.json').read_text())
    assert pack['status']=='PASS' and pack['source_main_sha256']==ctx.source_hash
    assert sha(HERE/'packed_curves.npz')==pack['output_curves_sha256']
    data=np.load(HERE/'packed_curves.npz')
    candidates,features,params=build(ctx,pack,data)
    rows=[]
    for name,m in candidates.items():
        m=save('C1_'+name,m);candidates[name]=m
        components=[float(c.volume()) for c in m.decompose()]
        row=dict(name=name,kernel=str(m.status()),components_mm3=components,
            added_mm3=float((m-ctx.ss[name].m).volume()),removed_mm3=float((ctx.ss[name].m-m).volume()),
            bounds_mm=list(m.bounding_box()),mesh_sha256=sha(HERE/('C1_'+name+'.npz')))
        row['connected']='PASS' if len(components)==1 else 'BLOCKED'
        rows.append(row);print('C1_PART',row,flush=True)
    for name,m in features.items():save('C1_feature_'+name,m)
    original_targets=ctx.targets
    groupmap={n:s.group if s.group in ['yaw','pitch'] else 'body' for n,s in ctx.ss.items()}
    candidate_targets={n:ctx.target(m) for n,m in candidates.items()}
    all_targets=dict(original_targets);all_targets.update(candidate_targets)
    targets={g:{n:t for n,t in all_targets.items() if groupmap.get(n,'body')==g} for g in ['body','yaw','pitch']}
    wire_hits=[];checks=0
    for i,slot in enumerate(pack['selected']):
        for yaw in range(-60,61,10):
            p=data[f'wire{i}_y{yaw}']
            for group,objects in targets.items():
                ctx.targets=objects
                for pitch in (range(-20,26,5) if group=='pitch' else [0]):
                    tr=np.linalg.inv(np.asarray(rigidtr(yaw,pitch if group=='pitch' else 0)))
                    q=p if group=='body' else p@tr[:3,:3].T+tr[:3,3]
                    checks+=1;hit=ctx.clear(q,chord_error=pack['family']['chord_error_mm'],radius=slot['OD_mm']/2)
                    if hit:wire_hits.append(dict(wire=i,yaw_deg=yaw,pitch_deg=pitch,group=group,**hit))
        print('C1_WIRE',i,'failures',len(wire_hits),'seconds',round(time.time()-started,1),flush=True)
    ctx.targets=original_targets
    protected=dict(socket=ctx.ss['Yaw_Base'].m^cylinder(9.5,137.,147.01),
        webs=ctx.ss['Yaw_Base'].m^box((-4,-36,137.),(4,36,148.5)),
        upper_seats=ctx.ss['Pitch_Yoke'].m-cylinder(22,148.8,195.1))
    protection={n:float((m-candidates['Pitch_Yoke' if n=='upper_seats' else 'Yaw_Base']).volume()) for n,m in protected.items()}
    sections={}
    layers={**{n+'_native':ctx.ss[n].m for n in ['Yaw_Base','Pitch_Yoke','Yaw_Anti_Lift_Keeper','Yaw_Bearing']},**candidates,
        'Yaw_Reaction_Link':ctx.ss['Yaw_Reaction_Link'].m}
    for z in [140.,145.5,146.,147.,149.5,152.5,157.,159.5,163.,166.,173.7,180.,185.,190.,194.]:
        sections['Z'+str(z)]={n:[p.tolist() for p in m.slice(z).to_polygons()] for n,m in layers.items()}
    for deg in [0,45,90,135]:
        a=math.radians(deg);tr=np.array([[math.cos(a),math.sin(a),0,0],[0,0,1,0],[-math.sin(a),math.cos(a),0,0]])
        sections['radial'+str(deg)]={n:[p.tolist() for p in m.transform(tr).slice(0).to_polygons()] for n,m in layers.items()}
    (HERE/'C1_sections.json').write_text(json.dumps(sections)+'\n')
    ctx.assert_unchanged()
    out=dict(status='PASS' if not wire_hits and all(r['connected']=='PASS' for r in rows) and max(protection.values())<1e-5 else 'BLOCKED',
        scope='Complete candidate print construction, protected support and local11wire clearance only',
        source_main_sha256=ctx.source_hash,sources=ctx.sources,parameters=params,parts=rows,
        packing_sha256=sha(HERE/'packing.json'),script_sha256=sha(__file__),
        wire_checks=checks,wire_hits=wire_hits,protected_material_removed_mm3=protection,
        sections_sha256=sha(HERE/'C1_sections.json'),main_applied=False,whole_harness='BLOCKED',
        full_part_motion='NOT_TESTED',assembly='NOT_TESTED',strength='NOT_TESTED',manufacturing_release=False,
        elapsed_s=time.time()-started)
    (HERE/'C1_build.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print('C1_DONE',out['status'],'wire hits',len(wire_hits),'protected',protection,'seconds',out['elapsed_s'],flush=True)

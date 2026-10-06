"""Independent integral support for the four-wire yaw-side pitch-loop anchor.

The first screen covers source solids and saved nominal wires only. A cable
tie, assembly path and strength require separate checks before adoption.
"""
from pathlib import Path
SUPPORT_SCRIPT=Path(__file__).resolve();SUPPORT_ROOT=SUPPORT_SCRIPT.parent
SUPPORT_HELPER=SUPPORT_ROOT/'plan_cam_yaw_fan_v4.py';__file__=str(SUPPORT_HELPER)
exec(compile(SUPPORT_HELPER.read_text().split('\nrng=np.random.default_rng',1)[0],str(SUPPORT_HELPER),'exec'),globals())
__file__=str(SUPPORT_SCRIPT)
OUT=SUPPORT_ROOT/'cam_anchors';OUT.mkdir(exist_ok=True)

def box(lo,hi):
    return manifold.Manifold.cube((np.asarray(hi)-lo).tolist()).translate(list(lo))
def cache(path,solid):
    mesh=solid.to_mesh64();np.savez_compressed(path,vertices_mm=np.array(mesh.vert_properties[:,:3]),triangles=np.array(mesh.tri_verts))
def overlap_boxes(a,b,pad=0.):
    a=np.asarray(a.bounding_box());b=np.asarray(b.bounding_box())
    return not (np.any(a[:3]>b[3:]+pad) or np.any(b[:3]>a[3:]+pad))
def source_fit(addition):
    minimum=math.inf;checked=0
    for name,group,m,lo,hi,tree in ob:
        if name=='Pitch_Yoke':continue # the explicitly joined host
        angles=range(-20,26,5) if group=='pitch' else (range(-60,61,10) if group=='body' else [0])
        for angle in angles:
            moving=m if group=='yaw' else m.transform(np.asarray(rigidtr(-angle if group=='body' else 0,angle if group=='pitch' else 0))[:3,:4])
            checked+=1
            if not overlap_boxes(addition,moving,.6):continue
            volume=max(0.,float((addition^moving).volume()))
            if volume>1e-6:return {'status':'BLOCKED','object':name,'angle_deg':angle,'group':group,'intersection_mm3':volume}
            gap=float(addition.min_gap(moving,.6));minimum=min(minimum,gap)
            if gap<.3-1e-5:return {'status':'BLOCKED','object':name,'angle_deg':angle,'group':group,'gap_mm':gap}
    return {'status':'PASS','minimum_gap_below_0_6mm':minimum if minimum<math.inf else None,'relative_checks':checked}

def wire_fit(addition):
    mesh=addition.to_mesh64();tree=BVHTree.FromPolygons(mesh.vert_properties[:,:3],mesh.tri_verts.tolist(),all_triangles=True)
    bb=np.asarray(addition.bounding_box());rows=[]
    # The four wires deliberately enter the grooved bed; their local straight
    # sweeps require no solid overlap, rather than a non-contact .3 mm air gap.
    # Use a circumscribed mesh radius so its polygon encloses the true tube.
    for slot,x in enumerate(xx):
        tube=manifold.Manifold.cylinder(4.4,(OD/2+.001)/math.cos(math.pi/64),circular_segments=64).translate([float(x),-1.5,229.9])
        volume=max(0.,float((tube^addition).volume()))
        if volume>1e-7:return {'status':'BLOCKED','type':'grip_straight_overlap','slot':slot,'volume_mm3':volume}
    routes=[]
    for (slot,pitch),(samples,error) in loop_samples.items():routes.append((f'loop_{slot}_{pitch}',samples[0],error))
    fan=SUPPORT_ROOT/'cam_fan_in/four_bend_transition'
    fc=np.load(fan/'curves.npz');fm=json.loads((fan/'pool.json').read_text())
    for pin in range(1,5):routes.append((f'fan_{pin}',fc[f'pin{pin}_candidate0'],fm['rows'][pin-1]['candidates'][0]['curve_error_bound_mm']))
    for name,p,error in routes:
        ds=np.linalg.norm(np.diff(p,axis=0),axis=1)
        allowance=OD/2+.3+np.maximum(np.r_[ds[0],ds],np.r_[ds,ds[-1]])/2+error+1e-4
        grip=(p[:,2]>=229.9)&(p[:,2]<=234.3)&(np.abs(p[:,1]+1.5)<1e-5)&(np.min(np.abs(p[:,0,None]-xx[None,:]),axis=1)<1e-5)
        ids=np.flatnonzero(np.all(p>=bb[:3]-allowance[:,None],axis=1)&np.all(p<=bb[3:]+allowance[:,None],axis=1)&~grip)
        for i in ids:
            distance=float(tree.find_nearest(Vector(p[i]))[3])
            if distance<allowance[i]:return {'status':'BLOCKED','type':'wire_gap','route':name,'point_mm':p[i].tolist(),'distance_mm':distance,'required_mm':float(allowance[i])}
        starts=ids[np.r_[True,np.diff(ids)>1]] if len(ids) else []
        for i in starts:
            tiny=manifold.Manifold.sphere(.01,16).translate(p[i].tolist())
            if (tiny^addition).volume()>tiny.volume()/2:return {'status':'BLOCKED','type':'inside','route':name}
        rows.append(name)
    return {'status':'PASS','routes_checked':len(rows),'grip_sweeps_checked':4,
            'grip_zone_mm':[[float(xx.min()),-1.5,229.9],[float(xx.max()),-1.5,234.3]],
            'physical_grip_and_pullout':'NOT_TESTED'}

host=ss['Pitch_Yoke'].m
bed=box([float(xx.min()-1.2),-4.5,230.4],[float(xx.max()+1.2),-1.75,233.8])
grooves=manifold.Manifold.batch_boolean([manifold.Manifold.cylinder(6.,.35,circular_segments=64).translate([float(x),-1.5,230.]) for x in xx],manifold.OpType.Add)
bed=bed-grooves
trials=[];accepted=[];started=time.time()
for ymin,zmin,height in itertools.product([-5.5,-7.], [233.,233.4,233.8], [1.8,2.]):
    beam=box([-31.5,ymin,zmin],[float(xx.max()+1.2),-2.5,zmin+height])
    addition=beam+bed
    root=float((addition^host).volume());combined=host+addition
    components=len([s for s in combined.decompose() if abs(s.volume())>1e-7])
    row={'parameters':{'beam_y_min_mm':ymin,'beam_z_min_mm':zmin,'beam_height_mm':height},'root_overlap_mm3':root,'components':components}
    if root<1e-5 or components!=1:row.update(status='BLOCKED',reason='not_connected')
    else:
        row['source']=source_fit(addition)
        row['wires']=wire_fit(addition) if row['source']['status']=='PASS' else {'status':'NOT_TESTED'}
        row['status']='PASS' if row['source']['status']==row['wires']['status']=='PASS' else 'BLOCKED'
    trials.append(row);print('ANCHOR_SUPPORT',row,flush=True)
    if row['status']=='PASS':
        i=len(accepted);cache(OUT/f'addition_{i}.npz',addition);cache(OUT/f'Pitch_Yoke_{i}.npz',combined)
        accepted.append({'index':i,**row,'addition_mm3':float((combined-host).volume()),
                         'addition_sha256':sha(OUT/f'addition_{i}.npz'),'host_union_sha256':sha(OUT/f'Pitch_Yoke_{i}.npz')})
result={'status':'PASS' if accepted else 'BLOCKED','scope':'Unapproved integral support only; cable tie, assembly and strength pending',
    'source_main_sha256':source_hash,'source_script_sha256':sha(SUPPORT_SCRIPT),'source_helper_sha256':sha(SUPPORT_HELPER),
    'source_J3M_yoke_sha256':sha(SUPPORT_ROOT/'assembly_feed_v3/open_mouth/cleaned/Pitch_Yoke.npz'),
    'source_connected_route_sha256':sha(SUPPORT_ROOT/'cam_fan_in/four_bend_transition/packing.json'),
    'trials':trials,'accepted':accepted,'wire_OD_mm':OD,'groove_radius_trial_mm':.35,'groove_depth_mm':.10,
    'added_print_parts':0,'changed_prints':['Pitch_Yoke'],'cable_tie':'NOT_TESTED','full_installation':'NOT_TESTED',
    'strength':'NOT_TESTED','physical_wire_shape':'NOT_TESTED','whole_harness':'BLOCKED','main_applied':False,
    'manufacturing_release':False,'elapsed_s':time.time()-started}
(OUT/'support_screen.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('ANCHOR_SUPPORT_DONE',result['status'],len(accepted),flush=True)

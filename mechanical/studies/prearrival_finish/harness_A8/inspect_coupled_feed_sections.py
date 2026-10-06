"""Actual section polygons and finite radial bearing-journal wall samples."""
from pathlib import Path
SECTION_SCRIPT=Path(__file__).resolve();SECTION_DIR=SECTION_SCRIPT.parent
SECTION_HELPER=SECTION_DIR/'plan_h06_documented_mates.py';__file__=str(SECTION_HELPER)
exec(compile(SECTION_HELPER.read_text().split('\nports=json.loads',1)[0],str(SECTION_HELPER),'exec'),globals())
__file__=str(SECTION_SCRIPT);OUT=SECTION_DIR/'assembly_feed_v3'
source_solids={n:s.m for n,s in ss.items()};layers={}
for name in ['Yaw_Base','Pitch_Yoke']:
    for suffix,path in [('J3',OUT/'cleaned'/f'{name}.npz'),
                        ('J2',SECTION_DIR/'terminal_threading/cleaned'/f'{name}.npz'),
                        ('main',SECTION_DIR/'joined_entry_candidate'/f'{name}_baseline.npz')]:
        raw=np.load(path);m=manifold.Manifold(manifold.Mesh64(vert_properties=raw['vertices_mm'],tri_verts=raw['triangles'].astype(np.uint64)))
        layers[name+'_'+suffix]=m
    layers[name+'_newly_removed']=layers[name+'_J2']-layers[name+'_J3']
    layers[name+'_restored']=layers[name+'_J3']-layers[name+'_J2']
for name in ['Yaw_Reaction_Link','Yaw_Bearing','Yaw_Anti_Lift_Keeper','Yaw_Servo','Pitch_Servo']:
    layers[name]=source_solids[name]
sections={}
for angle in [0,45,90,135]:
    a=math.radians(angle);tr=np.array([[0,0,1,0],[math.cos(a),math.sin(a),0,0],[-math.sin(a),math.cos(a),0,0]])
    sections[str(angle)]={name:[np.array(p)[:,[1,0]].tolist() for p in m.transform(tr).slice(0).to_polygons()] for name,m in layers.items()}
(OUT/'sections.json').write_text(json.dumps(sections,ensure_ascii=False,indent=2)+'\n')

def ray_material_intervals(polygons,angle):
    e=np.array([math.cos(angle),math.sin(angle)]);cross=lambda a,b:a[...,0]*b[...,1]-a[...,1]*b[...,0]
    values=[]
    for poly in polygons:
        a=np.array(poly);v=np.roll(a,-1,axis=0)-a;den=cross(e,v);valid=np.abs(den)>1e-12
        u=np.zeros(len(a));r=np.zeros(len(a));u[valid]=cross(a[valid],e)/den[valid];r[valid]=cross(a[valid],v[valid])/den[valid]
        values.extend(r[valid&(u>=-1e-9)&(u<1-1e-9)&(r>0)].tolist())
    # A ray starts in the empty centre; oriented manifold sections alternate
    # entry and exit. At exact tangent vertices skip the angle in this sample.
    values=sorted(set(round(x,9) for x in values))
    if len(values)%2:return None
    return [(a,b) for a,b in zip(values[::2],values[1::2])]

bearing=ss['Yaw_Bearing'];journal_r=P['head_axial_retention']['bearing']['trial_journal_d_mm']/2
zs=np.linspace(float(bearing.lo[2]+.25),float(bearing.hi[2]-.25),17)
walls={};xysections={}
def section_properties(polygons):
    area=ixx=iyy=ixy=0.
    for p in polygons:
        q=np.roll(p,-1,axis=0);cross=p[:,0]*q[:,1]-q[:,0]*p[:,1]
        area+=float(np.sum(cross)/2)
        ixx+=float(np.sum((p[:,1]**2+p[:,1]*q[:,1]+q[:,1]**2)*cross)/12)
        iyy+=float(np.sum((p[:,0]**2+p[:,0]*q[:,0]+q[:,0]**2)*cross)/12)
        ixy+=float(np.sum((2*p[:,0]*p[:,1]+p[:,0]*q[:,1]+q[:,0]*p[:,1]+2*q[:,0]*q[:,1])*cross)/24)
    if area<0:area,ixx,iyy,ixy=-area,-ixx,-iyy,-ixy
    return {'area_mm2':area,'Ixx_about_axis_mm4':ixx,'Iyy_about_axis_mm4':iyy,'Ixy_about_axis_mm4':ixy}
enclosing=axial(journal_r,20.,[0,0,float((bearing.lo[2]+bearing.hi[2])/2)],[0,0,1],segments=512)
for suffix in ['main','J2','J3']:
    # Restrict material to the nominal journal cylinder. At the top collar the
    # real outer radius is larger; this measures only load-path material inside
    # the cylinder, without treating the wider collar as missing journal wall.
    m=layers['Pitch_Yoke_'+suffix]^enclosing;rows=[];missing=[];properties=[];excluded=[]
    for iz,z in enumerate(zs):
        polygons=[np.array(p) for p in m.slice(float(z)).to_polygons()]
        properties.append({'z_mm':float(z),**section_properties(polygons)})
        if iz==len(zs)//2:xysections[suffix]=[p.tolist() for p in polygons]
        for degrees in np.arange(.125,360,.5):
            intervals=ray_material_intervals(polygons,math.radians(float(degrees)))
            if intervals is None:missing.append({'z_mm':float(z),'angle_deg':float(degrees),'reason':'tangent_ray'});continue
            bands=[(a,b) for a,b in intervals if abs(b-journal_r)<.02]
            if len(bands)!=1:
                if iz==0 and len(intervals)==1 and 0<journal_r-intervals[0][1]<.15:
                    excluded.append({'z_mm':float(z),'angle_deg':float(degrees),'status':'NOT_APPLICABLE',
                        'reason':'Existing lower entry chamfer is outside the constant-diameter cylindrical-land wall metric',
                        'intervals':intervals})
                else:missing.append({'z_mm':float(z),'angle_deg':float(degrees),'reason':'no_single_journal_band','intervals':intervals})
                continue
            a,b=bands[0];rows.append({'z_mm':float(z),'angle_deg':float(degrees),'inner_r_mm':a,'outer_r_mm':b,'thickness_mm':b-a})
    assert not missing,(suffix,missing[:3])
    assert len(excluded)==720,(suffix,len(excluded))
    walls[suffix]={'rays_sampled':len(zs)*720,'valid_rays':len(rows),'missing':missing,
        'excluded_entry_chamfer_rays':excluded,
        'minimum':min(rows,key=lambda x:x['thickness_mm']) if rows else None,
        'maximum_sampled':max(r['thickness_mm'] for r in rows) if rows else None,
        'section_properties_within_nominal_journal_cylinder':properties}
critical=['Yaw_Bearing','Yaw_Anti_Lift_Keeper','Yaw_Reaction_Retainer_Screw','Yaw_Reaction_Retainer_Nut','Yaw_Keeper_Insert_0','Yaw_Keeper_Insert_1']
interfaces=[]
for name in ['Yaw_Base','Pitch_Yoke']:
    removed=layers[name+'_main']-layers[name+'_J3']
    interfaces.append({'part':name,'removed_volume_mm3':float(removed.volume()),
        'gaps_to_other_source_solids_mm':{other:float(removed.min_gap(source_solids[other],10.)) for other in critical}})
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report={'status':'PASS','scope':'Section extraction and sampled radial journal-wall measurement; no minimum-wall/strength qualification',
    'source_blend_sha256':source_hash,'source_script_sha256':sha(SECTION_SCRIPT),
    'source_cleaned_candidate_sha256':sha(OUT/'cleaned/candidate.blend'),
    'journal_outer_nominal_radius_mm':journal_r,'bearing_z_mm':[float(bearing.lo[2]),float(bearing.hi[2])],
    'sample_z_mm':zs.tolist(),'wall_samples':walls,'critical_interface_gap_samples':interfaces,
    'xy_section_z_mm':float(zs[len(zs)//2]),'xy_section_polygons':xysections,
    'wall_measurement_scope':'17 sections x720 rays attempted; first chamfer plane720 rays NOT_APPLICABLE,16 cylindrical-land planes11520 rays valid; not whole-part minimum thickness',
    'area_measurement_scope':'All17 cross-sections including the entry chamfer, clipped to nominal journal cylinder',
    'minimum_all_part_wall':'NOT_TESTED','strength':'NOT_TESTED','main_applied':False}
(OUT/'journal_sections.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('J3_JOURNAL',{k:{'valid':v['valid_rays'],'missing':len(v['missing']),'minimum':v['minimum']} for k,v in walls.items()},flush=True)
assert sha(source)==source_hash

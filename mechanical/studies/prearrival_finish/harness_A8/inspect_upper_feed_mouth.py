"""Read-only origin and cross-section inspection of the apparent upper lip.

A disconnected 2D section is not called a disconnected 3D component.  Keep
the original main and both candidates untouched, and report exactly where
the thin cross-section was introduced.
"""
from pathlib import Path
MOUTH_SCRIPT=Path(__file__).resolve();MOUTH_DIR=MOUTH_SCRIPT.parent
MOUTH_HELPER=MOUTH_DIR/'plan_h06_documented_mates.py';__file__=str(MOUTH_HELPER)
exec(compile(MOUTH_HELPER.read_text().split('\nports=json.loads',1)[0],str(MOUTH_HELPER),'exec'),globals())
__file__=str(MOUTH_SCRIPT);OUT=MOUTH_DIR/'assembly_feed_v3'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inputs={
    'main':MOUTH_DIR/'joined_entry_candidate/Pitch_Yoke_baseline.npz',
    'J1':MOUTH_DIR/'joined_entry_candidate/Pitch_Yoke_candidate.npz',
    'J2':MOUTH_DIR/'terminal_threading/cleaned/Pitch_Yoke.npz',
    'J3':OUT/'cleaned/Pitch_Yoke.npz',
}
# In these local coordinates X=radial, Y=tangential, Z=vertical.
a=math.pi/4;co,si=math.cos(a),math.sin(a)
to_local=np.array([[co,si,0,0],[-si,co,0,0],[0,0,1,0]])
to_section=np.array([[0,0,1,0],[1,0,0,0],[0,1,0,0]])
roi=manifold.Manifold.cube([4.,5.,4.]).translate([12.,-2.5,188.])
report={'status':'PASS','scope':'Read-only upper exit section and material-origin inspection',
    'source_blend_sha256':source_hash,'source_script_sha256':sha(MOUTH_SCRIPT),
    'source_inputs':{str(p.relative_to(PROJECT)):sha(p) for p in inputs.values()},
    'candidate_blend_sha256':sha(OUT/'cleaned/candidate.blend'),
    'local_basis':'R at XY 45 degrees; T tangential; Z world height in mm',
    'sections':{},'clipped_material':{},'geometry_changed':False,
    'minimum_all_part_wall':'NOT_TESTED','strength':'NOT_TESTED'}
for name,path in inputs.items():
    z=np.load(path);m=manifold.Manifold(manifold.Mesh64(vert_properties=z['vertices_mm'],tri_verts=z['triangles'].astype(np.uint64))).transform(to_local)
    clipped=m^roi;mm=clipped.to_mesh64()
    np.savez_compressed(OUT/f'upper_mouth_{name}.npz',vertices_mm=np.array(mm.vert_properties[:,:3]),triangles=np.array(mm.tri_verts))
    component_volumes=[float(q.volume()) for q in m.decompose()]
    report['clipped_material'][name]={'clip_volume_mm3':float(clipped.volume()),
        'clipped_component_volumes_mm3':[float(q.volume()) for q in clipped.decompose()],
        'whole_part_transformed_component_volumes_mm3':component_volumes,
        'whole_part_positive_volume_components':sum(v>1e-6 for v in component_volumes),
        'numerical_near_zero_volume_components':sum(abs(v)<=1e-6 for v in component_volumes),
        'topology_authority':'reloaded_verification.json checks the untransformed saved mesh; transformed kernel decomposition is diagnostic only'}
    sections=[]
    for t in [-1.5,-1.,-.75,-.5,-.25,0.,.25,.5,.75,1.,1.5]:
        polygons=[]
        for p in m.transform(to_section).slice(float(t)).to_polygons():
            p=np.array(p)[:,[1,0]];q=np.roll(p,-1,axis=0)
            area=float(abs(np.sum(p[:,0]*q[:,1]-q[:,0]*p[:,1]))/2)
            lo,hi=p.min(0),p.max(0)
            if hi[0]<12 or lo[0]>16 or hi[1]<188 or lo[1]>192:continue
            polygons.append({'area_mm2':area,'bounds_rz_mm':[lo.tolist(),hi.tolist()],'polygon_rz_mm':p.tolist()})
        sections.append({'tangential_offset_mm':t,'polygons':polygons})
    report['sections'][name]=sections
report['finding']={
    'origin':'J1 running-wire clearance, inherited by J2 and J3; absent from the original main section',
    'central_section_remnant_rz_mm':[[13.49999972,190.16645813],[13.77710418,191.0]],
    'central_section_area_mm2':0.12323237946611698,
    'local_thickness_note':'0.2771mm radial section width at this cut is not a whole-part minimum-wall metric',
    'adjacent_section_evidence':'Thin roof section merges into surrounding material by tangential offset +/-1.0mm',
    'physical_part_status':'Continuous printed material, not a separate part or merely a shading artifact',
    'open_issue':'Upper exit roof edge needs a simple opening design and local material/access review before recommending adoption',
    'design_closed':False,
}
(OUT/'upper_mouth_inspection.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('UPPER_MOUTH_SOURCE',report['clipped_material'],flush=True)
for name,rows in report['sections'].items():
    print(name,[(r['tangential_offset_mm'],[(round(p['area_mm2'],5),p['bounds_rz_mm']) for p in r['polygons'] if p['area_mm2']<5]) for r in rows],flush=True)

"""Catalogue contact-envelope threading diagnostic on J1, not terminal CAD.

The dimensions are catalogue nominal references. Crimped wings/tolerances and
the actual CAM socket are not qualified. A failed pose rejects only this
tangent-following insertion attempt; no universal impossibility claim.
"""
from pathlib import Path
SCRIPT=Path(__file__).resolve()
HELPER=SCRIPT.parent.parent/'head_harness/check_loop_source_solids.py'
__file__=str(HELPER)
exec(compile(HELPER.read_text().split('\ngroups=[]')[0],str(HELPER),'exec'),globals())
__file__=str(SCRIPT);OUT=SCRIPT.parent/'joined_entry_candidate'
from interface_completion import replace_owned
route=json.loads((SCRIPT.parent/'joined_entry_screen.json').read_text())
source_pdf=PROJECT/'hardware/v1_2/head_harness_A8_20261003/sources/JST_SH_20261003.pdf'
assert hashlib.sha256(source_pdf.read_bytes()).hexdigest()=='ea3071ca5ee5a6069eba534fa39a10f34c9fb742ee42135a69ab4156bfa0f5de'
for name in ['Yaw_Base','Pitch_Yoke']:
    mesh=np.load(OUT/f'{name}_candidate.npz')
    m=manifold.Manifold(manifold.Mesh64(vert_properties=mesh['vertices_mm'],tri_verts=mesh['triangles'].astype(np.uint64)))
    obj=ss[name].o;replace_owned(name,m);ss[name]=Solid(obj)

cases=[]
for rec in [r for r in route['rows'] if r['yaw_deg']==0]:
    pts=np.asarray(rec['curve_mm']);grad=np.gradient(pts,axis=0)
    for label,dims in [('SSH_nominal_contact_reference',[.8,1.35,3.9]),('SHR04_nominal_housing_reference',[2.8,5.,5.])]:
        for roll in [0,90]:
            hit=None;tested=0
            for i in list(range(0,len(pts),5))+[len(pts)-1]:
                p=pts[i];z=grad[i]/np.linalg.norm(grad[i]);rad=np.r_[p[:2],0.];rad/=np.linalg.norm(rad)
                x=rad-z*np.dot(z,rad)
                if np.linalg.norm(x)<1e-5:x=np.array([0.,0.,1.])-z*z[2]
                x/=np.linalg.norm(x);y=np.cross(z,x)
                if roll==90:x,y=y,-x
                tr=np.column_stack([x,y,z,p])
                box=manifold.Manifold.cube(dims,center=True).transform(tr)
                bb=np.array(box.bounding_box());tested+=1
                for name,s in ss.items():
                    if np.any(bb[:3]>s.hi) or np.any(bb[3:]<s.lo):continue
                    overlap=max(0.,float((box^s.m).volume()))
                    if overlap>1e-4:
                        hit=dict(object=name,curve_index=i,centre_mm=p.tolist(),intersection_mm3=overlap)
                        break
                if hit:break
            cases.append(dict(azimuth_deg=rec['azimuth_deg'],allocation=label,dimensions_mm=dims,
                              roll_deg=roll,poses_tested=tested,status='FAIL' if hit else 'PASS',first_hit=hit))
            print('TERMINAL_ENTRY',rec['azimuth_deg'],label,roll,hit,flush=True)

out=dict(status='BLOCKED' if any(r['status']=='FAIL' for r in cases) else 'PASS',
    scope='Nominal catalogue-envelope tangent-following attempt at zero yaw/pitch only',
    source_blend_sha256=before,source_candidate_sha256=hashlib.sha256((OUT/'candidate.blend').read_bytes()).hexdigest(),
    source_script_sha256=hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
    source_pdf=str(source_pdf.relative_to(PROJECT)),source_pdf_sha256=hashlib.sha256(source_pdf.read_bytes()).hexdigest(),
    source_pdf_page=2,cases=cases,clearance_added_mm=0,
    contact_post_crimp_full_envelope='NOT_TESTED',actual_CAM_mating='BLOCKED',
    arbitrary_orientation_or_disassembled_joint='NOT_TESTED',main_model_changed=False,
    conclusion='J1 wire-curve clearance is not a completed assembly path. Need a compatible open/lay-in joint sequence or a verified terminal insertion design before release.')
(OUT/'terminal_entry.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==before

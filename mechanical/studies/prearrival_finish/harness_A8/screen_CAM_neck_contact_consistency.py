"""Check whether the larger upper-feed contact also fits the neck path.

This deliberately keeps the same 7.6 mm guide and existing candidate prints.
PH reverse feeding is only a comparison, not a selected assembly method.
Catalogue outlines and requested spaces are not finished-crimp tolerances.
"""
from pathlib import Path
THIS=Path(__file__).resolve(); HELPER=THIS.parent/'screen_CAM_complete_head_insertion.py'
__file__=str(HELPER)
exec(compile(HELPER.read_text().split('\nheadsets=',1)[0],str(HELPER),'exec'),globals())
__file__=str(THIS)
NECK=OUT/'neck_contact';NECK.mkdir(exist_ok=True)
PATH_HELPER=A8/'check_coupled_terminal_feed.py'
code='def radial_path'+PATH_HELPER.read_text().split('def radial_path',1)[1].split('\ndef pose(',1)[0]
R=8.;exec(compile(code,str(PATH_HELPER),'exec'),globals())
path,segments=radial_path(7.6,step=.08)
fixed_path=A8.parent/'harness_A2/assembly_safe_review/fourteen_wire_solids.json'
extra=json.loads(fixed_path.read_text())
targets=dict(solids)
for n,r in extra.items():
    targets['fixed_wire_'+n]=manifold.Manifold(manifold.Mesh64(np.asarray(r['vertices_mm']),np.asarray(r['triangles'],dtype=np.uint64)))
target_boxes={n:np.asarray(m.bounding_box()) for n,m in targets.items()}
allocations=[
 dict(id='historical_SH_reference',dims=[.8,1.35,3.9],direction=1,evidence='ASSUMED catalogue-derived historical box'),
 dict(id='larger_SH_requested_space',dims=[1.,1.8,4.1],direction=1,evidence='ASSUMED larger requested space used in the upper-feed checks'),
 dict(id='PH_reverse_catalogue_reference',dims=[1.5,2.08,5.7],direction=-1,evidence='ASSUMED box from PH series outline; not finished-crimp dimensions or exact individual drawing'),
 dict(id='PH_reverse_requested_space',dims=[1.7,2.3,6.],direction=-1,evidence='ASSUMED larger requested space, not a vendor maximum'),
]
started=time.time();rows=[]
for alloc in allocations:
    dims=np.asarray(alloc['dims']);nominal=manifold.Manifold.cube(dims.tolist(),center=True)
    padded=nominal.minkowski_sum(manifold.Manifold.sphere(.3,48));cases=[]
    for phase in [45,135,225,315]:
        ph=math.radians(phase);er=np.array([math.cos(ph),math.sin(ph),0.]);ez=np.array([0.,0.,1.]);et=np.cross(ez,er)
        failures=[];indices=range(len(path)) if alloc['direction']==1 else range(len(path)-1,-1,-1);checked=0
        for idx in indices:
            r,z,a=path[idx];axis=er*math.sin(a)+ez*math.cos(a);x=er*math.cos(a)-ez*math.sin(a)
            rear=r*er+z*ez;center=rear+alloc['direction']*dims[2]/2*axis
            T=np.column_stack([x,et,axis,center]);m=padded.transform(T);bb=np.asarray(m.bounding_box());checked+=1
            for name,target in targets.items():
                tb=target_boxes[name]
                if np.any(bb[:3]>tb[3:]) or np.any(tb[:3]>bb[3:]):continue
                v=max(0.,float((m^target).volume()))
                if v>1e-5:
                    actual=nominal.transform(T);overlap=max(0.,float((actual^target).volume()))
                    failures.append(dict(index=idx,segment=segments[idx],obstacle=name,rear_mm=rear.tolist(),
                        transform_3x4=T.tolist(),padded_intersection_mm3=v,nominal_box_intersection_mm3=overlap,
                        nominal_gap_below_1_mm=float(actual.min_gap(target,1.))))
                    break
            if failures:break
        cases.append(dict(phase_deg=phase,status='BLOCKED' if failures else 'PASS',checked_positions=checked,
            planned_positions=len(path),failures=failures))
    row=dict(**alloc,status='PASS' if all(c['status']=='PASS' for c in cases) else 'BLOCKED',cases=cases)
    rows.append(row);print('NECK_CONTACT_CONSISTENCY',alloc['id'],row['status'],
        [(c['phase_deg'],c['failures'][:1]) for c in cases],flush=True)
report=dict(status='PASS' if rows[1]['status']=='PASS' else 'BLOCKED',
    scope='Finite reference/contact-space sweep on unchanged candidate neck guide; not whole-wire installation',
    script_sha256=sha(THIS),helper_sha256=sha(HELPER),path_helper_sha256=sha(PATH_HELPER),
    source_main_sha256=source_hash,protected_sources=protected,source_fixed_wires_sha256=sha(fixed_path),
    substituted_unadopted_prints={n:dict(path=str(p.relative_to(PROJECT)),sha256=sha(p)) for n,p in replacements.items()},
    source_objects=len(solids),fixed_wires=len(extra),radial_guide_mm=7.6,bend_radius_mm=8.,
    maximum_arc_sampling_step_mm=.08,clearance_padding_mm=.3,rows=rows,
    PH_source_url='https://www.jst-mfg.com/product/pdf/eng/ePH.pdf',
    PH_source_scope='Shared series contact outline, not a maximum post-crimp envelope',
    mating_housings='NOT_TESTED',complete_wire_and_common_body_plug='NOT_TESTED',continuous_sweep='NOT_TESTED',
    candidate_structures_changed=False,main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,
    elapsed_s=time.time()-started)
(NECK/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('NECK_CONTACT_CONSISTENCY_DONE',report['status'],round(time.time()-started,2),flush=True)

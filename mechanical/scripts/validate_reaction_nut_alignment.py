"""M1.52 current checks with a strict two-nut rigid-rotation comparison."""
from common import *
import time


def run_current():
    import validate as v
    from harness_context import Context, sha
    started=time.time();ctx=Context();ss=ctx.ss;v.CHECKS.clear()
    q=P['reaction_nut_alignment'];snapshot=PROJECT/q['baseline']
    inspection_path=PROJECT/q['baseline_inspection']
    prior_geometry=json.loads(inspection_path.read_text())
    assert prior_geometry['sources']['mechanical/mori_v1_2.blend']==sha(snapshot/'mechanical/mori_v1_2.blend')
    expected_ids=set(q['nut_hosts'])
    before=prior_geometry['native_fingerprints'];assert set(before)==set(ctx.print_fingerprints)
    changed={n for n,h in before.items() if h!=ctx.print_fingerprints[n]}
    assert changed==expected_ids,changed
    oldp=json.loads((snapshot/'config/geometry.json').read_text())
    newp=json.loads(json.dumps(P));newp.pop('reaction_nut_alignment')
    oldp.pop('revision');newp.pop('revision');assert oldp==newp
    rows=[]
    for name,host in q['nut_hosts'].items():
        path=inspection_path.parent/(name+'_native_baseline.npz');old=np.load(path)
        points=old['vertices_mm'];c=(points.min(0)+points.max(0))/2
        angle=math.radians(q['rotation_y_deg'])
        r=np.array([[math.cos(angle),0,math.sin(angle)],[0,1,0],[-math.sin(angle),0,math.cos(angle)]])
        target=(points-c)@r.T+c;s=ss[name]
        assert np.array_equal(s.f,old['triangles'])
        error=float(np.linalg.norm(s.v-target,axis=1).max());assert error<5e-5,(name,error)
        volume=float((s.m^ss[host].m).volume());assert abs(volume)<1e-6
        source=manifold.Manifold(manifold.Mesh64(points,old['triangles'].astype(np.uint64)))
        oldvolume=float((source^ss[host].m).volume())
        assert oldvolume>.008
        assert s.o['data_status']=='ASSUMED' and s.o['model_fidelity']=='ALLOCATION_ONLY'
        rows.append(dict(nut=name,host=host,previous_overlap_mm3=oldvolume,corrected_overlap_mm3=volume,
                         rotation_y_deg=q['rotation_y_deg'],maximum_rigid_transform_error_mm=error,
                         unchanged_triangles=True,dimensions_and_evidence_unchanged=True))
    scope=dict(changed_ids=sorted(changed),unchanged_native_parts=len(before)-len(changed),
               printed_solids_unchanged=True,configuration_delta=['revision','reaction_nut_alignment'],
               baseline=str(snapshot.relative_to(PROJECT)),rows=rows)
    v.check('reaction_nut_exact_scope','PASS','两枚试配螺母绕原Y轴转正30°；另199件实体、全部打印件与孔轴保持',scope,
            'Exact world-mesh fingerprints; identical triangles and a rigid rotation with less than0.00005mm float error. No dimension or evidence upgrade.')
    v.check('reaction_nut_pocket_seating','PASS','两处原有约0.00847mm³角部相交消失',rows,
            'Actual closed triangle-solid intersections at zero pose; this is nominal seating, not selected fastener fit.')
    v.actual_checks(ss);v.geometry_checks(ss);v.camera_checks(ss)
    v.access_checks(ss,core_only=True);v.mass_checks(ss);v.v12_checks(ss)
    fresh={r['id'] for r in v.CHECKS}
    prior_path=snapshot/'mechanical/reports/validation.json';prior=json.loads(prior_path.read_text())
    assert prior['counts']['FAIL']==0
    inherited=[]
    for row in prior['checks']:
        if row['id'] in fresh:continue
        record=dict(row)
        record.setdefault('evidence_revision','V1.2-M1.51')
        record.setdefault('evidence_file',str(prior_path.relative_to(PROJECT)))
        record.setdefault('evidence_file_sha256',sha(prior_path))
        record['rerun_this_revision']=False
        record['M1_52_applicability']='Previously scoped result retained; all printed surfaces, hardware except the two named nuts, and datums are byte-identical. Affected rigid collisions/motion rerun. This is not a new physical or complete assembly PASS.'
        inherited.append(record);v.CHECKS.append(record)
    ctx.assert_unchanged()
    result=dict(revision=P['revision'],source_blend_sha256=ctx.source_hash,
        checks=v.CHECKS,counts={s:sum(c['status']==s for c in v.CHECKS) for s in ['PASS','FAIL','NOT_TESTED','BLOCKED','NOT_APPLICABLE']},
        current_rerun_ids=sorted(fresh),inherited_evidence_basis=dict(prior_report=str(prior_path.relative_to(PROJECT)),prior_report_sha256=sha(prior_path),scope=scope),
        historical_superseded_checks=prior['historical_superseded_checks'],
        limits='Nut orientation correction only. Horn/shaft/final fastener selection and complete wired assembly remain BLOCKED.',
        elapsed_s=time.time()-started)
    save_json(ROOT/'reports/reaction_nut_alignment_validation.json',dict(status='PASS',source_blend_sha256=ctx.source_hash,sources=ctx.sources,scope=scope,
              script_sha256=sha(Path(__file__)),physical_fit='NOT_TESTED',complete_reaction_assembly='BLOCKED'))
    save_json(ROOT/'reports/validation.json',result)
    print('M1_52_VALIDATION_COMPLETE',result['counts'],flush=True)
    return result

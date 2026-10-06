"""Cover the first three existing sequential wire motions independently."""
from pathlib import Path
F3_SCRIPT=Path(__file__).resolve();F3_ROOT=F3_SCRIPT.parent
F3_HELPER=F3_ROOT/'check_CAM_sequential_continuous.py';__file__=str(F3_HELPER)
exec(compile(F3_HELPER.read_text().split('\n# Static mixed states',1)[0],str(F3_HELPER),'exec'),globals())
__file__=str(F3_SCRIPT)
F3_OUT=TC_OUT/'first_three_continuous';F3_OUT.mkdir(exist_ok=True)
prior=json.loads((TC_OUT/'continuous/screen.json').read_text())
assert prior['helper_sha256']==sha(SC_HELPER) and prior['source_main_sha256']==source_hash
static=[r for r in prior['static_wire_pairs'] if r['stage']<3]
assert len(static)==9 and all(r['status']=='PASS' for r in static)
contact_source=json.loads((TC_SOURCE/'contacts.json').read_text())
for stage in range(3):
    assert next(r for r in contact_source['rows'] if r['stage']==stage and r['fraction']==0.)['nominal_nonpenetration']=='PASS'
assert all(r['status']=='PASS' for r in contact_source['static_wire_fixture_checks'])
edges=[(s['stage'],a,b) for s in sc_path['stages'][:3] for a,b in zip(s['path'],s['path'][1:])]
priority=[(2,.8),(2,.775),(2,0.)]
edges.sort(key=lambda x:(priority.index((x[0],x[1]['fraction'])) if (x[0],x[1]['fraction']) in priority else len(priority),x[0],x[1]['fraction']))
try:
    for stage,a,b in edges:
        print('FIRST_THREE_EDGE',stage,a['fraction'],b['fraction'],flush=True)
        sc_interval(stage,(a,b),a['fraction'],b['fraction'])
    error=None
except Exception as exc:error=repr(exc)
coverage=[]
for stage in range(3):
    rows=sorted([r for r in sc_passed if r['stage']==stage],key=lambda r:r['interval'][0])
    complete=bool(rows and rows[0]['interval'][0]==0. and rows[-1]['interval'][1]==1.
        and all(a['interval'][1]==b['interval'][0] for a,b in zip(rows,rows[1:])))
    coverage.append({'stage':stage,'complete':complete,'intervals':len(rows)})
good=all(r['complete'] for r in coverage) and not sc_unproved and error is None
report={'status':'PASS' if good else 'BLOCKED','scope':'First three wires only, slots3 then2 then1; nominal forming motion with static mixed wires retained',
    'source_main_sha256':source_hash,'script_sha256':sha(F3_SCRIPT),'helper_sha256':sha(F3_HELPER),
    'source_path_sha256':sha(TC_OUT/'screen.json'),'source_static_proof_sha256':sha(TC_OUT/'continuous/screen.json'),
    'source_static_contact_sha256':sha(TC_SOURCE/'contacts.json'),'static_wire_pairs':static,
    'coverage':coverage,'complete_first_three_coverage':good,'full_four_stage_continuous':'NOT_TESTED',
    'passed_intervals':sc_passed,'unproved_intervals':sc_unproved,'nominal_intermediate_failures':sc_nominal,
    'interval_tests':sc_tests,'error':error,'ordinary_margin_mm':.3,'bare_contact_margin_mm':0.,
    'generic_0_3mm_contact_packing':'BLOCKED','terminal_insertion':'NOT_TESTED','feed_to_start':'NOT_TESTED','ties':'NOT_TESTED',
    'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False,'elapsed_s':time.time()-sc_start}
(F3_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('FIRST_THREE_DONE',report['status'],len(sc_passed),error,flush=True)

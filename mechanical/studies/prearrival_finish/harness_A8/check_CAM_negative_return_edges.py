"""Check the negative-side branch, excluding the already failed48deg jump.

Reuse only the exact, accepted0.85..0.875 constant-control edge from the
previous search. Its overall BLOCKED outcome does not erase that bounded
substep, nor does this local audit certify a whole wire installation.
"""
from pathlib import Path
NR_SCRIPT=Path(__file__).resolve();NR_ROOT=NR_SCRIPT.parent
NR_HELPER=NR_ROOT/'check_CAM_sequential_continuous.py';__file__=str(NR_HELPER)
exec(compile(NR_HELPER.read_text().split('\n# Static mixed states',1)[0],str(NR_HELPER),'exec'),globals())
__file__=str(NR_SCRIPT)
NR_OUT=TC_OUT/'negative_return_branch';NR_OUT.mkdir(exist_ok=True)
nr_src=TC_OUT/'return_corridor/screen.json';nr_path=json.loads(nr_src.read_text())
nr_tail_src=TC_OUT/'critical_return_continuous/screen.json';nr_tail=json.loads(nr_tail_src.read_text())
assert nr_path['status']=='PASS' and nr_tail['status']=='BLOCKED'
assert nr_tail['source_main_sha256']==source_hash
assert nr_tail['helper_sha256']==sha(NR_HELPER)
nr_nodes=[n for n in nr_path['path'] if .8025<=n['fraction']<=.85]
nr_nodes=[{k:n[k] for k in ['fraction','amplitude_mm','side_angle_deg']} for n in nr_nodes]
assert nr_nodes[0]['fraction']==.8025 and nr_nodes[-1]['fraction']==.85
assert nr_tail['path']==[{'fraction':.85,'amplitude_mm':9.,'side_angle_deg':0.},
                         {'fraction':.875,'amplitude_mm':9.,'side_angle_deg':0.}]
reused=nr_tail['accepted_intervals'];assert len(reused)==250
reused=sorted(reused,key=lambda r:r['interval'][0])
assert reused[0]['interval'][0]==.85 and reused[-1]['interval'][1]==.875
assert all(a['interval'][1]==b['interval'][0] for a,b in zip(reused,reused[1:]))
edges=list(zip(nr_nodes,nr_nodes[1:]))
edges.sort(key=lambda ab:(ab[0]['side_angle_deg']==ab[1]['side_angle_deg'],
                          ab[0]['amplitude_mm']==ab[1]['amplitude_mm'],ab[0]['fraction']))
try:
    for a,b in edges:
        print('NEGATIVE_BRANCH_EDGE',a['fraction'],b['fraction'],flush=True)
        sc_interval(3,(a,b),a['fraction'],b['fraction'])
    error=None
except Exception as exc:error=repr(exc)
newrows=sorted(sc_passed,key=lambda r:r['interval'][0]);allrows=sorted(newrows+reused,key=lambda r:r['interval'][0])
coverage=bool(allrows and allrows[0]['interval'][0]==.8025 and allrows[-1]['interval'][1]==.875
              and all(a['interval'][1]==b['interval'][0] for a,b in zip(allrows,allrows[1:])))
good=coverage and not sc_unproved and error is None
report={'status':'PASS' if good else 'BLOCKED','scope':'Only last-wire negative-side return, parameter0.8025..0.875',
    'source_main_sha256':source_hash,'script_sha256':sha(NR_SCRIPT),'helper_sha256':sha(NR_HELPER),
    'source_path_sha256':sha(nr_src),'source_tail_proof_sha256':sha(nr_tail_src),
    'path':nr_nodes+[nr_tail['path'][-1]],'complete_local_coverage':good,'complete_last_wire_coverage':False,
    'new_passed_intervals':newrows,'reused_tail_intervals':reused,'unproved_intervals':sc_unproved,
    'nominal_intermediate_failures':sc_nominal,'interval_tests':sc_tests,'error':error,
    'ordinary_margin_mm':.3,'bare_contact_margin_mm':0.,'generic_0_3mm_contact_packing':'BLOCKED',
    'entry_connection_from_initial_state':'NOT_TESTED','full_four_stage_continuous':'NOT_TESTED',
    'terminal_insertion':'NOT_TESTED','feed_to_start':'NOT_TESTED','ties':'NOT_TESTED',
    'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False,'elapsed_s':time.time()-sc_start}
(NR_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('NEGATIVE_BRANCH_DONE',report['status'],len(newrows),error,flush=True)

"""Apply displacement bounds to the revised local return, retaining failures."""
from pathlib import Path
CC_SCRIPT=Path(__file__).resolve();CC_ROOT=CC_SCRIPT.parent
CC_HELPER=CC_ROOT/'check_CAM_sequential_continuous.py';__file__=str(CC_HELPER)
exec(compile(CC_HELPER.read_text().split('\n# Static mixed states',1)[0],str(CC_HELPER),'exec'),globals())
__file__=str(CC_SCRIPT)
CC_SOURCE=TC_OUT/'return_corridor';CC_OUT=CC_SOURCE/'continuous';CC_OUT.mkdir(exist_ok=True)
cc_path=json.loads((CC_SOURCE/'screen.json').read_text());assert cc_path['status']=='PASS'
edges=list(zip(cc_path['path'],cc_path['path'][1:]))
# The new connection from+48deg to-6deg is checked first, followed by the
# angle changes through the former collision region.
edges.sort(key=lambda ab:(abs(ab[1]['side_angle_deg']-ab[0]['side_angle_deg'])==0.,ab[0]['fraction']))
try:
    for a,b in edges:
        print('RETURN_CONTINUOUS_EDGE',a['fraction'],b['fraction'],flush=True)
        sc_interval(3,(a,b),a['fraction'],b['fraction'])
    error=None
except Exception as exc:error=repr(exc)
rows=sorted(sc_passed,key=lambda r:r['interval'][0])
coverage=bool(rows and rows[0]['interval'][0]==.8 and rows[-1]['interval'][1]==.875
              and all(a['interval'][1]==b['interval'][0] for a,b in zip(rows,rows[1:])))
good=coverage and not sc_unproved and error is None
report={'status':'PASS' if good else 'BLOCKED','scope':'Revised stage3 local return only, parameter0.8..0.875',
    'source_main_sha256':source_hash,'script_sha256':sha(CC_SCRIPT),'helper_sha256':sha(CC_HELPER),
    'source_path_sha256':sha(CC_SOURCE/'screen.json'),'complete_local_coverage':good,
    'passed_intervals':sc_passed,'unproved_intervals':sc_unproved,'nominal_intermediate_failures':sc_nominal,
    'interval_tests':sc_tests,'error':error,'ordinary_margin_mm':.3,'bare_contact_margin_mm':0.,
    'generic_0_3mm_contact_packing':'BLOCKED','full_four_stage_continuous':'NOT_TESTED',
    'terminal_insertion':'NOT_TESTED','feed_to_start':'NOT_TESTED','ties':'NOT_TESTED',
    'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False,'elapsed_s':time.time()-sc_start}
(CC_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('RETURN_CONTINUOUS_DONE',report['status'],len(sc_passed),error,flush=True)

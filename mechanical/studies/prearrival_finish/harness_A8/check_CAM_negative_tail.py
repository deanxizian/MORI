"""Finish the last-wire tail and assemble an explicitly bounded full path."""
from pathlib import Path
NT_SCRIPT=Path(__file__).resolve();NT_ROOT=NT_SCRIPT.parent
NT_HELPER=NT_ROOT/'check_CAM_sequential_continuous.py';__file__=str(NT_HELPER)
exec(compile(NT_HELPER.read_text().split('\n# Static mixed states',1)[0],str(NT_HELPER),'exec'),globals())
__file__=str(NT_SCRIPT)
NT_OUT=TC_OUT/'negative_tail';NT_OUT.mkdir(exist_ok=True)
nt_pre_file=TC_OUT/'negative_prefix/screen.json';nt_ret_file=TC_OUT/'negative_return_branch/screen.json'
nt_pre=json.loads(nt_pre_file.read_text());nt_ret=json.loads(nt_ret_file.read_text())
assert nt_pre['status']==nt_ret['status']=='PASS' and nt_pre['complete_prefix_coverage'] and nt_ret['complete_local_coverage']
assert nt_pre['source_main_sha256']==nt_ret['source_main_sha256']==source_hash
assert nt_pre['helper_sha256']==nt_ret['helper_sha256']==sha(NT_HELPER)
assert nt_pre['path'][-1]==nt_ret['path'][0]
nt_a=nt_ret['path'][-1];nt_b={'fraction':1.,'amplitude_mm':9.,'side_angle_deg':0.}
assert nt_a=={'fraction':.875,'amplitude_mm':9.,'side_angle_deg':0.}
try:sc_interval(3,(nt_a,nt_b),.875,1.);error=None
except Exception as exc:error=repr(exc)
rows=sorted(sc_passed,key=lambda r:r['interval'][0])
covered=bool(rows and rows[0]['interval'][0]==.875 and rows[-1]['interval'][1]==1.
             and all(a['interval'][1]==b['interval'][0] for a,b in zip(rows,rows[1:])))
good=covered and not sc_unproved and error is None
allrows=nt_pre['accepted_intervals']+nt_ret['new_passed_intervals']+nt_ret['reused_tail_intervals']+rows
allrows=sorted(allrows,key=lambda r:r['interval'][0])
complete=good and allrows[0]['interval'][0]==0. and allrows[-1]['interval'][1]==1.
complete=complete and all(a['interval'][1]==b['interval'][0] for a,b in zip(allrows,allrows[1:]))
path=nt_pre['path']+nt_ret['path'][1:]+[nt_b]
assert all(a['fraction']<b['fraction'] for a,b in zip(path,path[1:]))
assert path[0]=={'fraction':0.,'amplitude_mm':9.,'side_angle_deg':0.} and path[-1]==nt_b
report={'status':'PASS' if complete else 'BLOCKED','scope':'Last wire only: complete0..1 prescribed motion with three completed wires retained',
    'source_main_sha256':source_hash,'script_sha256':sha(NT_SCRIPT),'helper_sha256':sha(NT_HELPER),
    'source_prefix_sha256':sha(nt_pre_file),'source_return_sha256':sha(nt_ret_file),
    'complete_tail_coverage':good,'complete_last_wire_coverage':complete,'path':path,
    'new_tail_intervals':rows,'combined_intervals':allrows,'unproved_intervals':sc_unproved,
    'nominal_intermediate_failures':sc_nominal,'interval_tests':sc_tests,'error':error,
    'ordinary_margin_mm':.3,'bare_contact_margin_mm':0.,'generic_0_3mm_contact_packing':'BLOCKED',
    'full_four_stage_continuous':'NOT_TESTED','terminal_insertion':'NOT_TESTED','feed_to_start':'NOT_TESTED','ties':'NOT_TESTED',
    'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False,'elapsed_s':time.time()-sc_start}
(NT_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('NEGATIVE_TAIL_DONE',report['status'],len(rows),len(allrows),error,flush=True)

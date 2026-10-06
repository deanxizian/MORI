#!/usr/bin/env python3
"""Verify bounded receipt, unchanged released CAD and honest status fields."""
from pathlib import Path
import csv, hashlib, json, subprocess, sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def rows(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def main():
    checks={};manifest=read(HERE/'publish_manifest.json')
    checks['released_native_source_hashes_unchanged']=all(sha(ROOT/p)==v for p,v in manifest['native_sources'].items())
    old=read(HERE/'j10_candidate/reports/source_hashes.json')
    checks['power_source_all_copied_files_unchanged']=all(sha(ROOT/p)==v for p,v in old.items())
    initial={'motion_P5R7':'0f7dfd337522c602ecb11e56dab266f54589b256585332075e2b57a84a82e24e',
       'rear_P5R7':'4c44796c21883d3b16ce1212651ffbed90b62edbe0c878175f78eadbe02686f6',
       'power_P5R6':'3e6a76409928e96840aef31cfa43985a6ad00db0c0abed68a6fcb3c2a9f816dc',
       'imu_P5R4':'b960058cd5e8660431ec619fe3c733d1d08a68f19847ed3bcd750c324061ff68'}
    checks['received_initial_four_pcb_hashes_unchanged']=all(sha(ROOT/'hardware/v1_2/kicad'/('MORI_'+k)/('MORI_'+k+'.kicad_pcb'))==v for k,v in initial.items())
    before=sha(HERE/'calculation_results.json')
    cp=subprocess.run([sys.executable,str(HERE/'calculate.py')],capture_output=True,text=True)
    checks['calculations_reproduce']=cp.returncode==0 and before==sha(HERE/'calculation_results.json')
    original=rows(ROOT/'hardware/v1_2/wiring_P5R7/04_线束汇总.csv');new=rows(HERE/'harness_detail.csv')
    checks['all_harnesses_once']=sorted(x['线束'] for x in original)==sorted(x['线束'] for x in new) and len(new)==len({x['线束'] for x in new})
    original={x['线束']:x for x in original}
    checks['all_endpoints_and_pin_maps_preserved']=all(all(x[k]==original[x['线束']][k] for k in ['起点','终点','逐针关系']) for x in new)
    ffc=rows(HERE/'ffc_pinmap.csv')
    checks['18_ffc_pins_once']=sorted(int(x['针号']) for x in ffc)==list(range(1,19))
    checks['ffc_16_18_NC_documented']=all(x['屏幕信号']=='NC' and x['CAM信号']=='NC' for x in ffc if int(x['针号'])>=16)
    tests=rows(HERE/'test_plan.csv');checks['no_fabricated_bench_results']=all(x['状态']=='NOT_TESTED' for x in tests)
    report=read(HERE/'j10_candidate/reports/drc.json');geometry=read(HERE/'j10_candidate/reports/geometry.json')
    checks['candidate_failures_not_hidden']=len(report['violations'])==49 and geometry['status']=='FAIL'
    checks['candidate_ERC_zero']=sum(len(s['violations']) for s in read(HERE/'j10_candidate/reports/erc.json')['sheets'])==0
    hand=read(ROOT/'hardware/v1_2/handoff/mechanical_P5R7_prearrival_A2.json')
    checks['failed_candidate_not_released']=hand['J10_native_check']['status']=='FAIL' and not hand['native_boards_replaced'] and not hand['manufacturing_release']
    checks['handoff_geometry_matches_review']=hand['J10_side_entry']==geometry
    d=read(ROOT/'contracts/electrical_interfaces.json')
    checks['electrical_ffc_no_plug_release']=not d['display_ffc']['direct_plug_approved']
    allowed={'components':{'prearrival_A2','components'},'electrical_interfaces':{'prearrival_A2','display_ffc','safety','mechanical_handoff_addenda'}}
    changes={}
    for kind in allowed:
        old=read(HERE/'inputs'/(kind+'_before_A2.json'));current=read(ROOT/'contracts'/(kind+'.json'))
        changed={k for k in old.keys()|current.keys() if old.get(k)!=current.get(k)}
        changes[kind]=sorted(changed);checks[kind+'_scoped_top_level_diff']=changed<=allowed[kind]
    # Native rendering is an inspection output, never a fabrication export.
    checks['candidate_preview_exists']=(HERE/'j10_candidate/reports/J10_candidate_front.pdf').is_file()
    evidence=read(HERE/'evidence_index.json')
    checks['evidence_hashes_match']=all(sha(HERE/x['path'])==x['sha256'] for x in evidence if x.get('path') and x.get('sha256'))
    result={'status':'PASS' if all(checks.values()) else 'FAIL','scope':'artifact consistency and bounded source preservation ONLY',
       'checks':checks,'contract_changed_top_level_keys':changes,'bench':'NOT_TESTED','J10_DRC':'FAIL',
       'charging_pulse_fuse_and_fit_qualification':'BLOCKED','calculation_command':cp.args,'calculation_stdout':cp.stdout}
    (HERE/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if not all(checks.values()):raise SystemExit(1)

if __name__=='__main__':main()

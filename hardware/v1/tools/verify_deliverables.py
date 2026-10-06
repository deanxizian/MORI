#!/usr/bin/env python3
"""Artifact integrity checks, explicitly separate from physical hardware qualification."""
import csv,hashlib,json,math,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[3];H=R/'hardware/v1';checks=[]
if json.loads((H/'bom_candidates.json').read_text()).get('revision') != 'V1-H0.1':
    raise SystemExit('Historical H0.1 verifier; current procurement checks: tools/publish_procurement_handoff.py. No V1 ERC/DRC or physical-test result is inferred.')
def j(p):return json.loads(p.read_text())
def check(name,ok):
    checks.append({'check':name,'status':'PASS' if ok else 'FAIL'})
    if not ok:raise AssertionError(name)
manifest=j(H/'reports/input_manifest.json')
for name,sha in manifest['inputs'].items():
    if name!='contracts/mechanical_interfaces.json':check('unchanged upstream '+name,hashlib.sha256((R/name).read_bytes()).hexdigest()==sha)
old=j(H/'interfaces/mechanical_V1_A_before_hardware.json');new=j(R/'contracts/mechanical_interfaces.json')
check('original mechanical component allocations unchanged',old['components']==new['components'])
check('original coordinate frame unchanged',old['coordinate_frame']==new['coordinate_frame'])
e=j(R/'contracts/electrical_interfaces.json');check('four actuators / two MCUs',e['actuator_count']==4 and e['mcu_count']==2)
check('no unearned hardware freeze',e['hardware_freeze'] is False and e['pcb_release'] is False)
pins=list(csv.DictReader((R/'hardware/pinmap.csv').open(encoding='utf-8-sig')))
check('root pinmap equals versioned candidate',(R/'hardware/pinmap.csv').read_bytes()==(H/'interfaces/pinmap_V1-H0.1.csv').read_bytes())
for dom in ['MOTION','INTERACTION']:
    gp=[r['gpio'] for r in pins if r['domain']==dom and r['peripheral'] not in ['POWER','RESERVED']];check(dom+' unique GPIO',len(gp)==len(set(gp)))
    check(dom+' no PSRAM/unused straps as application',not set(gp)&{'3','35','36','37','45','46'})
    pads=[int(r['module_pad']) for r in pins if r['domain']==dom];check(dom+' all 41 module pads covered exactly once',sorted(pads)==list(range(1,42)))
for r in j(H/'bom_candidates.json')['items']:
    check('BOM unknown is not zero '+r['id'],r['unit_price'] is None or r['unit_price']>0)
tests=list(csv.DictReader((H/'test_plan.csv').open(encoding='utf-8-sig')))
check('all 15 physical tests remain NOT_TESTED',len(tests)==15 and all(t['status']=='NOT_TESTED' and not t['results'] and not t['evidence'] for t in tests))
d=j(H/'reports/dynamics_sweep.json');check('27 simulation scenarios actually produced',len(d['runs'])==27)
check('calculation is not standing claim',d['status']=='NOT_TESTED' and d['simulation_run']=='PASS')
b=j(H/'reports/budget.json');check('both price coverages incomplete',all(not v['full_quote_coverage'] for v in b['routes'].values()))
check('no V1 manufacturing files',not list((H/'kicad').glob('*.gbr')) and not list((H/'kicad').glob('*.drl')))
cli='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
commands=[]
for args in [[cli,'--version'],[cli,'sch','erc','--help'],[cli,'pcb','drc','--help']]:
    p=subprocess.run(args,capture_output=True,text=True)
    commands.append({'argv':args,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
    check('tool invocation '+' '.join(args[1:]),p.returncode==0)
(H/'reports/tool_check.json').write_text(json.dumps({'date':'2026-09-21','actual_executed_commands':commands,'note':'Only version/help checks; no V1 ERC/DRC execution.'},indent=2)+'\n')
status={'revision':'V1-H0.1','overall':'BLOCKED','artifact_integrity':'PASS','artifact_checks':checks,
 'KiCad':{'version':commands[0]['stdout'].strip(),'V1_native_schematic_exists':False,'V1_native_PCB_exists':False,
          'ERC':{'status':'BLOCKED','executed':False,'error_count':None,'warning_count':None},
          'DRC':{'status':'BLOCKED','executed':False,'error_count':None,'unconnected_count':None},
          'reason':'User-required budget/envelope/parts/power gates not met. A0 results are not V1 evidence.'},
 'physical_tests':'NOT_TESTED','procurement':'BLOCKED','PCB_order':'NOT_AUTHORIZED_NOT_PERFORMED'}
(H/'reports/validation_status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
print(f'{len(checks)} artifact consistency checks PASS. V1 schematic/PCB/ERC/DRC BLOCKED; physical tests NOT_TESTED.')

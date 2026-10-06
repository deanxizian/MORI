#!/usr/bin/env python3
"""Real KiCad ERC plus exported connectivity audit; no PCB mutation or DRC claim."""
from pathlib import Path
from datetime import datetime,timezone
import subprocess,json,hashlib,xml.etree.ElementTree as ET
from collections import Counter
from logic5v_S3 import H,DEST,REPORT,NAME,REV
CLI='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'

def main():
    REPORT.mkdir(parents=True,exist_ok=True);commands=[]
    sch=DEST/(NAME+'.kicad_sch')
    for label,argv in [('erc',[CLI,'sch','erc','--format','json','--severity-all','--exit-code-violations','-o',str(REPORT/'erc.json'),str(sch)]),
                       ('netlist',[CLI,'sch','export','netlist','--format','kicadxml','-o',str(REPORT/'netlist.xml'),str(sch)])]:
        p=subprocess.run(argv,capture_output=True,text=True,timeout=180)
        (REPORT/(label+'.log')).write_text(p.stdout+p.stderr)
        commands.append(dict(argv=argv,returncode=p.returncode,utc=datetime.now(timezone.utc).isoformat()))
    data=json.loads((DEST/'connectivity.json').read_text());actual={};nets={}
    root=ET.parse(REPORT/'netlist.xml').getroot()
    for n in root.findall('.//nets/net'):
        net=n.attrib['name'].lstrip('/');members={(x.attrib['ref'],x.attrib['pin']) for x in n.findall('node')}
        nets[net]=members
        for key in members:actual[key]=net
    # KiCad omits virtual #PWR/#FLG symbols from the physical netlist. Their
    # driving semantics are checked by native ERC, not by fabricating nodes.
    expected={(c['ref'],pn):p['net'] for c in data['components'] if not c['ref'].startswith('#') for pn,p in c['pins'].items() if p['net']}
    diffs=[dict(ref=r,pin=p,expected=n,actual=actual.get((r,p))) for (r,p),n in expected.items() if actual.get((r,p))!=n]
    extra=[dict(ref=r,pin=p,net=n) for (r,p),n in actual.items() if (r,p) not in expected and not n.startswith('unconnected-')]
    old=json.loads((H/'kicad/MORI_power_P2/connectivity.json').read_text())
    oldpins={(c['ref'],pn):p['net'] for c in old['components'] if not c['ref'].startswith('#') for pn,p in c['pins'].items() if p['net']}
    olddiff=[(r,p) for (r,p),n in oldpins.items() if actual.get((r,p))!=n]
    dnp={c.attrib['ref'] for c in root.findall('.//components/comp') if c.find('property[@name="dnp"]') is not None}
    checks={
        'all_declared_ref_pins_match_native_netlist':not diffs and not extra,
        'inherited_circuit_pin_nets_preserved':not olddiff,
        'two_5V_rails_are_distinct':nets.get('+5V_MOTION') and nets.get('+5V_CAM') and not (nets['+5V_MOTION']&nets['+5V_CAM']),
        'raw_service_J6_is_DNP':'J6' in dnp,
        'no_new_PCB_file':not (DEST/(NAME+'.kicad_pcb')).exists(),
        'board_outline_unfrozen':data['size'] is None,
    }
    for n,p,out,j in [(60,'M5','+5V_MOTION','J17'),(70,'C5','+5V_CAM','J18')]:
        checks[f'{p}_physical_pin_mapping']=all(actual.get((f'U{n}',str(pin)))==net for pin,net in [(1,'GND'),(2,p+'_SW'),(3,p+'_VIN'),(4,p+'_FB'),(5,p+'_EN'),(6,p+'_BOOT')])
        checks[f'{p}_BOOT_to_SW_not_ground']=actual.get((f'C{n+2}','1'))==p+'_BOOT' and actual.get((f'C{n+2}','2'))==p+'_SW'
        checks[f'{p}_fused_input']=actual.get((f'F{n}','1'))=='BAT_MON' and actual.get((f'F{n}','2'))==p+'_VIN'
        checks[f'{p}_output_after_inductor']=actual.get((f'L{n}','2'))==out and actual.get((j,'1'))==out and actual.get((j,'2'))=='GND'
        checks[f'{p}_disable_not_tied_to_battery']=nets[p+'_EN']=={(f'U{n}','5'),(f'JP{n}','1')}
    baseline=json.loads((H/'revisions/before_logic5V_S3_20260922/preserve_hashes.json').read_text())
    current={p:hashlib.sha256((H.parents[1]/p).read_bytes()).hexdigest() for p in baseline}
    preserved={p:current[p]==v for p,v in baseline.items()}
    checks['existing_P2_CAD_unchanged']=all(ok for p,ok in preserved.items() if '/kicad/' in p)
    erc=json.loads((REPORT/'erc.json').read_text())
    violations=[v for s in erc.get('sheets',[]) for v in s.get('violations',[])]
    project=json.loads((DEST/(NAME+'.kicad_pro')).read_text())
    ignored={key:value for key,value in project.get('erc',{}).get('rule_severities',{}).items() if value=='ignore'}
    checks['native_ERC_zero_violations']=not violations and commands[0]['returncode']==0
    checks['native_netlist_export_ok']=commands[1]['returncode']==0
    result=dict(revision=REV,status='PASS' if all(checks.values()) else 'FAIL',
        kicad_version=subprocess.check_output([CLI,'--version'],text=True).strip(),
        scope='Schematic and exported netlist only; PCB DRC not applicable to this revision, board/frame intentionally not generated.',
        checks={k:'PASS' if v else 'FAIL' for k,v in checks.items()},
        ERC=dict(violations=len(violations),types=dict(Counter(v['type'] for v in violations)),inherited_ignored_rules=ignored,exclusions=project.get('erc',{}).get('erc_exclusions',[])),
        netlist_differences=diffs,extra_connected_pins=extra,inherited_pin_differences=olddiff,
        preserved_files=preserved,schematic_sha256=hashlib.sha256(sch.read_bytes()).hexdigest(),
        physical_tests='NOT_TESTED',commands=commands)
    (REPORT/'verification.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(result['status'], 'ERC',len(violations),'net differences',len(diffs), 'checks',len(checks))
    if result['status']!='PASS':
        print(json.dumps({k:v for k,v in checks.items() if not v},indent=2));print(json.dumps(diffs[:10]));print('DNP exported',dnp)
        raise SystemExit(1)

if __name__=='__main__':main()

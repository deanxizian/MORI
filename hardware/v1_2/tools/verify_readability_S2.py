#!/usr/bin/env python3
"""Check S2 identity/connectivity against the pre-S2 files, including P2 copies.

P1 native CAD verification is reused only if its source hashes are current.
P2 ERC/netlists are independent of its unfinished PCB layout. No DRC claim for P2.
"""
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
import subprocess,json,hashlib
from verify_functional_schematic import native,nets

H=Path(__file__).resolve().parents[1];CLI='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
A=H/'revisions/before_readability_S2_20260922';O=H/'reports/readability_S2'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def p2(name):
    d=H/'kicad'/name;o=O/name;o.mkdir(exist_ok=True)
    commands=[]
    for argv in [[CLI,'sch','erc','--format','json','--severity-all','--exit-code-violations','-o',str(o/'erc.json'),str(d/(name+'.kicad_sch'))],
                 [CLI,'sch','export','netlist','--format','kicadxml','-o',str(o/'netlist.xml'),str(d/(name+'.kicad_sch'))]]:
        p=subprocess.run(argv,capture_output=True,text=True,timeout=180)
        commands.append(dict(argv=argv,returncode=p.returncode,stdout=p.stdout,stderr=p.stderr))
    (o/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    return name,commands


def main():
    with ThreadPoolExecutor(3) as pool:cmds=dict(pool.map(p2,['MORI_'+k+'_P2' for k in ['motion','power','imu']]))
    baseline=json.loads((A/'before_hashes.json').read_text());cad=json.loads((H/'reports/cad_validation.json').read_text())
    checks=[];boards={}
    def check(n,ok,detail):checks.append(dict(name=n,status='PASS' if ok else 'FAIL',detail=detail))
    check('P1 current native verification',cad['status']=='PASS',cad['status'])
    for name in ['MORI_'+k+'_'+v for v in ['P1','P2'] for k in ['motion','power','imu']]:
        d=H/'kicad'/name;sch=d/(name+'.kicad_sch');before=native(A/name/(name+'.kicad_sch'));after=native(sch)
        check(name+' root and component/pin identities',before[:2]==after[:2],len(after[1]))
        pcb=d/(name+'.kicad_pcb');check(name+' PCB unchanged by S2',sha(pcb)==baseline[str(pcb.relative_to(H.parents[1]))],sha(pcb))
        original=H/'revisions/netlabels_before_functional_20260922'/name.replace('_P2','_P1')/'netlist.xml'
        if name.endswith('P1'):
            out=H/'reports/cad'/name
            for rel,digest in cad['boards'][name]['input_hashes'].items():check(name+' fresh '+rel,sha(H.parents[1]/rel)==digest,digest)
        else:
            out=O/name
            check(name+' native commands',all(c['returncode']==0 for c in cmds[name]),[c['returncode'] for c in cmds[name]])
        erc=json.loads((out/'erc.json').read_text());count=sum(len(s['violations']) for s in erc['sheets'])
        old,new=nets(original),nets(out/'netlist.xml');delta=[n for n in old.keys()|new.keys() if old.get(n)!=new.get(n)]
        check(name+' ERC',count==0,count);check(name+' exact named net membership',not delta,delta)
        boards[name]=dict(schematic_sha256=sha(sch),erc=count,net_count=len(new),components=len(after[1]),pcb_validation='P1: current native report' if name.endswith('P1') else 'P2: NOT INCLUDED; unfinished PCB rules/layout')
    export=json.loads((O/'export.json').read_text())
    for name,digest in export['source_schematic_sha256'].items():check(name+' PDF source current',sha(H/'kicad'/name/(name+'.kicad_sch'))==digest,digest)
    report=dict(utc=datetime.now(timezone.utc).isoformat(),drawing_revision='S2',status='PASS' if all(c['status']=='PASS' for c in checks) else 'FAIL',boards=boards,checks=checks,physical_tests='NOT_TESTED',manufacturing_release=False)
    (O/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(checks),'checks')
    if report['status']!='PASS':
        print(json.dumps([c for c in checks if c['status']=='FAIL'],indent=2));raise SystemExit(1)


if __name__=='__main__':main()

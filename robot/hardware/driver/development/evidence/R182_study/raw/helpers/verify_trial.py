"""Run native checks and independent copper regression; capture actual commands.

KiCad 10.0.7 --save-board normalizes three project metadata defaults. If and only
if these exact differences are present, preserve the normalized file as evidence
and restore the source project bytes before read-only verification. Never alter
rules, geometry, exclusions or other project changes as a side effect.
"""
import argparse
import copy
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

CLI='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'


def verify(baseline, candidate, output):
    baseline=Path(baseline).resolve();candidate=Path(candidate).resolve();output=Path(output).resolve()
    output.mkdir(parents=True,exist_ok=False)
    source=baseline/'MORI_Interface_C3.kicad_pro';dest=candidate/source.name
    original=source.read_bytes();actual=dest.read_bytes();normalization=None
    if actual!=original:
        a=json.loads(original);b=json.loads(actual);expected=copy.deepcopy(a)
        for item in expected['board']['design_settings']['teardrop_parameters']:
            item.setdefault('td_enabled',False)
        for key in ['net_colors','netclass_assignments']:
            if expected['net_settings'][key] is None:expected['net_settings'][key]={}
        if b!=expected:
            raise ValueError('Unexpected project changes; not restoring anything')
        (output/'kicad_normalized_project.json').write_bytes(actual)
        normalization={'reason':'Only KiCad save normalization of disabled teardrops and empty maps; original project bytes restored',
                       'source_sha256':hashlib.sha256(original).hexdigest(),'normalized_sha256':hashlib.sha256(actual).hexdigest()}
        dest.write_bytes(original)
    board=candidate/'MORI_Interface_C3.kicad_pcb';board_before=hashlib.sha256(board.read_bytes()).hexdigest()
    commands=[]
    def run(argv):
        r=subprocess.run(argv,cwd=candidate,text=True,capture_output=True)
        record={'argv':list(map(str,argv)),'cwd':str(candidate),'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
        commands.append(record)
        (output/'commands.json').write_text(json.dumps(commands,indent=2,ensure_ascii=False)+'\n')
        return r
    version=run([CLI,'version']).stdout.strip()
    drc=run([CLI,'pcb','drc','--format','json','--schematic-parity','--refill-zones','--severity-all','--exit-code-violations','-o',str(output/'drc.json'),str(board)])
    erc=run([CLI,'sch','erc','--format','json','--severity-all','--exit-code-violations','-o',str(output/'erc.json'),str(candidate/'MORI_Interface_C3.kicad_sch')])
    regression=run([sys.executable,str(Path(__file__).with_name('audit_candidate.py')),str(baseline/board.name),str(board),str(output/'regression.json')])
    ina300=run([sys.executable,str(Path(__file__).with_name('audit_ina300_return.py')),str(board),str(output/'ina300-return.json')])
    assert drc.returncode in (0,5) and erc.returncode in (0,5) and regression.returncode==0 and ina300.returncode==0
    assert dest.read_bytes()==original and hashlib.sha256(board.read_bytes()).hexdigest()==board_before
    d=json.loads((output/'drc.json').read_text());e=json.loads((output/'erc.json').read_text());r=json.loads((output/'regression.json').read_text());i=json.loads((output/'ina300-return.json').read_text())
    result={'executed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'kicad_version':version,'board_sha256':board_before,
            'normalization':normalization,'violations':len(d['violations']),'unconnected_items':len(d['unconnected_items']),
            'schematic_parity':len(d.get('schematic_parity',[])),'erc_violations':sum(len(s['violations']) for s in e.get('sheets',[])),
            'regression_status':r['regression_status'], 'new_reference_gaps':sum(x['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']>1e-6 for x in r['new_copper_review']),
            'new_body_projection_candidates':sum(bool(x['body_projections_outside_existing_lands']) for x in r['new_copper_review']),
            'historical_transition_flags':sum(x['status']=='FAIL' for x in r['reference_transitions']),
            'ina300_rlimit_return_screen':i['direct_return_screen'],
            'manufacturer_layout_qualification':'NOT_TESTED',
            'whole_board_visual':'NOT_TESTED','physical':'NOT_TESTED','manufacturing_release':False}
    result['engineering_status']='FAIL' if result['unconnected_items'] or result['violations'] or result['schematic_parity'] or result['erc_violations'] or i['direct_return_screen']=='FAIL' else 'UNVALIDATED'
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('baseline');p.add_argument('candidate');p.add_argument('output');a=p.parse_args();verify(a.baseline,a.candidate,a.output)

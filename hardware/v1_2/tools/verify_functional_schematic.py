#!/usr/bin/env python3
"""Compare functional drawings to the archived net-label originals.

Requires fresh verify_cad.py reports. Does not run/regenerate or write any PCB.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import xml.etree.ElementTree as ET
from functional_schematic import sexpr

H=Path(__file__).resolve().parents[1]
ARCHIVE=H/'revisions/netlabels_before_functional_20260922'
NAMES=['MORI_motion_P1','MORI_imu_P1','MORI_power_P1']


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def native(path):
    tree=sexpr(path.read_text())
    symbols={}
    counts={key:sum(isinstance(x,list) and x[0]==key for x in tree) for key in ['label','wire','junction']}
    root=next(x[1] for x in tree if isinstance(x,list) and x[0]=='uuid')
    for s in tree:
        if not isinstance(s,list) or s[0]!='symbol' or not any(isinstance(x,list) and x[0]=='lib_id' for x in s):continue
        p={json.loads(x[1]):json.loads(x[2]) for x in s if isinstance(x,list) and x[0]=='property'}
        symbols[p['Reference']]={
            'value':p.get('Value',''), 'footprint':p.get('Footprint',''), 'datasheet':p.get('Datasheet',''),
            'uuid':next(x[1] for x in s if isinstance(x,list) and x[0]=='uuid'),
            'pins':{json.loads(x[1]):next(y[1] for y in x if isinstance(y,list) and y[0]=='uuid') for x in s if isinstance(x,list) and x[0]=='pin'}}
    return root,symbols,counts


def nets(path):
    return {n.get('name'):sorted((x.get('ref'),x.get('pin')) for x in n.findall('node')) for n in ET.parse(path).findall('./nets/net')}


def main():
    hashes=json.loads((ARCHIVE/'before_hashes.json').read_text())
    cad=json.loads((H/'reports/cad_validation.json').read_text())
    results={};checks=[]
    def check(name,ok,detail):checks.append(dict(name=name,status='PASS' if ok else 'FAIL',detail=detail))
    check('fresh native ERC / DRC / parity checks',cad['status']=='PASS',cad['status'])
    for name in NAMES:
        folder=H/'kicad'/name
        before=native(ARCHIVE/name/(name+'.kicad_sch'))
        after=native(folder/(name+'.kicad_sch'))
        oldnets=nets(ARCHIVE/name/'netlist.xml');newnets=nets(H/'reports/cad'/name/'netlist.xml')
        changed=[r for r in before[1].keys()|after[1].keys() if before[1].get(r)!=after[1].get(r)]
        delta=[n for n in oldnets.keys()|newnets.keys() if oldnets.get(n)!=newnets.get(n)]
        check(name+' component identities, values, footprints, datasheets, UUIDs and pin UUIDs',not changed,changed)
        check(name+' named net memberships including NC pins',not delta,delta)
        check(name+' root sheet UUID',before[0]==after[0],after[0])
        for ext in ['.kicad_pcb','/connectivity.json']:
            file='connectivity.json' if ext.startswith('/') else name+ext
            current=sha(folder/file)
            check(name+' unchanged '+file,current==hashes[name][file],current)
        for file,digest in cad['boards'][name]['input_hashes'].items():
            check('current native result '+file,sha(H.parents[1]/file)==digest,digest)
        results[name]=dict(before=before[2],after=after[2],nets=len(newnets),components=len(after[1]),
            native_checks=cad['boards'][name]['counts'],
            project_file_hash_changed_since_start=sha(folder/(name+'.kicad_pro'))!=hashes[name][name+'.kicad_pro'],
            project_note='The layout script never writes .kicad_pro. An open KiCad session may update project preferences; current native checks record the file actually used.')
    report=dict(run_utc=datetime.now(timezone.utc).isoformat(),drawing_revision='S2',
        cad_report_sha256=sha(H/'reports/cad_validation.json'),
        status='PASS' if all(c['status']=='PASS' for c in checks) else 'FAIL',
        boards=results,checks=checks,PCB_MODIFIED=False,NETLIST_MODIFIED=False,
        physical_validation='NOT_TESTED',manufacturing_release=False,
        scope='Drawing organization, symbol graphics and real local wires only. Existing hardware release gates remain unchanged.')
    out=H/'reports/functional_schematic';out.mkdir(exist_ok=True)
    (out/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],checks=len(checks),boards=results),indent=2))
    if report['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()

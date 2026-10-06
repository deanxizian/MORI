#!/usr/bin/env python3
"""Run native ERC/DRC, then compare routed pads/netlist/contracts. No fabrication.

Run with KiCad's Python (pcbnew). Reports preserve rule coverage and return codes.
Does not regenerate or overwrite the routed design.
"""
from pathlib import Path
from datetime import datetime, timezone
import concurrent.futures
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
import pcbnew

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / 'hardware/v1_2'
CLI = os.environ.get('KICAD_CLI', '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli')
NAMES = ['MORI_motion_P1', 'MORI_imu_P1', 'MORI_power_P1']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_native(name):
    folder = HERE / 'kicad' / name
    out = HERE / 'reports/cad' / name
    out.mkdir(parents=True, exist_ok=True)
    commands = [
        [CLI, 'sch', 'erc', '--format', 'json', '--severity-all', '--exit-code-violations', '-o', str(out / 'erc.json'), str(folder / (name + '.kicad_sch'))],
        [CLI, 'pcb', 'drc', '--format', 'json', '--severity-all', '--all-track-errors', '--schematic-parity', '--refill-zones', '--exit-code-violations', '-o', str(out / 'drc_routed.json'), str(folder / (name + '.kicad_pcb'))],
        [CLI, 'sch', 'export', 'netlist', '--format', 'kicadxml', '-o', str(out / 'netlist.xml'), str(folder / (name + '.kicad_sch'))],
        [CLI, 'sch', 'export', 'svg', '-o', str(HERE / 'previews' / name), str(folder / (name + '.kicad_sch'))],
    ]
    log = []
    for argv in commands:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=150)
        log.append(dict(argv=argv, returncode=p.returncode, stdout=p.stdout, stderr=p.stderr))
    (out / 'validation_commands.json').write_text(json.dumps(log, indent=2) + '\n')
    return name, log


def main():
    started = datetime.now(timezone.utc).isoformat()
    # Different boards are independent; PCB read/geometry inspection stays serial.
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        logs = dict(pool.map(run_native, NAMES))
    checks, boards = [], {}

    def check(name, ok, detail):
        checks.append(dict(name=name, status='PASS' if ok else 'FAIL', detail=detail))

    elec = json.loads((ROOT / 'contracts/electrical_interfaces.json').read_text())
    for name in NAMES:
        folder = HERE / 'kicad' / name
        out = HERE / 'reports/cad' / name
        data = json.loads((folder / 'connectivity.json').read_text())
        pro = json.loads((folder / (name + '.kicad_pro')).read_text())
        drc = json.loads((out / 'drc_routed.json').read_text())
        erc = json.loads((out / 'erc.json').read_text())
        b = pcbnew.LoadBoard(str(folder / (name + '.kicad_pcb')))
        fps = {f.GetReference(): f for f in b.GetFootprints()}
        netlist = ET.parse(out / 'netlist.xml').getroot()
        nets = {(n.attrib['ref'], n.attrib['pin']): net.attrib['name'] for net in netlist.findall('./nets/net') for n in net.findall('node')}
        mismatches = []
        for c in data['components']:
            if not c['footprint']:
                continue
            if c['ref'] not in fps:
                mismatches.append((c['ref'], 'missing footprint'))
                continue
            actual = {p.GetNumber(): p.GetNetname() for p in fps[c['ref']].Pads() if p.GetNumber()}
            for pin, p in c['pins'].items():
                if not p['net']:
                    ncnet = actual.get(pin, '')
                    # KiCad assigns a unique synthetic net to a no-connect pad.
                    isolated_nc = ncnet.startswith('unconnected-(') and sum(q.GetNetname()==ncnet for f in fps.values() for q in f.Pads())==1 and not any(t.GetNetname()==ncnet for t in b.GetTracks())
                    if ncnet not in ['', None] and not isolated_nc:
                        mismatches.append((c['ref'], pin, 'NC connected', ncnet))
                    continue
                expected = '/' + p['net']
                if actual.get(pin) != expected or nets.get((c['ref'], pin)) != expected:
                    mismatches.append((c['ref'], pin, expected, actual.get(pin), nets.get((c['ref'], pin))))
        counts = dict(erc=sum(len(s['violations']) for s in erc['sheets']),
                      drc=len(drc['violations']), unconnected=len(drc['unconnected_items']),
                      schematic_parity=len(drc['schematic_parity']))
        check(name + ' native checks', all(v == 0 for v in counts.values()) and all(x['returncode'] == 0 for x in logs[name]), counts)
        check(name + ' pad/netlist/connectivity agreement', not mismatches, mismatches)
        exclusions = pro['board']['design_settings'].get('drc_exclusions', [])
        check(name + ' no individual DRC exclusions', not exclusions, exclusions)
        check(name + ' PCB rule coverage', not drc['ignored_checks'], drc['ignored_checks'])
        expected_holes = [c for c in data['components'] if c['ref'].startswith('H')]
        holes = []
        for c in expected_holes:
            pad = list(fps[c['ref']].Pads())[0]
            holes.append(dict(reference=c['ref'], at_mm=[pcbnew.ToMM(pad.GetPosition().x), pcbnew.ToMM(pad.GetPosition().y)], drill_mm=pcbnew.ToMM(pad.GetDrillSize().x)))
        check(name + ' mechanical hole coordinates', all(abs(h['at_mm'][i]-c['at'][i]) < 1e-5 and abs(h['drill_mm']-2.2) < 1e-5 for h,c in zip(holes, expected_holes) for i in [0,1]), holes)
        sources = [folder/(name+e) for e in ['.kicad_sch', '.kicad_pcb', '.kicad_pro']]
        boards[name] = dict(counts=counts, footprints=len(fps), tracks_and_vias=len(b.GetTracks()), copper_layers=b.GetCopperLayerCount(), holes=holes,
                            erc_ignored_rules=erc['ignored_checks'], drc_ignored_rules=drc['ignored_checks'],
                            erc_rule_note='KiCad default single-global-label, four-way-junction, SPICE-model and footprint-filter rules are not enabled. No individual ERC exclusions added; no SPICE claim.',
                            input_hashes={str(p.relative_to(ROOT)):sha(p) for p in sources}, status='PROTOTYPE_UNVALIDATED')
        if name == 'MORI_motion_P1':
            u = next(c for c in data['components'] if c['ref']=='U100')
            bad = [p for p in elec['pinmap'] if p['domain']=='motion' and u['pins'][p['carrier_pad'].split('.')[1]]['net'] != p['net']]
            check('published GPIOs match native module nets', not bad, bad)
    result = dict(revision=elec['revision'], run_utc=started, kicad_version=subprocess.check_output([CLI, '--version'],text=True).strip(),
                  status='PASS' if all(c['status']=='PASS' for c in checks) else 'FAIL', boards=boards, checks=checks,
                  manufacturing_release=False, BENCH='NOT_TESTED', ROBOT='NOT_TESTED',
                  limit='Native connectivity/rule checks only; not power, solderability, EMI, thermal, battery or robot qualification.')
    (HERE / 'reports/cad_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':result['status'], 'checks':len(checks), 'boards':{n:x['counts'] for n,x in boards.items()}},indent=2))
    if result['status'] != 'PASS':
        sys.exit(1)


if __name__ == '__main__':
    main()

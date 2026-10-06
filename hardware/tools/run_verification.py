#!/usr/bin/env python3
"""Run real local checks, record argv/exit codes; never flash or fabricate."""
from pathlib import Path
import argparse, datetime, hashlib, json, subprocess

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
CLI = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
KPY = '/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3'
parser = argparse.ArgumentParser()
parser.add_argument('group', choices=['software', 'cad'])
group = parser.parse_args().group
records = []

def run(name, argv):
    start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    log = ROOT / 'reports' / (name + '.log')
    with log.open('w') as output:
        result = subprocess.run(argv, cwd=PROJECT, stdout=output, stderr=subprocess.STDOUT)
    records.append(dict(name=name, argv=argv, cwd=str(PROJECT), start_utc=start,
                        exit_code=result.returncode, log=str(log.relative_to(ROOT)),
                        log_sha256=hashlib.sha256(log.read_bytes()).hexdigest()))
    (ROOT / 'reports' / ('verification_commands_' + group + '.json')).write_text(
        json.dumps(records, indent=2, ensure_ascii=False) + '\n')
    print(name + ': exit ' + str(result.returncode), flush=True)
    return result.returncode

if group == 'software':
    run('host_tests', ['sh', 'hardware/tests/run_host_tests.sh'])
    run('toolchain_versions', ['/bin/bash', '-c',
        'source /Users/dean/esp/esp-idf/export.sh && idf.py --version && '
        'xtensa-esp-elf-gcc --version && git -C /Users/dean/esp/esp-idf rev-parse HEAD && '
        'git -C /Users/dean/esp/esp-idf status --porcelain'])
    run('idf_build', ['/bin/bash', '-c',
        'source /Users/dean/esp/esp-idf/export.sh && '
        'idf.py -C hardware/firmware reconfigure && idf.py -C hardware/firmware build'])
else:
    run('kicad_version', [CLI, 'version'])
    if run('kicad_generate', [KPY, 'hardware/tools/generate_kicad.py']) != 0:
        raise SystemExit('Generation failed: do not use stale checks')
    run('erc_run', [CLI, 'sch', 'erc', 'hardware/kicad/MORI_carrier.kicad_sch',
        '--format', 'json', '--exit-code-violations', '-o', 'hardware/reports/erc.json'])
    run('drc_run', [CLI, 'pcb', 'drc', 'hardware/kicad/MORI_carrier.kicad_pcb',
        '--format', 'json', '--schematic-parity', '--exit-code-violations', '-o', 'hardware/reports/drc.json'])
    run('schematic_export', [CLI, 'sch', 'export', 'svg', 'hardware/kicad/MORI_carrier.kicad_sch',
        '-o', 'hardware/reports/schematic_svg'])
    run('pcb_export', [CLI, 'pcb', 'export', 'svg', 'hardware/kicad/MORI_carrier.kicad_pcb',
        '--mode-single', '--exclude-drawing-sheet', '--page-size-mode', '2',
        '--layers', 'F.Cu,B.Cu,F.Silkscreen,Edge.Cuts,Dwgs.User',
        '-o', 'hardware/reports/pcb_preview.svg'])

# A known unrouted PCB must retain its nonzero DRC result.
raise SystemExit(1 if any(r['exit_code'] != 0 for r in records) else 0)

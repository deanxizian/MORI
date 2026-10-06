#!/usr/bin/env python3
"""Run with KiCad Python. Cross-file audit and an honest revision status file."""
from pathlib import Path
import json,hashlib,csv,xml.etree.ElementTree as ET
import pcbnew as k
R=Path(__file__).resolve().parents[1];ROOT=R.parents[2]
cs=json.loads((R/'kicad/connectivity.json').read_text())
board=k.LoadBoard(str(R/'kicad/MORI_carrier.kicad_pcb'))
fps={f.GetReference():f for f in board.GetFootprints()}
expected={(c['ref'],str(pn)):pin['net'] for c in cs for pn,pin in c['pins'].items() if pin['net']}
xml=ET.parse(R/'reports/netlist.xml')
actual={}
for net in xml.findall('.//nets/net'):
    for n in net.findall('node'):actual[(n.get('ref'),n.get('pin'))]=net.get('name').lstrip('/')
checked=0
for key,net in expected.items():
    assert actual[key]==net,(key,actual.get(key),net)
    ref,pn=key;pad=next(p for p in fps[ref].Pads() if p.GetNumber()==pn)
    assert str(pad.GetNetname()).lstrip('/')==net,(key,pad.GetNetname(),net)
    checked+=1
assert expected[('J10','3')]=='HEAD_SIGNAL_5V'
assert expected[('U6','3')]=='HEAD_PWM' and expected[('U6','4')]=='HEAD_SIGNAL_5V'
assert expected[('U6','6')]=='HEAD_5V'
rows=list(csv.DictReader((R/'wiring.csv').open()))
for row in rows:
    if row['pin']:
        assert expected[(row['carrier'],row['pin'])]==row['net'],row
assert (R/'pinmap.csv').read_bytes()==(ROOT/'hardware/pinmap.csv').read_bytes()
defaults=(R/'firmware/sdkconfig.defaults').read_text()
for flag in ['MORI_ENABLE_BALANCE','MORI_POWER_STAGE_VERIFIED','MORI_HEAD_VERIFIED']:
    assert 'CONFIG_'+flag+'=n' in defaults
assert 'ledc_fade_func_install(0)' in (R/'firmware/main/motor.c').read_text()
fit=json.loads((R/'mechanical/fit_review.json').read_text())
for name,digest in fit['mechanical_source_sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
baseline=json.loads((R/'reports/baseline_firmware_hashes.json').read_text())
# Baseline keys are project-relative paths recorded before the copy.
baseline_ok=[]
for name,digest in baseline.items():
    p=Path(name)
    if not p.is_absolute():
        p=ROOT/p if (ROOT/p).exists() else ROOT/'hardware'/p
    assert p.exists(),(name,str(p))
    assert hashlib.sha256(p.read_bytes()).hexdigest()==digest,name
    baseline_ok.append(name)
drc=json.loads((R/'reports/drc_routed.json').read_text())
summary={'revision':'A0.5','checked_electrical_pin_nets':checked,'wiring_rows_checked':sum(bool(row['pin']) for row in rows),
    'offboard_wiring_rows_retained':sum(not row['pin'] for row in rows),
    'netlist_board_wiring_consistency':'PASS','GPIO_baseline_unchanged':'PASS',
    'root_mechanics_unchanged':'PASS','baseline_firmware_unchanged':'PASS',
    'baseline_files_checked':len(baseline_ok),'default_motion_locked':'PASS',
    'native_DRC_counts':{key:len(drc.get(key,[])) for key in ['violations','unconnected_items','schematic_parity']},
    'footprints':len(fps),'tracks_and_vias':len(board.GetTracks()),'zones':len(board.Zones()),
    'firmware_build':json.loads((R/'reports/idf_build_command.json').read_text()),
    'simulated_assertions':163+22+10,'physical_tests':'NOT_TESTED','fabrication_allowed':False,
    'board_sha256':hashlib.sha256((R/'kicad/MORI_carrier.kicad_pcb').read_bytes()).hexdigest()}
(R/'reports/audit.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(summary,indent=2,ensure_ascii=False))

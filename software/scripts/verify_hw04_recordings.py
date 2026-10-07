#!/usr/bin/env python3
"""Read-only replay acceptance for versioned simulation evidence, never device IO."""
import csv
import hashlib
import json
import math
import pathlib
import sys

SW=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SW/'tools'))
from mori_cli import replay

adopted=json.loads((SW/'reports/hw04_adoption.json').read_text())
for name,sha in adopted['old_simulated_sha256'].items():
    assert hashlib.sha256((SW/name).read_bytes()).hexdigest()==sha,name
old=replay(SW/'reports/SIMULATED_release_estop.csv')
assert old['device_metadata']['requirements']=='HW-SW-0.2'
assert old['device_metadata']['wheel_counts_per_turn']=='1204.44'
assert old['source']=='SIMULATED'
print('PASS historical recording retains HW-SW-0.2 / 1204.44; all 24 old files unchanged')
for scenario,frames in [('estop',1000),('reset',400)]:
    path=SW/f'reports/SIMULATED_hw04_{scenario}.csv'
    result=replay(path)
    meta=result['device_metadata']
    assert result['source']=='SIMULATED' and result['rows']==frames
    assert meta['requirements']=='HW-SW-0.4' and meta['firmware']=='SW-0.4'
    assert meta['wheel_counts_per_turn']=='979.616'
    assert math.isclose(float(meta['wheel_m_per_count']),math.pi*.095/979.616,abs_tol=5e-13)
    assert meta['physical']=='NOT_TESTED' and meta['timing']=='INJECTED'
    assert all(meta[key]=='0' for key in ('power_gate','balance_gate','head_gate','axes_gate'))
    with path.open() as f: rows=list(csv.DictReader(f))
    assert all(row['enabled']=='0' for row in rows)
    if scenario=='estop':
        assert all(row['state']=='FAULT' and row['fault']=='2' for row in rows[frames//2:])
    else:
        assert result['resets_or_clock_discontinuities']==1
        assert all(row['state']=='DISARMED' for row in rows)
    print(f'PASS {path.name}: {frames} rows, scale / closed gates / {scenario} / replay verified; hardware NOT_TESTED')

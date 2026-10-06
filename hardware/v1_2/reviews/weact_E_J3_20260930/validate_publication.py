# -*- coding: utf-8 -*-
"""Read native boards and validate the published E/J3 handoff, without CAD edits."""
from update_native_P5R7 import *
from datetime import datetime, timezone

REV = 'V1.2-H0.5-P5R7'
errors = []

def check(condition, message):
    if not condition:
        errors.append(message)

def readcsv(path):
    with path.open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))

def no_revision(rows):
    return [{key: val for key, val in row.items() if key != 'revision'} for row in rows]

electrical = json.loads((ROOT/'contracts/electrical_interfaces.json').read_text())
components = json.loads((ROOT/'contracts/components.json').read_text())
handoff = json.loads((H/'handoff/mechanical_P5R7.json').read_text())
check(electrical['revision'] == components['revision'] == handoff['revision'] == REV, 'Contract revision mismatch')

boards = {}
padmap = {}
for name, info in electrical['pcb_projects'].items():
    path = ROOT/info['path']/(name+'.kicad_pcb')
    check(sha(path) == info['native_checks']['source_sha256'], name+' native check hash mismatch')
    check(sha(path) == handoff['boards'][name]['pcb_sha256'], name+' handoff hash mismatch')
    boards[name] = k.LoadBoard(str(path))
    for f in boards[name].GetFootprints():
        for p in f.Pads():
            padmap.setdefault((name, f.GetReference(), p.GetNumber()), []).append((f, p))
for path, digest in handoff['source_manifest'].items():
    check(sha(ROOT/path) == digest, 'Published source hash mismatch: '+path)

snap = HERE/'sources/pre_publish'
before_pinmap = readcsv(snap/'pinmap.csv')
after_pinmap = readcsv(ROOT/'hardware/pinmap.csv')
check(no_revision(before_pinmap) == no_revision(after_pinmap), 'GPIO/pin assignments changed')
check(all(r['revision'] == REV for r in after_pinmap), 'Pinmap revision mismatch')
for path in [H/'interfaces'/('pinmap_'+REV+'.csv'), HERE/'pinmap_P5R7.csv']:
    check(readcsv(path) == after_pinmap, 'Versioned pinmap mismatch: '+str(path))
before_electrical = json.loads((snap/'electrical_interfaces.json').read_text())
check(no_revision(before_electrical['pinmap']) == no_revision(electrical['pinmap']), 'Inline pin assignments changed')

old_harness = readcsv(H/'interfaces/harness_V1.2-H0.5-P5R6.csv')
new_harness = readcsv(H/'interfaces'/('harness_'+REV+'.csv'))
for r in old_harness:
    r['revision'] = REV
    for key in ['from_', 'to']:
        endpoint = json.loads(r[key])
        endpoint['board'] = endpoint['board'].replace('MORI_motion_P5R6','MORI_motion_P5R7').replace('MORI_rear_P5R6','MORI_rear_P5R7')
        r[key] = json.dumps(endpoint, ensure_ascii=False)
check(old_harness == new_harness, 'Numbered harness functions changed')
native_endpoints = 0
external_endpoints = []
for row in electrical['harness']:
    for side in ['from_', 'to']:
        ep = row[side]
        if ep['board'] not in boards:
            external_endpoints.append({'harness_id':row['harness_id'], 'endpoint':ep})
            continue
        key = (ep['board'], ep['connector'], str(ep['pin']))
        found = padmap.get(key, [])
        check(bool(found), 'Harness pad missing: '+str(key))
        if found:
            check(all(p.GetNetname().lstrip('/') == ep['signal'].lstrip('/') for f,p in found), 'Harness signal mismatch: '+str(key))
            native_endpoints += 1

ports = readcsv(HERE/'connector_pinmap_P5R7.csv')
for row in ports:
    key = (row['board'], row['reference'], row['pin'])
    found = padmap.get(key, [])
    check(bool(found), 'Port missing: '+str(key))
    if found:
        check(all(p.GetNetname() == row['net'] for f,p in found), 'Port net mismatch: '+str(key))
        expected = json.loads(row['xy_mm'])
        check(any(list(xy(p.GetPosition())) == expected for f,p in found), 'Port coordinates mismatch: '+str(key))
        check(all(('B' if f.IsFlipped() else 'F') == row['component_side'] for f,p in found), 'Port side mismatch: '+str(key))
j3 = sorted([r for r in ports if r['board']=='MORI_rear_P5R7' and r['reference']=='J3'], key=lambda r:json.loads(r['xy_mm'])[0])
check([r['pin'] for r in j3] == ['4','3','2','1'], 'Rear J3 top-view order mismatch')
check(handoff['weact_assembly']['component_side'] == 'UP', 'Core orientation mismatch')
check(handoff['weact_assembly']['core_STEP_to_robot_translation_z_mm'] is None, 'Unverified core Z was frozen')

initial = json.loads((HERE/'source_manifest_initial.json').read_text())
own = {'contracts/components.json','contracts/electrical_interfaces.json','hardware/pinmap.csv'}
external = {'AGENTS.md','config/geometry.json'}
source_rows = []
for row in initial:
    now = sha(ROOT/row['path'])
    same = now == row['sha256']
    category = 'UNCHANGED' if same else ('INTENTIONAL_HARDWARE_CONTRACT_UPDATE' if row['path'] in own else 'CONCURRENT_EXTERNAL_CHANGE' if row['path'] in external else 'UNEXPECTED_CHANGE')
    check(category != 'UNEXPECTED_CHANGE', 'Unexpected protected source change: '+row['path'])
    source_rows.append(dict(row, current_sha256=now, classification=category))
integrity = {'generated_utc':datetime.now(timezone.utc).isoformat(), 'scope':'Initial protected source manifest; does not claim the entire workspace is unchanged', 'mechanical_files_written_by_this_task':False, 'files':source_rows}
dump(HERE/'source_integrity_final.json', integrity)

report = {'status':'FAIL' if errors else 'PASS', 'generated_utc':datetime.now(timezone.utc).isoformat(), 'revision':REV,
    'errors':errors, 'native_projects':list(boards), 'native_input_hashes_checked':len(handoff['source_manifest']),
    'pinmap_rows':len(after_pinmap), 'numbered_harness_rows':len(new_harness), 'native_harness_endpoints_checked':native_endpoints,
    'external_harness_endpoints_not_qualified_by_native_CAD':external_endpoints, 'connector_pin_rows_checked':len(ports),
    'functions_unchanged_except_version_labels':True if not errors else None,
    'protected_source_count':len(initial), 'protected_source_integrity':'source_integrity_final.json',
    'contract_sha256':{name:sha(ROOT/name) for name in own}, 'physical_tests':'NOT_TESTED','full_mechanical_fit':'BLOCKED'}
dump(HERE/'publication_audit.json', report)
print(json.dumps({key:report[key] for key in ['status','errors','native_input_hashes_checked','pinmap_rows','numbered_harness_rows','native_harness_endpoints_checked','connector_pin_rows_checked']}, ensure_ascii=False))
if errors:
    raise SystemExit(1)

"""Verify this independent evidence package and write its final manifest."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import csv
import json
import re
import sys

B=Path(__file__).resolve().parent
def load(p): return json.loads((B/p).read_text())
def h(p): return sha256(p.read_bytes()).hexdigest()
def save(p,d): (B/p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
for p in B.rglob('*.json'):
    json.loads(p.read_text())
for p in B.glob('*.csv'):
    rows=list(csv.reader(p.open(newline='')))
    assert rows and all(len(r)==len(rows[0]) for r in rows),p
readme=(B/'README.md').read_text()
missing=[]
for link in re.findall(r'\]\(([^\n)]+)\)',readme):
    if link.startswith(('http://','https://','#')): continue
    if link=='results/validation.json': continue
    if not (B/link).exists(): missing.append(link)
assert not missing,missing
for r in load('receipt.json')['files']:
    assert h(B/r['snapshot'])==r['sha256'],r['snapshot']
retrievals=load('retrievals.json')
for r in retrievals:
    if r['retrieval_status']=='PASS':
        assert h(B/r['file'])==r['sha256'],r['file']
    if 'document_obtained' in r and r['retrieval_status']=='PASS':
        page=(B/r['file']).read_text()
        if r.get('page_kind') not in ('PRODUCT_INDEX_FALLBACK','OTHER_HTML_NO_DOCUMENT'):
            assert 'メール添付' in page or 'email attachment' in page,r['file']
        assert r['document_obtained'] is False
assert load('results/preservation.json')['status']=='PASS'
d=load('handoff.json')
assert d['formal_source']['contact']=='SPH-002T-P0.5S'
assert d['received_candidate']['body_contact']=='SPH-004T-P0.5S'
assert d['received_candidate']['formally_selected'] is False
assert d['formal_changes'] is False and d['messages_to_other_threads'] is False
assert d['bare_contact_envelope']['exact_finished_width_max_mm'] is None
assert d['full_combination_approval']=='BLOCKED'
v=load('visual_review.json')
assert len(v['viewed'])==12
assert all((B/p).is_file() for p in v['viewed'])

old=load('inputs/hardware_A8_evidence.json')
old_ph=next(r['sha256'] for r in old['source_retrievals'] if r['file']=='JST_PH_20261003.pdf')
old_sh=next(r['sha256'] for r in old['source_retrievals'] if r['file']=='JST_SH_20261003.pdf')
save('results/source_comparison.json',{
    'PH_catalogue_equal_to_hardware_A8':h(B/'sources/JST_PH.pdf')==old_ph,
    'SH_catalogue_equal_to_hardware_A8':h(B/'sources/JST_SH.pdf')==old_sh,
    'old_PH_sha256':old_ph,'current_PH_sha256':h(B/'sources/JST_PH.pdf'),
    'old_SH_sha256':old_sh,'current_SH_sha256':h(B/'sources/JST_SH.pdf'),
    'meaning':'Byte comparison only; no inference about latest approved process revision.'})
save('results/validation.json',{
    'status':'PASS','verified_utc':datetime.now(timezone.utc).isoformat(),
    'python':sys.version,'json_parse':'PASS','csv_shape':'PASS','README_local_links':'PASS',
    'swift_version_observed':'swift-driver 1.168.6; Apple Swift 6.4 (swiftlang-6.4.0.34.1 clang-2100.3.34.1); arm64-apple-macosx27.0.0',
    'validation_repair':'Initial English-only gate assertion failed on Japanese landing pages. Inspected actual text, accepted either language, and separately classified manual GET product-index fallbacks; no source PDF or engineering limit was changed.',
    'source_snapshot_integrity':'PASS','detailed_document_gate_not_bypassed':True,
    'formal_and_mechanical_preservation':load('results/preservation.json'),
    'commands':[
      '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python hardware/v1_2/cam_ph_terminal_reconciliation_20261006/prepare.py',
      'swift hardware/v1_2/cam_ph_terminal_reconciliation_20261006/render_sources.swift /Users/dean/Documents/MORI/hardware/v1_2/cam_ph_terminal_reconciliation_20261006',
      '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python hardware/v1_2/cam_ph_terminal_reconciliation_20261006/review.py',
      '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python hardware/v1_2/cam_ph_terminal_reconciliation_20261006/validate.py'],
    'no_native_ERC_DRC_run':'No circuit or board modification in this task',
    'finished_harness_release':'BLOCKED'})
files={str(p.relative_to(B)):h(p) for p in sorted(B.rglob('*')) if p.is_file() and p.name!='delivery_manifest.json'}
save('delivery_manifest.json',{'revision':'CAM-PH-RECON-R1','file_count':len(files),'hash_algorithm':'SHA-256','files':files})
print(json.dumps({'package':'PASS','files':len(files),'protected_unchanged':load('results/preservation.json')['checked_files'],'manufacturing':'BLOCKED'},ensure_ascii=False))

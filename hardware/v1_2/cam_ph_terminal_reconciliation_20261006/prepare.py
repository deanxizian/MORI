"""Read-only receipt and public-source archive; writes only this independent package."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import urllib.request

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
def digest(p):
    return sha256(p.read_bytes()).hexdigest()
def save(name, obj):
    p = BASE / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')
def now():
    return datetime.now(timezone.utc).isoformat()

if (BASE / 'receipt.json').exists():
    raise SystemExit('Receipt already exists; preserve dated snapshots.')

snapshots = {
    'AGENTS.md': 'AGENTS.md',
    'formal_mechanical_P5R7.json': 'hardware/v1_2/handoff/mechanical_P5R7.json',
    'hardware_A8_README.md': 'hardware/v1_2/head_harness_A8_20261003/README.md',
    'hardware_A8_evidence.json': 'hardware/v1_2/head_harness_A8_20261003/evidence.json',
    'hardware_process_comparison_README.md': 'hardware/v1_2/harness_process_comparison_20261003/README.md',
    'hardware_process_comparison.json': 'hardware/v1_2/harness_process_comparison_20261003/comparison.json',
    'hardware_process_reference_values.json': 'hardware/v1_2/harness_process_reference_20261003/reference_values.json',
    'CAM_PH_TERMINAL_HANDOFF.md': 'mechanical/studies/prearrival_finish/head_harness_M1_49/remaining_routes/CAM_PH_TERMINAL_HANDOFF.md',
    'PH_terminal_gate_review.json': 'mechanical/studies/prearrival_finish/head_harness_M1_49/remaining_routes/cam_restraints/PH_terminal_gate/review.json',
    'head_interface_pinmap_revA.csv': 'hardware/v1_2/head_harness_evidence_20261003/head_interface_pinmap_revA.csv',
}
copy_sources = {
    'JST_SPH004_crimp_2001.pdf': 'hardware/v1_2/harness_process_reference_20261003/sources/JST_SPH004_crimp.pdf',
    'JST_tooling_SPH-004T-P0.5S_20261003.json': 'hardware/v1_2/harness_process_comparison_20261003/sources/JST_tooling_SPH-004T-P0.5S.json',
    'JST_tooling_SSH-003T-P0.2-H_20261003.json': 'hardware/v1_2/harness_process_comparison_20261003/sources/JST_tooling_SSH-003T-P0.2-H.json',
    'tooling_lookup_sources_20261003.json': 'hardware/v1_2/harness_process_comparison_20261003/sources/tooling_lookup_sources.json',
    'crimp_guide_sources_20261003.json': 'hardware/v1_2/harness_process_reference_20261003/sources/crimp_guide_sources.json',
}
receipt = []
for folder, items in [('inputs', snapshots), ('sources', copy_sources)]:
    (BASE / folder).mkdir(parents=True, exist_ok=True)
    for name, rel in items.items():
        src = ROOT / rel
        dst = BASE / folder / name
        dst.write_bytes(src.read_bytes())
        receipt.append({'source': rel, 'snapshot': str(dst.relative_to(BASE)),
                        'sha256': digest(src), 'bytes': src.stat().st_size})
save('receipt.json', {'captured_utc': now(), 'files': receipt})

old = json.loads((ROOT / 'hardware/v1_2/harness_feasibility_20261006/inputs/protected_baseline.json').read_text())
extra = list(snapshots.values()) + list(copy_sources.values()) + [
    'config/geometry.json', 'contracts/mechanical_interfaces.json',
    'mechanical/mori_v1_2.blend', 'mechanical/reports/build_manifest.json',
]
paths = sorted(set(old['files']) | set(extra))
save('protected_baseline.json', {'captured_utc': now(),
    'files': {p: digest(ROOT / p) for p in paths},
    'prior_manifest_mismatches': [p for p, h in old['files'].items() if digest(ROOT / p) != h]})

urls = {
    'JST_PH.pdf': 'https://www.jst-mfg.com/product/pdf/eng/ePH.pdf',
    'JST_SH.pdf': 'https://www.jst-mfg.com/product/pdf/eng/eSH.pdf',
    'JST_crimp_precautions.pdf': 'https://www.jst-mfg.com/precaution/eP-Crimp.pdf',
    'JST_handling_precautions.pdf': 'https://www.jst-mfg.com/precaution/eP-Handling.pdf',
    'Alpha_2841_7.html': 'https://www.alphawire.com/products/wire/hook-up-wire/premium/2841_7',
    'JST_PH_series.html': 'https://www.jst-mfg.com/product/index.php?lang=2&series=199',
    'JST_SPH004_drawing_gate.html': 'https://www.jst-mfg.com/product/index.php?doc=4&filename=SPH-004T-P0.5S.pdf&series=199&type=10',
    'JST_SPH002_drawing_gate.html': 'https://www.jst-mfg.com/product/index.php?doc=4&filename=SPH-002T-P0.5S.pdf&series=199&type=10',
    'JST_PHR4_drawing_gate.html': 'https://www.jst-mfg.com/product/index.php?doc=4&filename=PHR-4.pdf&series=199&type=10',
    'JST_PH_manual_gate.html': 'https://www.jst-mfg.com/product/index.php?doc=11&filename=CHM-1-105.pdf%7CCHM-1-2201.pdf&series=199&type=10',
    'JST_PH_manual_literal_href.html': 'https://www.jst-mfg.com/product/index.php?type=10&series=199&doc=11&filename=CHM-1-105.pdf|CHM-1-2201.pdf',
}
def fetch(item):
    name, url = item
    record = {'file': 'sources/' + name, 'url': url, 'accessed_utc': now()}
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=25) as r:
            data = r.read()
            record.update(http_status=r.status, final_url=r.url, content_type=r.headers.get('Content-Type'))
        if name.endswith('.pdf') and not data.startswith(b'%PDF'):
            raise ValueError('Expected PDF, rejected non-PDF response')
        (BASE / 'sources' / name).write_bytes(data)
        record.update(bytes=len(data), sha256=sha256(data).hexdigest(), retrieval_status='PASS')
        if '_gate.html' in name or name == 'JST_PH_manual_literal_href.html':
            html = data.decode('utf-8', 'replace')
            gate = 'メール添付' in html or 'email attachment' in html
            record.update(document_obtained=False,
                          page_kind='IDENTITY_EMAIL_GATE' if gate else 'OTHER_HTML_NO_DOCUMENT',
                          reason='No form submitted or personal data supplied; HTML landing page is not document content')
    except Exception as e:
        record.update(retrieval_status='BLOCKED', error=str(e))
    return record
with ThreadPoolExecutor(max_workers=5) as pool:
    results = list(pool.map(fetch, urls.items()))
save('retrievals.json', results)
print(json.dumps({'snapshots': len(receipt), 'protected': len(paths),
    'retrieved': [x['file'] for x in results if x['retrieval_status'] == 'PASS'],
    'failed': [x for x in results if x['retrieval_status'] != 'PASS']}, ensure_ascii=False))

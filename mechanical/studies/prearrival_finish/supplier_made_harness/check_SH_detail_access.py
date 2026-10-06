"""Record public JST SH document entries and their current access method.

GET requests only. No form submission, personal data, or manufacturer contact.
This checks document availability, not connector suitability or manufacturing fit.
"""
from pathlib import Path
from urllib.request import Request, urlopen
from datetime import datetime, timezone
import hashlib
import json
import platform

HERE = Path(__file__).resolve().parent
OUT = HERE / 'recheck_20261004'
ITEMS = [
    ('manual', 'CHM-1-2389.pdf | CHM-1-2146.pdf',
     'https://www.jst-mfg.com/product/index.php?doc=11&filename=CHM-1-2389.pdf%7CCHM-1-2146.pdf&series=231&type=10'),
    ('terminal_drawing', 'SSH-003T-P0.2-H.pdf',
     'https://www.jst-mfg.com/product/index.php?doc=4&filename=SSH-003T-P0.2-H.pdf&series=231&type=10'),
    ('housing_STEP', 'SHR-04V-S.zip',
     'https://www.jst-mfg.com/product/index.php?doc=2&filename=SHR-04V-S.zip&series=231&type=10'),
    ('housing_drawing', 'SHR-04V-S.pdf',
     'https://www.jst-mfg.com/product/index.php?doc=4&filename=SHR-04V-S.pdf&series=231&type=10'),
]

rows = []
for name, document, url in ITEMS:
    # The browser inherits the product page's language; a fresh HTTP session
    # needs the same public lang=2 setting explicitly.
    request_url = url + '&lang=2'
    with urlopen(Request(request_url, headers={'User-Agent': 'MORI-public-source-review/1.0'}), timeout=30) as response:
        body = response.read()
        content_type = response.headers.get('Content-Type', '')
        code = response.status
        final_url = response.url
    html = body.decode('utf-8', errors='replace')
    markers = {
        'license_agreement': 'License Agreement' in html,
        'email_attachment_method': 'email attachment method' in html,
        'email_field': 'E-Mail address' in html,
        'company_field': 'Company name' in html,
    }
    assert code == 200 and 'text/html' in content_type and all(markers.values()), (url, code, content_type, markers)
    target = OUT / f'JST_SH_{name}_request.html'
    target.write_bytes(body)
    rows.append(dict(document=document, url=url, request_url=request_url, final_url=final_url,
                     http_status=code, content_type=content_type,
                     saved_response=target.name, sha256=hashlib.sha256(body).hexdigest(),
                     access='EMAIL_REQUEST_FORM', markers=markers,
                     requested_document_obtained=False))

record = dict(
    status='PASS',
    scope='Verification of public document-entry access only; PDF/STEP contents were not obtained.',
    checked_utc=datetime.now(timezone.utc).isoformat(),
    index_url='https://www.jst-mfg.com/product/index.php?lang=2&series=231',
    method='Read-only HTTP GET of four links observed on the official SH product page.',
    submitted_personal_data=False, submitted_form=False, contacted_supplier=False,
    exact_CAM_mating_part_number='BLOCKED', terminal_insertion_geometry='BLOCKED',
    manufacturing_release='BLOCKED', main_model_changed=False,
    script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    python=platform.python_version(),
    command='/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/supplier_made_harness/check_SH_detail_access.py',
    documents=rows,
)
(OUT / 'JST_SH_detail_access.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'status': 'PASS', 'document_entries': len(rows), 'files_obtained': 0, 'method': 'EMAIL_REQUEST_FORM'}))

"""Read-only source collection for the A8 harness addendum; never changes CAD."""
from pathlib import Path
import concurrent.futures, datetime, hashlib, json, shutil, urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / 'sources'
OUT.mkdir(exist_ok=True)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
inputs = [
    ('mechanical/studies/prearrival_finish/supplier_made_harness/DECISION.md', 'DECISION_received.md'),
    ('mechanical/studies/prearrival_finish/supplier_made_harness/sources/JST_GAM-050.pdf', 'JST_GAM-050_received.pdf'),
    ('mechanical/studies/prearrival_finish/supplier_made_harness/JST_GAM-050.png', 'JST_GAM-050_received.png'),
    ('mechanical/studies/prearrival_finish/supplier_made_harness/retrievals_addendum.json', 'mechanical_retrievals_received.json'),
]
received = []
for rel, name in inputs:
    src, dst = ROOT / rel, OUT / name
    if dst.exists():
        assert sha(dst) == sha(src), f'Refuse to overwrite changed receipt: {dst}'
    else:
        shutil.copy2(src, dst)
    received.append(dict(source=rel, snapshot=str(dst.relative_to(ROOT)), sha256=sha(src)))
(HERE / 'received_sources.json').write_text(json.dumps(received, ensure_ascii=False, indent=2)+'\n')

urls = [
    ('JST_PH_20261003.pdf', 'https://www.jst-mfg.com/product/pdf/eng/ePH.pdf'),
    ('JST_SH_20261003.pdf', 'https://www.jst-mfg.com/product/pdf/eng/eSH.pdf'),
    ('GAM-050_retrieved.pdf', 'https://gam-gec.com/wp-content/uploads/2018/10/GAM-050.pdf'),
    ('Alpha_2842_19.html', 'https://www.alphawire.com/products/wire/hook-up-wire/premium/2842_19'),
    ('Alpha_2841_7.html', 'https://www.alphawire.com/products/wire/hook-up-wire/premium/2841_7'),
    ('Hitachi_UL_PVC.pdf', 'https://hitachi.co.in/pdf/resources/high-function-materials-and-components/advanced-materials-and-components/ul-pvc.pdf'),
]
def fetch(item):
    name, url = item
    row = dict(file=name, url=url, accessed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    try:
        request = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(request, timeout=25) as response:
            data=response.read()
            row.update(http_status=response.status, final_url=response.url, content_type=response.headers.get('Content-Type'))
        p=OUT/name
        if p.exists() and p.read_bytes()!=data:
            raise RuntimeError('Refuse to overwrite different source bytes')
        p.write_bytes(data)
        row.update(status='PASS',bytes=len(data),sha256=sha(p))
    except Exception as error:
        row.update(status='BLOCKED',error=str(error))
    return row
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
    results=list(pool.map(fetch,urls))
(HERE/'retrievals.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
print(json.dumps([dict(file=r['file'],status=r['status'],sha256=r.get('sha256'),error=r.get('error'))for r in results],indent=2))

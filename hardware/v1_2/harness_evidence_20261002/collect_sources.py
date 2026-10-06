"""Collect public manufacturer evidence; never submit a form or change CAD."""
from pathlib import Path
import concurrent.futures
import datetime
import hashlib
import json
import shutil
import urllib.request

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
DEST = ROOT / 'sources'
DEST.mkdir(exist_ok=True)
URLS = {
    'jst_PH.pdf': 'https://www.jst-mfg.com/product/pdf/eng/ePH.pdf',
    'jst_tooling.pdf': 'https://www.jst.fr/doc/jst/family/pdf/eTOOL-5A.pdf',
    'jst_WC240.html': 'https://jst.co.uk/productSeries.php?cat=71&pid=10689',
    'jst_FAQ.html': 'https://www.jst.com/resources/faq/',
    'feetech_SCS0009_A0.pdf': 'https://www.feetechrc.com/Data/feetechrc/upload/file/20220915/6379883463905538176347522.pdf',
    'feetech_SCS0009_product.html': 'https://www.feetechrc.com/6v-23kg-serial-bus-steering-gear_65522.html',
    'waveshare_LCD35079.html': 'https://www.waveshare.com/product/1.85inch-touch-lcd-module.htm',
    'alpha_6711.html': 'https://www.alphawire.com/products/wire/ecogen/ecowire/6711',
    'alpha_6712.html': 'https://www.alphawire.com/products/wire/ecogen/ecowire/6712',
    'lcsc_SPH002_C111515.html': 'https://www.lcsc.com/product-detail/Housing-Contact_JST-SPH-002T-P0-5S_C111515.html',
}

def fetch(item):
    name, url = item
    r = {'name': name, 'source_url': url, 'accessed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(request, timeout=30) as response:
            content = response.read()
            r.update(final_url=response.url, http_status=response.status, content_type=response.headers.get('Content-Type'))
        (DEST / name).write_bytes(content)
        r.update(status='PASS', bytes=len(content), sha256=hashlib.sha256(content).hexdigest(), scope='retrieval only; facts require content inspection')
    except Exception as exc:
        r.update(status='BLOCKED', error=str(exc))
    return r

if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(fetch, URLS.items()))
    local = PROJECT / 'hardware/v1_2/sources/S288_manual.pdf'
    shutil.copyfile(local, DEST / 'unitree_S288_manual.pdf')
    results.append({'name': 'unitree_S288_manual.pdf', 'source_url': 'https://www.unitree.com/images/无刷数字舵机J288S288使用手册.pdf', 'copied_from': str(local), 'original_access_record': 'hardware/v1_2/sources/S288_manual.pdf.json', 'sha256': hashlib.sha256(local.read_bytes()).hexdigest(), 'status': 'PASS', 'scope': 'local source copy; not a fresh network retrieval'})
    (ROOT / 'sources_manifest.json').write_text(json.dumps(results, indent=2, ensure_ascii=False)+'\n')
    for r in results:
        print(r['name'], r['status'], r.get('bytes'), r.get('error', ''))

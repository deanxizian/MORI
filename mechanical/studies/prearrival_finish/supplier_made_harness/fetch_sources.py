"""Fetch publicly linked supplier files; retain redirects and content hashes."""
from pathlib import Path
from urllib.request import Request, urlopen
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json

ROOT = Path(__file__).resolve().parent
SOURCES = {
    'robotopian_scs0009.html': 'https://robotopian.com/products/feetech-scs0009-servo-motor',
    'SCS009-20230110-S.stp': 'https://robotopian.com/cdn/shop/files/SCS009-20230110-S.stp?v=3345111436623940966',
    'SCS0009_A0_mirror.pdf': 'https://robotopian.com/cdn/shop/files/SC-0090-C001Serial_Communication_Specification.pdf?v=8050184137930430276',
    'JST_PH_product.html': 'https://www.jst-mfg.com/product/index.php?lang=2&series=199',
    'PHR-8_IGES_download_form.html': 'https://www.jst-mfg.com/product/index.php?type=10&series=199&doc=1&filename=PHR-8.zip',
    'PHR-8_3DPDF_download_form.html': 'https://www.jst-mfg.com/product/index.php?type=10&series=199&doc=3&filename=PHR-8.pdf',
    'S8B-PH-K-S_IGES_download_form.html': 'https://www.jst-mfg.com/product/index.php?type=10&series=199&doc=1&filename=S8B-PH-K-S.zip',
    'S8B-PH-K-S_3DPDF_download_form.html': 'https://www.jst-mfg.com/product/index.php?type=10&series=199&doc=3&filename=S8B-PH-K-S.pdf',
    'T81H_quickref_response.bin': 'https://banebots.com/t81-hub-6mm-shaft/docs/T81H-QuickRef.pdf',
    'Waveshare_CAM_resources.html': 'https://docs.waveshare.com/ESP32-S3-CAM-OVxxxx/Resources-And-Documents',
}

def fetch(item):
    name, url = item
    row = {'file': 'sources/' + name, 'url': url, 'retrieved_utc': datetime.now(timezone.utc).isoformat()}
    try:
        with urlopen(Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=35) as r:
            data = r.read()
            row.update(status=r.status, final_url=r.url, content_type=r.headers.get('Content-Type'), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        (ROOT / row['file']).write_bytes(data)
    except Exception as exc:
        row['error'] = str(exc)
    return row

if __name__ == '__main__':
    (ROOT / 'sources').mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(fetch, SOURCES.items()))
    (ROOT / 'retrievals.json').write_text(json.dumps(rows, indent=2, ensure_ascii=False) + '\n')
    for row in rows:
        print(row['file'], row.get('status'), row.get('content_type'), row.get('bytes'), row.get('error', ''))

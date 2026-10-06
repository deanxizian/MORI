"""Download identified primary sources; retain URL/date/hash and failures."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib, json, urllib.request

ROOT = Path(__file__).resolve().parent
SOURCES = {
    'vishay_ac': 'https://www.vishay.com/docs/28730/ac_ac-at_ac-ni.pdf',
    'jst_ph': 'https://www.jst-mfg.com/product/pdf/eng/ePH.pdf',
    'jst_xh': 'https://www.jst-mfg.com/product/pdf/eng/eXH.pdf',
    'jst_handling': 'https://www.jst-mfg.com/product/pdf/eng/handling_e.pdf',
    'mini_fuse': 'https://www.littelfuse.com/assetdocs/littelfuse-datasheet-297-mini32v?assetguid=42c9dd21-a88e-4328-8e67-2f832444faf1',
    'fuse_holders': 'https://www.littelfuse.com/assetdocs/fuse-holder-brochure2022?assetguid=b04f3712-6b2d-4c40-a36a-e051935607f2',
    'cam_v11': 'https://files.waveshare.com/wiki/ESP32-S3-CAM-OVxxxx/ESP32-S3-CAM-OVxxxx_Rev1.1.pdf',
    'lcd_resources': 'https://docs.waveshare.com/1.85inch_Touch_LCD_Module/Resources-And-Documents',
    'alpha_5852': 'https://www.alphawire.com/en/products/wire/hook-up-wire/premium/5852',
    'pw140': 'https://www.pwchip.com/en/article/511.html',
    'idec_xa': 'https://us.idec.com/idec-us/en/USD/medias/IDEC-XA-Unibody-Datasheet.pdf?context=bWFzdGVyfGRvY3VtZW50c3wyMzgwMjd8YXBwbGljYXRpb24vcGRmfGRvY3VtZW50cy9oMTIvaDU3LzkxNjkzMDAwOTUwMDYucGRmfGQxMWM5NjlhOTVlYzliZWZiOGNlOGFkYmZhOTk4MWY1NjY2MmEyOTA2ZjljNjc3MDhkYWIxOTQ0ZDNhMmI4ZTU',
}

def fetch(item):
    name, url = item
    row = {'id': name, 'url': url, 'access_date': '2026-10-02'}
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=25) as response:
            data = response.read()
            row['final_url'] = response.url
        suffix = '.pdf' if data[:4] == b'%PDF' else '.html'
        path = ROOT / 'sources' / (name + suffix)
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(data)
        row.update(path=str(path.relative_to(ROOT)), sha256=hashlib.sha256(data).hexdigest(), bytes=len(data), status='PASS')
    except Exception as error:
        row.update(status='BLOCKED', error=str(error))
    return row

if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(fetch, SOURCES.items()))
    (ROOT / 'source_downloads.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n')
    for row in rows:
        print(row['id'], row['status'], row.get('bytes', row.get('error')))

"""Retrieve public manufacturer crimp guidance without submitting any forms."""
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import hashlib
import json

HERE=Path(__file__).resolve().parent
OUT=HERE/'sources'
OUT.mkdir(exist_ok=True)
SOURCES={
    'JST_SPH004_crimp.pdf':'https://www.jst-india.com/downloads/series/SPH-004-P0.5S.pdf',
    'JST_SSH003_crimp.pdf':'https://www.jst-india.com/downloads/series/SSH-003-02_SSHL-003-02_2.pdf',
    'JST_PH_series.html':'https://www.jst-india.com/productSeries.php?pid=2944',
    'JST_SHD_series.html':'https://www.jst-india.com/productSeries.php?pid=183',
    'JST_official_global_contact.html':'https://www.jst.com/zh/contact/global-contact/',
}
manifest=HERE/'crimp_guide_sources.json'
old=json.loads(manifest.read_text()) if manifest.exists() else {}
rows=old.get('sources',{})
failures=old.get('failed_requests',{})
for name,url in SOURCES.items():
    path=OUT/name
    if name in rows and path.exists():
        assert hashlib.sha256(path.read_bytes()).hexdigest()==rows[name]['sha256']
        if name.endswith('.html'):
            raw=path.read_bytes()
            rows[name]['content_review']='BLOCKED' if b'Fatal error' in raw else 'PASS'
            if b'Fatal error' in raw:rows[name]['note']='Server error page, not usable product data.'
        else:
            assert path.read_bytes().startswith(b'%PDF-')
            rows[name]['content_review']='PASS'
        continue
    if name in failures:continue
    request=Request(url,headers={'User-Agent':'Mozilla/5.0'})
    try:
        with urlopen(request,timeout=30) as response:
            raw=response.read()
            if name.endswith('.pdf'):assert raw.startswith(b'%PDF-'),(url,response.headers.get('content-type'))
            path.write_bytes(raw)
            rows[name]={'url':url,'final_url':response.url,'http_status':response.status,
                        'content_type':response.headers.get('content-type'),
                        'retrieved_utc':datetime.now(timezone.utc).isoformat(),
                        'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
                        'content_review':'BLOCKED' if b'Fatal error' in raw else 'PASS'}
        print(name,len(raw),flush=True)
    except (HTTPError,URLError,TimeoutError) as error:
        failures[name]={'url':url,'status':'BLOCKED','error':str(error),
                        'checked_utc':datetime.now(timezone.utc).isoformat()}
        print(name,'BLOCKED',str(error),flush=True)
manifest.write_text(json.dumps({'status':'PASS' if len(rows)==len(SOURCES) and not failures and
    all(r.get('content_review')=='PASS' for r in rows.values()) else 'BLOCKED',
    'scope':'Per-file public retrieval; both PDF guides obtained, supplementary page failures retained; no process approval',
    'sources':rows,'failed_requests':failures},ensure_ascii=False,indent=2)+'\n')

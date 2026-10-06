#!/usr/bin/env python3
"""Read public supplier pages and save dated procurement evidence (no cart/order)."""
import concurrent.futures, hashlib, json, re, sys, urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / 'procurement/evidence'

class Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.skip=0; self.parts=[]; self.links=[]; self.a=None
    def handle_starttag(self, tag, attrs):
        if tag in ('script','style'): self.skip+=1
        if tag=='a': self.a=[dict(attrs).get('href',''),'']
    def handle_endtag(self, tag):
        if tag in ('script','style'): self.skip=max(0,self.skip-1)
        if tag=='a' and self.a:
            self.links.append({'text':self.a[1].strip(),'href':self.a[0]}); self.a=None
    def handle_data(self, data):
        if not self.skip and data.strip(): self.parts.append(data.strip())
        if self.a: self.a[1]+=data

def capture(pair):
    key,url=pair; now=datetime.now(timezone.utc).isoformat()
    record={'id':key,'requested_url':url,'accessed_utc':now,'method':'public HTTP GET; no login/order/contact'}
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(req,timeout=25) as response:
            raw=response.read(); charset=response.headers.get_content_charset() or 'utf-8'
            record.update(http_status=response.status,final_url=response.url)
        s=raw.decode(charset,errors='replace'); p=Text(); p.feed(s)
        txt='\n'.join(p.parts)
        (OUT/(key+'.html')).write_bytes(raw)
        (OUT/(key+'.txt')).write_text(txt,encoding='utf8')
        record.update(sha256=hashlib.sha256(raw).hexdigest(),links=p.links,
            price_tokens=re.findall(r'[￥¥]\s*[0-9.]+',txt)[:8],
            stock_context=[txt[max(0,m.start()-15):m.start()+90] for m in re.finditer('库存|现货',txt)][:5])
    except Exception as exc: record['error']=str(exc)
    (OUT/(key+'.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    return {k:v for k,v in record.items() if k not in ('links',)}

if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    pairs=[arg.split('=',1) for arg in sys.argv[1:]]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        for result in pool.map(capture,pairs): print(json.dumps(result,ensure_ascii=False))

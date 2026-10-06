"""Check candidate source chain, protected main files and served review links."""
from pathlib import Path
import hashlib,json,sys
from urllib.request import urlopen
from urllib.parse import urljoin,urlparse,unquote
from html.parser import HTMLParser
from datetime import datetime,timezone
SCRIPT=Path(__file__).resolve();OUT=SCRIPT.parent;PROJECT=OUT.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
j=read(OUT/'publication.json');v=read(OUT/'verification.json');c=read(OUT/'construction.json')
assert j['status']==v['status']=='PASS' and j['visual_reviewed'] and not j['main_applied']
assert j['script_sha256']==sha(OUT/'publish_review.py')
assert all(sha(OUT/n)==h for n,h in j['source_files'].items())
assert all(sha(OUT/n)==h for n,h in j['outputs'].items())
assert all(sha(PROJECT/n)==h for n,h in j['protected_sources'].items())
assert v['unchanged_source_objects']==208 and v['changed_source_objects']==['Display_Frame']
assert v['topology']['connected_solid_components']==1 and v['saved_shell_gap_mm']>.3
assert all(r['status']=='PASS' and not r['failures'] for r in v['paths'])
assert v['continuous_shell_frame_path']['status']=='PASS' and not v['continuous_shell_frame_path']['unresolved']
assert read(OUT.parent/'work_status.json')['camera_top_clearance_candidate']['candidate_sha256']==j['source_files']['candidate.blend']
class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):
        for k,val in attrs:
            if k in ['href','src'] and val:self.links.append(val)
parser=Links();parser.feed((OUT/'index.html').read_text());checked=[]
base='http://127.0.0.1:58201/'+str((OUT/'index.html').relative_to(PROJECT))
for rel in ['index.html']+parser.links:
    u=urlparse(rel)
    if u.scheme or u.netloc or not u.path:continue
    local=(OUT/unquote(u.path)).resolve();assert local.is_file()
    with urlopen(urljoin(base,rel),timeout=15) as res:
        assert res.status==200;digest=hashlib.sha256(res.read()).hexdigest()
    assert digest==sha(local)
    checked.append(dict(target=rel,http_status=200,served_bytes_match=True))
files={str(p.relative_to(PROJECT)):sha(p) for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='delivery.json'}
report=dict(status='PASS',verified_utc=datetime.now(timezone.utc).isoformat(),python=sys.version,script_sha256=sha(SCRIPT),
    protected_sources=j['protected_sources'],files=files,links=checked,main_applied=False,pending_user_adoption=True,manufacturing_release=False)
(OUT/'delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(status='PASS',files=len(files),http_links=len(checked),main_unchanged=True)))

"""Validate this review's source receipts and locally served files."""
from pathlib import Path
from datetime import datetime,timezone
from html.parser import HTMLParser
from urllib.parse import urljoin,urlparse,unquote
from urllib.request import urlopen
import hashlib,json,platform
SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;P=A8.parent;ROOT=A8.parents[3]
BASE=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock/install_order'
OUT=BASE/'review';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text())
pub=read(OUT/'publication.json')
assert pub['status']=='PASS' and pub['script_sha256']==sha(A8/'publish_CAM_first_order_review.py')
for p,h in pub['source_files'].items():assert sha(ROOT/p)==h,p
for p,h in pub['protected_sources'].items():assert sha(ROOT/p)==h,p
for p,h in pub['outputs'].items():assert sha(OUT/p)==h,p
assert not pub['main_applied'] and not pub['manufacturing_release'] and pub['full_harness']=='BLOCKED'
state=read(P/'work_status.json');row=state['CAM_first_body_order']
assert row['status']=='BLOCKED' and row['finite_body_positions']==408 and row['later_bare_plug_paths']==6
assert row['attached_deferred_harnesses']=='NOT_TESTED'
assert next(r for r in state['remaining'] if r['id']=='harness')['evidence']==row['review']
assert next(r for r in state['remaining'] if r['id']=='head_front_contact')['evidence']=='camera_top_clearance/index.html'
supplier=read(A8/'supplier_source_update/verification.json')
assert supplier['CAM_first_publication_sha256']==sha(OUT/'publication.json')
assert supplier['script_sha256']==sha(A8/'publish_supplier_source_update.py')
h02dir=BASE/'H02_preinstalled';h02=read(h02dir/'publication.json')
assert h02['script_sha256']==sha(A8/'publish_H02_preinstalled_route.py')
assert pub['H02_preinstalled_publication_sha256']==supplier['H02_preinstalled_publication_sha256']==sha(h02dir/'publication.json')
assert h02['H02_open_deck_positions']==201 and h02['H02_body_positions']==408 and h02['H02_head_positions']==130
assert row['latest_order_variant']['remaining_later_harnesses']==['H01','H04']
assert state['A8_harness_research']['CAM_later_harness_conductors']==10
for p,h in h02['source_files'].items():assert sha(ROOT/p)==h,p
for p,h in h02['outputs'].items():assert sha(h02dir/p)==h,p
assert h02['full_harness']=='BLOCKED' and not h02['main_applied']
class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):
        self.links.extend(v for k,v in attrs if k in ['src','href'] and v)
files={OUT/'index.html',OUT/'publication.json',OUT/'plots.json',h02dir/'publication.json'}
files.update(h02dir/p for p in h02['outputs'])
for directory in [OUT,h02dir]:
    parser=Links();parser.feed((directory/'index.html').read_text())
    for link in parser.links:
        u=urlparse(link)
        if u.netloc:
            if u.netloc=='127.0.0.1:58201':files.add(ROOT/unquote(u.path.lstrip('/')))
        elif not u.scheme and u.path:files.add((directory/unquote(u.path)).resolve())
http=[]
for p in sorted(files):
    assert p.is_file(),p
    url='http://127.0.0.1:58201/'+str(p.relative_to(ROOT))
    with urlopen(url,timeout=10) as response:
        data=response.read();assert response.status==200
    assert hashlib.sha256(data).hexdigest()==sha(p)
    http.append(dict(file=str(p.relative_to(ROOT)),url=url,status=200,sha256=sha(p)))
report=dict(status='PASS',scope='Review publication, source preservation and HTTP content only',
    script_sha256=sha(SCRIPT),publication_sha256=sha(OUT/'publication.json'),protected_sources=pub['protected_sources'],
    python_version=platform.python_version(),blender_version='5.2.2 LTS d13f752e3b9c',
    generated_utc=datetime.now(timezone.utc).isoformat(),http=http,local_visual_review='PASS',
    full_harness='BLOCKED',main_applied=False,manufacturing_release=False,
    H02_publication_sha256=sha(h02dir/'publication.json'),H02_candidate='PASS',remaining_later_conductors=10)
(OUT/'delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(status='PASS',http_files=len(http),main_unchanged=True,full_harness='BLOCKED')))

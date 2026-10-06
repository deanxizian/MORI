"""Verify source provenance, failure scope and usable local review links."""
from pathlib import Path
from datetime import datetime,timezone
from html.parser import HTMLParser
from urllib.parse import urlparse,unquote
from urllib.request import urlopen
import json,hashlib,platform

SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;ROOT=A8.parents[3]
STOCK=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock'
OUT=STOCK/'bridge_tail_order_review'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pub=read(OUT/'publication.json');diag=read(STOCK/'bridge_then_shell_over_wires/diagnosis.json')
assert pub['status']=='PASS' and pub['whole_harness']=='BLOCKED'
assert pub['original_bridge_order']==pub['bearing_deferred_order']=='BLOCKED'
assert pub['substituted_prints']==[] and not pub['main_applied'] and not pub['manufacturing_release']
assert pub['script_sha256']==sha(A8/'publish_bridge_tail_order_review.py')
assert diag['bare_bridge_candidate_centre_probe']['centre_inside']
assert diag['bare_bridge_candidate_centre_probe']['solid_fraction']>.99
assert abs(diag['terminal_hits'][0]['volume_mm3']-2.7179324375684715)<1e-6
for group in ['source_files','protected_sources']:
    for p,h in pub[group].items():assert sha(ROOT/p)==h,p
for p,h in pub['outputs'].items():assert sha(OUT/p)==h,p
state=read(A8.parent/'work_status.json')
assert state['native_bridge_tail_order']['publication_sha256']==sha(OUT/'publication.json')
assert state['native_bridge_tail_order']['status']=='BLOCKED'
item=next(r for r in state['remaining'] if r['id']=='harness')
assert item['status']=='BLOCKED'
assert item['latest_native_bridge_order_evidence'].endswith('/bridge_tail_order_review/index.html')
assert state['CAM_PH_guided_wire_entry']['continuous']=='PASS'
overview=read(A8/'supplier_source_update/verification.json')
assert overview['script_sha256']==sha(A8/'publish_supplier_source_update.py')
assert overview['native_bridge_order_publication_sha256']==sha(OUT/'publication.json')
assert overview['native_bridge_tail_order']=='BLOCKED' and overview['PH_guided_full_wire_continuous']=='PASS'
assert overview['whole_harness']=='BLOCKED'

class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):self.links.extend(v for k,v in attrs if k in ['href','src'] and v)

parser=Links();parser.feed((OUT/'index.html').read_text())
files={OUT/n for n in ['index.html','README.md','sections.png','publication.json']}
files.update([A8/'supplier_source_update/index.html',A8/'supplier_source_update/README.md',A8/'supplier_source_update/verification.json'])
for link in parser.links:
    u=urlparse(link)
    if not u.scheme and not u.netloc and u.path:files.add((OUT/unquote(u.path)).resolve())
http=[]
for p in sorted(files):
    assert p.is_file(),p
    rel=str(p.relative_to(ROOT))
    with urlopen('http://127.0.0.1:58201/'+rel,timeout=20) as response:
        assert response.status==200;data=response.read()
    assert hashlib.sha256(data).hexdigest()==sha(p),p
    http.append(dict(path=rel,status=200,sha256=sha(p)))
report=dict(status='PASS',scope='File provenance, scope boundaries and served review links only',
    generated_utc=datetime.now(timezone.utc).isoformat(),script_sha256=sha(SCRIPT),
    publication_sha256=sha(OUT/'publication.json'),protected_sources=pub['protected_sources'],
    visual_review=dict(status='PASS',file='sections.png',method='Assistant viewed final source-solid sections after spacing correction'),
    http=http,versions=dict(python=platform.python_version(),blender='5.2.2 LTS d13f752e3b9c'),
    candidate_assembly='BLOCKED',whole_harness='BLOCKED',main_applied=False,manufacturing_release=False)
(OUT/'delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(status='PASS',http_files=len(http),candidate_assembly='BLOCKED',main_unchanged=True)))

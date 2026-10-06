"""Check new review provenance, remaining-work status and served file identity."""
from pathlib import Path
from datetime import datetime,timezone
from html.parser import HTMLParser
from urllib.request import urlopen
from urllib.parse import urlparse,unquote
import json,hashlib,platform

SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;ROOT=A8.parents[3]
STOCK=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock'
OUT=STOCK/'PH_guided_wire_entry';read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pub=read(OUT/'publication.json');full=read(OUT/'full_wire_continuous.json');v=read(OUT/'verification.json')
assert pub['status']==full['status']==v['status']=='PASS'
assert pub['script_sha256']==sha(A8/'publish_PH_guided_wire_review.py')
assert full['script_sha256']==sha(A8/'verify_PH_guided_full_wire_continuous.py')
assert full['source_verification_sha256']==sha(OUT/'verification.json')
assert len(full['intervals'])==174 and all(r['status']=='PASS' for r in full['intervals'])
assert len(full['terminal_pair_intervals'])==54 and len(full['terminal_motion'])==4
assert all(r['status']=='PASS' for r in full['terminal_pair_intervals']+full['terminal_motion'])
assert v['wire_finite_positions']==171 and v['continuous_sweeps']==875
assert v['maximum_remaining_intersection_mm3']==0.
assert full['static_union_is_validation_superset_not_additional_wire']
assert full['minimum_radius_bound_mm']>=9. and full['subsequent_neck_threading']=='NOT_TESTED'
assert pub['full_harness']==full['complete_attached_assembly']=='BLOCKED'
assert not pub['main_applied'] and not pub['manufacturing_release'] and not pub['supplier_cut_lengths']
for group in ['source_files','protected_sources']:
    for p,h in pub[group].items():assert sha(ROOT/p)==h,p
for p,h in pub['outputs'].items():assert sha(OUT/p)==h,p
state=read(A8.parent/'work_status.json')
assert state['CAM_PH_guided_wire_entry']['publication_sha256']==sha(OUT/'publication.json')
assert state['CAM_PH_guided_wire_entry']['whole_harness']=='BLOCKED'
item=next(r for r in state['remaining'] if r['id']=='harness')
assert item['status']=='BLOCKED' and item['latest_PH_attached_evidence'].endswith('/PH_guided_wire_entry/index.html')
overview=read(A8/'supplier_source_update/verification.json')
assert overview['script_sha256']==sha(A8/'publish_supplier_source_update.py')
assert overview['PH_guided_wire_publication_sha256']==sha(OUT/'publication.json')
assert overview['PH_guided_full_wire_continuous']=='PASS' and overview['whole_harness']=='BLOCKED'
class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):self.links.extend(v for k,v in attrs if k in ['href','src'] and v)
parser=Links();parser.feed((OUT/'index.html').read_text())
files={OUT/n for n in ['index.html','README.md','route.png','plot.json','screen.json','verification.json','full_wire_continuous.json','publication.json']}
files.update([A8/'supplier_source_update/index.html',A8/'supplier_source_update/README.md',A8/'supplier_source_update/verification.json'])
for link in parser.links:
    url=urlparse(link)
    if not url.scheme and not url.netloc and url.path:files.add((OUT/unquote(url.path)).resolve())
http=[]
for p in sorted(files):
    assert p.is_file(),p
    rel=str(p.relative_to(ROOT))
    with urlopen('http://127.0.0.1:58201/'+rel,timeout=20) as response:
        assert response.status==200;data=response.read()
    assert hashlib.sha256(data).hexdigest()==sha(p),p
    http.append(dict(path=rel,status=200,sha256=sha(p)))
report=dict(status='PASS',scope='File, source, scope and local HTTP delivery checks, not physical assembly',
    generated_utc=datetime.now(timezone.utc).isoformat(),script_sha256=sha(SCRIPT),
    publication_sha256=sha(OUT/'publication.json'),protected_sources=pub['protected_sources'],
    visual_review=dict(status='PASS',method='Assistant viewed the final source-based route PNG after layout adjustment',file='route.png'),
    http=http,versions=dict(python=platform.python_version(),blender='5.2.2 LTS d13f752e3b9c'),
    full_wire_continuous_stage='PASS',whole_harness='BLOCKED',main_applied=False,manufacturing_release=False)
(OUT/'delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(status='PASS',http_files=len(http),wire_intervals=174,whole_harness='BLOCKED',main_unchanged=True)))

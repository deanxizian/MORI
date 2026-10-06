"""Validate current report scope, file provenance and served review links."""
from pathlib import Path
from datetime import datetime,timezone
from html.parser import HTMLParser
from urllib.parse import urlparse,unquote
from urllib.request import urlopen
import hashlib,json,platform

SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;ROOT=A8.parents[3]
ORDER=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock/install_order'
OUT=ORDER/'shell16_joint_feed'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
pub=read(OUT/'publication.json')
assert pub['status']=='PASS' and pub['script_sha256']==sha(A8/'publish_shell16_review.py')
assert pub['rigid_sample_records']==297 and pub['rigid_unique_poses']==294
assert pub['prefix_wire_status']=='PASS' and pub['prefix_wire_sample_records']==98
assert pub['complete_attached_assembly']=='BLOCKED' and pub['continuous_assembly']=='NOT_TESTED'
assert not pub['main_applied'] and not pub['manufacturing_release']
for key in ['source_files','protected_sources']:
    for name,h in pub[key].items():assert sha(ROOT/name)==h,name
for name,h in pub['outputs'].items():assert sha(OUT/name)==h,name
state=read(A8.parent/'work_status.json')
assert state['CAM_shell16_body_sequence']['publication_sha256']==sha(OUT/'publication.json')
assert state['CAM_shell16_body_sequence']['complete_attached_assembly']=='BLOCKED'
assert next(r for r in state['remaining'] if r['id']=='head_front_contact')['evidence']=='camera_top_clearance/index.html'
overview=read(A8/'supplier_source_update/verification.json')
assert overview['script_sha256']==sha(A8/'publish_supplier_source_update.py')
assert overview['shell16_publication_sha256']==sha(OUT/'publication.json')
assert overview['shell16_complete_assembly']=='BLOCKED'
assert overview['shell16_rigid_path']=='PASS'

class Links(HTMLParser):
    def __init__(self):super().__init__();self.items=[]
    def handle_starttag(self,tag,attrs):
        self.items.extend(v for k,v in attrs if k in ['src','href'] and v)

files={OUT/n for n in pub['outputs']}
files.update([OUT/'publication.json',OUT/'screen.json',OUT/'verification.json',A8/'supplier_source_update/verification.json'])
for folder in [OUT,A8/'supplier_source_update']:
    parser=Links();parser.feed((folder/'index.html').read_text())
    for item in parser.items:
        parsed=urlparse(item)
        if not parsed.scheme and not parsed.netloc and parsed.path:files.add((folder/unquote(parsed.path)).resolve())
http=[]
for p in sorted(files):
    assert p.is_file(),p
    relative=p.relative_to(ROOT)
    with urlopen('http://127.0.0.1:58201/'+str(relative),timeout=20) as reply:
        data=reply.read();assert reply.status==200
    assert hashlib.sha256(data).hexdigest()==sha(p),p
    http.append(dict(path=str(relative),http_status=200,sha256=sha(p)))
report=dict(status='PASS',scope='File identities, published scope and HTTP delivery only',
    generated_utc=datetime.now(timezone.utc).isoformat(),script_sha256=sha(SCRIPT),
    publication_sha256=sha(OUT/'publication.json'),protected_sources=pub['protected_sources'],
    python_version=platform.python_version(),blender_version='5.2.2 LTS d13f752e3b9c',
    visual_inspection=dict(status='PASS',method='Assistant viewed both generated PNGs',files=['sequence.png','prefix_views.png']),
    finite_rigid_samples=297,finite_wire_prefix_samples=98,complete_attached_assembly='BLOCKED',
    main_applied=False,manufacturing_release=False,http=http)
(OUT/'delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(status='PASS',http_files=len(http),rigid_records=297,wire_prefix_records=98,whole_assembly='BLOCKED',main_unchanged=True)))

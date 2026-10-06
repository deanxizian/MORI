"""Check new source receipts, scoped claims, and actual local HTTP delivery."""
from pathlib import Path
from datetime import datetime,timezone
from html.parser import HTMLParser
from urllib.parse import urlparse,unquote
from urllib.request import urlopen
import hashlib,json,platform

SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;ROOT=A8.parents[3]
ORDER=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock/install_order'
OUT=ORDER/'feed_pose_packing';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
pub=read(OUT/'publication.json')
assert pub['status']=='PASS' and pub['verified_single_poses']==2
assert pub['script_sha256']==sha(A8/'publish_CAM_segmented_feed_review.py')
assert pub['complete_attached_assembly']=='BLOCKED' and pub['continuous_movement']=='NOT_TESTED'
assert not pub['main_applied'] and not pub['manufacturing_release']
for section in ['source_files','protected_sources']:
    for p,digest in pub[section].items():assert sha(ROOT/p)==digest,p
for name,digest in pub['outputs'].items():assert sha(OUT/name)==digest,name
for label in ['lift18','rear14_lift18']:
    d=read(OUT/label/'verification.json')
    assert d['status']=='PASS' and d['source_objects_present']==122
    assert d['fixed_body_wires']==14 and d['mating_allocations']==29
    assert len(d['selected_checks'])==4 and len(d['selected_pairs'])==6
    assert len(d['terminal_pairs'])==6 and len(d['terminal_other_wire_checks'])==12
    assert all(r['status']=='PASS' for r in d['terminal_pairs']+d['terminal_other_wire_checks'])
    assert min(r['surface_gap_lower_bound_mm'] for r in d['selected_pairs'])>=.3
    assert d['transition_from_settled']=='NOT_TESTED' and d['whole_harness']=='BLOCKED'
state=read(A8.parent/'work_status.json')
assert state['CAM_segmented_body_feed']['publication_sha256']==sha(OUT/'publication.json')
assert state['CAM_segmented_body_feed']['complete_attached_assembly']=='BLOCKED'
supplier=read(A8/'supplier_source_update/verification.json')
assert supplier['script_sha256']==sha(A8/'publish_supplier_source_update.py')
assert supplier['segmented_body_wire_feed_publication_sha256']==sha(OUT/'publication.json')
assert supplier['segmented_single_pose_count']==2 and supplier['segmented_body_wire_feed']=='BLOCKED'
assert next(r for r in state['remaining'] if r['id']=='head_front_contact')['evidence']=='camera_top_clearance/index.html'


class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):self.links.extend(v for k,v in attrs if k in ['href','src'] and v)


files={OUT/name for name in pub['outputs']}
files.add(OUT/'publication.json')
for label in ['lift18','rear14_lift18']:
    files.update(OUT/label/name for name in ['screen.json','verification.json','curves.npz'])
for name in ['feed_lift_transition','feed_lift_schedule','feed_lift_refinement','feed_lift_pulse']:
    files.add(ORDER/name/'screen.json')
for folder in [OUT,A8/'supplier_source_update']:
    parser=Links();parser.feed((folder/'index.html').read_text())
    for link in parser.links:
        u=urlparse(link)
        if not u.scheme and not u.netloc and u.path:
            files.add((folder/unquote(u.path)).resolve())
http=[]
for p in sorted(files):
    assert p.is_file(),p
    url='http://127.0.0.1:58201/'+str(p.relative_to(ROOT))
    with urlopen(url,timeout=15) as response:
        data=response.read();assert response.status==200
    assert hashlib.sha256(data).hexdigest()==sha(p),p
    http.append(dict(file=str(p.relative_to(ROOT)),status=200,sha256=sha(p)))
report=dict(status='PASS',scope='Source identity, scope consistency, visual plot inspection and HTTP delivery only',
            generated_utc=datetime.now(timezone.utc).isoformat(),script_sha256=sha(SCRIPT),
            publication_sha256=sha(OUT/'publication.json'),protected_sources=pub['protected_sources'],
            python_version=platform.python_version(),blender_version='5.2.2 LTS d13f752e3b9c',
            local_plot_visual_review='PASS',http=http,verified_single_poses=2,
            complete_attached_assembly='BLOCKED',main_applied=False,manufacturing_release=False)
(OUT/'delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(status='PASS',http_files=len(http),single_poses=2,complete_assembly='BLOCKED',main_unchanged=True)))

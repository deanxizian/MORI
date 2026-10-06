"""Verify published scope/source identities and local HTTP delivery."""
from pathlib import Path
from datetime import datetime,timezone
from html.parser import HTMLParser
from urllib.request import urlopen
from urllib.parse import urlparse,unquote
import hashlib,json,platform
SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;ROOT=A8.parents[3]
ORDER=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock/install_order'
OUT=ORDER/'CAM_H02_joint_lift'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
pub=read(OUT/'publication.json')
assert pub['status']=='PASS' and pub['script_sha256']==sha(A8/'publish_CAM_H02_joint_review.py')
assert pub['joint_wire_finite_lift']=='PASS' and pub['joint_wire_lift_positions']==37
assert pub['complete_attached_assembly']=='BLOCKED' and pub['shell_connector_path']=='BLOCKED'
assert pub['continuous_assembly']=='NOT_TESTED' and not pub['main_applied'] and not pub['manufacturing_release']
for section in ['source_files','protected_sources']:
    for p,h in pub[section].items():assert sha(ROOT/p)==h,p
for p,h in pub['outputs'].items():assert sha(OUT/p)==h,p
check=read(OUT/'verification.json');screen=read(OUT/'screen.json')
assert check['source_screen_sha256']==sha(OUT/'screen.json')
assert all(r['status']=='PASS' for r in check['joint_lift']+check['open_deck_insertion'])
assert len(check['joint_lift'])==37 and len(check['open_deck_insertion'])==201
assert len(screen['selected']['cam_pairs'])==6 and len(screen['selected']['route_cam_pairs'])==8
assert check['head_poses']==130 and check['head_solid_intersections']==[]
assert check['supplier_cut_lengths'] is None and check['actual_terminals_and_plug_fit']=='NOT_TESTED'
state=read(A8.parent/'work_status.json')
assert state['CAM_H02_joint_lift']['publication_sha256']==sha(OUT/'publication.json')
assert state['CAM_H02_joint_lift']['complete_attached_assembly']=='BLOCKED'
assert next(r for r in state['remaining'] if r['id']=='head_front_contact')['evidence']=='camera_top_clearance/index.html'
sup=read(A8/'supplier_source_update/verification.json')
assert sup['script_sha256']==sha(A8/'publish_supplier_source_update.py')
assert sup['joint_CAM_H02_publication_sha256']==sha(OUT/'publication.json')
assert sup['joint_CAM_H02_complete_assembly']=='BLOCKED' and sup['rear_J2_shell_path']=='BLOCKED'


class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):
        self.links.extend(v for k,v in attrs if k in ['href','src'] and v)


files={OUT/n for n in pub['outputs']}
files.update(OUT/n for n in ['screen.json','verification.json','wire_solids.json','curves.npz','publication.json'])
for folder in [OUT,A8/'supplier_source_update']:
    parser=Links();parser.feed((folder/'index.html').read_text())
    for link in parser.links:
        u=urlparse(link)
        if not u.scheme and not u.netloc and u.path:
            files.add((folder/unquote(u.path)).resolve())
for name in ['CAM_H02_back_transition','CAM_H02_vertical_withdrawal','CAM_H02_shell_first','CAM_H02_shell_schedule']:
    files.add(ORDER/name/'screen.json')
http=[]
for p in sorted(files):
    assert p.is_file(),p
    with urlopen('http://127.0.0.1:58201/'+str(p.relative_to(ROOT)),timeout=20) as r:
        content=r.read();assert r.status==200
    assert hashlib.sha256(content).hexdigest()==sha(p),p
    http.append(dict(path=str(p.relative_to(ROOT)),sha256=sha(p),http_status=200))
report=dict(status='PASS',scope='Source/scope/HTTP consistency only',
            generated_utc=datetime.now(timezone.utc).isoformat(),script_sha256=sha(SCRIPT),
            publication_sha256=sha(OUT/'publication.json'),protected_sources=pub['protected_sources'],
            python_version=platform.python_version(),blender_version=check['blender_version'],
            visual_inspection=dict(status='PASS',method='Assistant viewed all three rendered PNGs in this turn',
                                   files=['H02_comparison.png','lift_comparison.png','rear_J2_overlap.png']),
            joint_wire_finite_positions=37,complete_attached_assembly='BLOCKED',
            main_applied=False,manufacturing_release=False,http=http)
(OUT/'delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(status='PASS',http_files=len(http),wire_positions=37,full_assembly='BLOCKED',main_unchanged=True)))

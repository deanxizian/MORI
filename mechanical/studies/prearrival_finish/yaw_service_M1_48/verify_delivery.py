"""Audit final reports and links while proving the approved main is unchanged."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
from urllib.request import Request, urlopen
from datetime import datetime, timezone
import hashlib
import json

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
load = lambda p: json.loads(Path(p).read_text())
pub = load(HERE / 'publication.json')
for p, h in pub['native_sources'].items():
    assert sha(PROJECT / p) == h, p
for p, h in pub['files'].items():
    assert sha(HERE / p) == h, p
for p, record in pub['changed_presentation_files'].items():
    assert sha(PROJECT / p) == record['after'], p

for report, script in [
    ('refined_construction.json', 'refine_neck_channels.py'),
    ('refined_adaptive_all.json', 'replay_local_clearance.py'),
    ('curve_packing_refined.json', 'refine_curve_packing.py'),
    ('radius_evidence.json', 'check_radius_evidence.py'),
    ('section_checks.json', 'check_sections.py')]:
    d = load(HERE / report)
    assert d['status'] == 'PASS' and not d['main_applied'], report
    assert d['script_sha256'] == sha(HERE / script), report
motion = load(HERE / 'refined_adaptive_all.json')
packing = load(HERE / 'curve_packing_refined.json')
radius = load(HERE / 'radius_evidence.json')
sections = load(HERE / 'section_checks.json')
assert motion['head_poses'] == len(motion['poses']) == 130
assert all(r['status'] == 'PASS' and not r['hits'] for r in motion['poses'])
assert motion['native_parts'] == 209 and motion['mating_allocations'] == 29
assert motion['fixed_candidate_wires'] == 14 and not motion['excluded_for_diagnosis']
assert motion['curve_source_sha256'] == sha(HERE / 'internal_full_curves.npz')
assert motion['clearance_helper_sha256'] == sha(HERE / 'local_clearance.py')
assert {p['name'] for p in motion['substituted_prints']} == {'Yaw_Base', 'Pitch_Yoke'}
for p in motion['substituted_prints']:
    assert sha(PROJECT / p['source']) == p['source_sha256']
    assert abs(p['added_mm3']) < 1e-5 and len(p['components_mm3']) == 1
assert len(packing['mutual_checks']) == 780 and len(packing['nonlocal_self_checks']) == 520
assert all(r['status'] == 'PASS' for r in packing['mutual_checks'] + packing['nonlocal_self_checks'])
assert packing['minimum_pair_gap_lower_bound_mm'] >= packing['surface_gap_mm'] == .3
assert packing['source_curves_sha256'] == sha(HERE / 'internal_full_curves.npz')
assert packing['source_screen_sha256'] == sha(HERE / 'curve_packing.json')
assert radius['minimum_radius_lower_mm'] >= radius['required_radius_mm']
for p, h in radius['sources'].items():
    assert sha(PROJECT / p) == h, p
assert sections['sections_sha256'] == sha(HERE / 'sections.json')
assert all(p['components'] == 1 and p['non_two_face_edges'] == 0 and p['zero_area_faces'] == 0 for p in sections['topology'].values())
assert motion['retention'] == motion['full_assembly'] == 'NOT_TESTED'
assert motion['whole_harness'] == packing['whole_harness'] == radius['whole_harness'] == 'BLOCKED'
status = load(HERE.parent / 'work_status.json')
assert len([r for r in status['remaining'] if r['id'] != 'physical_validation']) == 5
assert status['revision'] == 'V1.2-M1.48' and not status['manufacturing_release']
assert not status['yaw_service_M1_48']['main_applied']

hardware = load(HERE.parent / 'camera_cam_adoption/approval.json')['protected_hardware']
for p, h in hardware.items():
    assert sha(PROJECT / p) == h, p
old = load(HERE.parent / 'camera_cam_adoption/delivery.json')
unchanged = []
for p, h in old['files'].items():
    if Path(p).suffix.lower() in ['.blend', '.mp4', '.stl']:
        assert sha(PROJECT / p) == h, p
        unchanged.append(p)
export = load(PROJECT / 'mechanical/reports/export_manifest.json')
assert export['exported_count'] == 21
for r in export['parts']:
    p = PROJECT / 'mechanical' / r['file']
    assert sha(p) == r['sha256'], p
    unchanged.append(str(p.relative_to(PROJECT)))
animation = load(PROJECT / 'mechanical/animation/manifest.json')
assert animation['animation_revision'] == 'V1.2-M1.48-A1'
assert animation['source_blend_sha256'] == motion['source_main_sha256']
video = PROJECT / 'mechanical/animation' / animation['video']['file']
assert sha(video) == animation['video']['sha256']
unchanged.append(str(video.relative_to(PROJECT)))

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.values = []
    def handle_starttag(self, tag, attrs):
        self.values.extend(value for key, value in attrs if key in ['href', 'src'] and value)

pages = [HERE / 'index.html'] + [PROJECT / p for p in pub['changed_presentation_files'] if p.endswith('.html')]
links = []
for page in pages:
    parser = Links()
    parser.feed(page.read_text())
    for link in parser.values:
        u = urlsplit(link)
        if u.scheme or not u.path:
            continue
        target = (page.parent / unquote(u.path)).resolve()
        if target == HERE / 'delivery.json':
            continue
        assert target.exists(), (page, link)
        links.append(dict(page=str(page.relative_to(PROJECT)), link=link))
http = []
for name in ['index.html', 'complete_route.png', 'upper_route.png', 'channel_sections.png', 'review.blend']:
    url = 'http://127.0.0.1:58201/' + str((HERE / name).relative_to(PROJECT))
    with urlopen(Request(url, method='HEAD'), timeout=15) as response:
        assert response.status == 200
        http.append(dict(url=url, status=response.status, content_length=response.headers.get('Content-Length')))
result = dict(status='PASS', scope='Study publication and preserved main/hardware; full harness incomplete',
              utc=datetime.now(timezone.utc).isoformat(), script_sha256=sha(__file__),
              publication_sha256=sha(HERE / 'publication.json'),
              local_links_checked=len(links), protected_hardware_files=len(hardware),
              unchanged_main_animation_STL=sorted(set(unchanged)), http=http,
              source_main_sha256=motion['source_main_sha256'], main_applied=False,
              whole_harness='BLOCKED', manufacturing_release=False)
(HERE / 'delivery.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print('YAW_SERVICE_DELIVERY', result['status'], 'links', len(links), 'hardware', len(hardware), flush=True)

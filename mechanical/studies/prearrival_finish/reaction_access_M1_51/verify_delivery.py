"""Read back M1.52 delivery, without upgrading inherited or physical evidence."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote, quote
from urllib.request import Request, urlopen
from concurrent.futures import ThreadPoolExecutor
import datetime, hashlib, json, sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
M = ROOT / 'mechanical'
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
source = sha(M / 'mori_v1_2.blend')
cfg = read(ROOT / 'config/geometry.json')
rev = cfg['revision']
assert rev == 'V1.2-M1.52'
prep = read(OUT / 'preparation.json')
snapshot = ROOT / prep['snapshot_root']
protected = {n: sha(ROOT / n) == h for n, h in prep['protected_hardware'].items()}
assert all(protected.values()), [n for n, ok in protected.items() if not ok]
assert sha(snapshot / 'mechanical/mori_v1_2.blend') == prep['files']['mechanical/mori_v1_2.blend']['sha256']

scope = read(M / 'reports/reaction_nut_alignment_validation.json')
access = read(OUT / 'access.json')
body = read(OUT / 'body_split_check.json')
validation = read(M / 'reports/validation.json')
consistency = read(M / 'reports/delivery_consistency.json')
engineering = read(OUT.parent / 'engineering_current.json')
exports = read(M / 'reports/export_manifest.json')
animation = read(M / 'animation/manifest.json')
av = read(M / 'animation/validation.json')
ad = read(M / 'animation/delivery.json')
work = read(OUT.parent / 'work_status.json')
electronic = read(M / 'reports/electronics_detail_manifest.json')
ev = read(M / 'reports/electronics_detail_validation.json')
plot = read(OUT / 'plot_receipt.json')
sections = read(OUT / 'sections.json')
pub = read(OUT / 'publication.json')
for report in [scope, access, body, consistency, engineering, av, ev, plot, pub]:
    assert report['status'] == 'PASS'
for report in [scope, access, body, validation, engineering, animation, ad, work, sections, pub]:
    assert report['source_blend_sha256'] == source
assert electronic['source_main_sha256'] == source and ev['source_main_hash_matches']
assert electronic['revision'] == rev and ev['maximum_coordinate_difference_mm'] == 0
assert validation['counts']['FAIL'] == 0
changed = sorted(cfg['reaction_nut_alignment']['nut_hosts'])
assert scope['scope']['changed_ids'] == changed
assert scope['scope']['unchanged_native_parts'] == 199
assert scope['scope']['printed_solids_unchanged']
assert all(row['corrected_overlap_mm3'] < 1e-6 for row in scope['scope']['rows'])
assert all(row['status'] == 'PASS' for row in access['lower_rows'])
assert access['upper_row']['status'] == 'BLOCKED'
assert access['full_reaction_preassembly'] == 'BLOCKED' and not access['C6_applied']
assert len(body['paths']) == 2 and all(r['status'] == 'PASS' and r['positions'] == 275 for r in body['paths'])
assert len(body['frame_tool_access']) == 4 and all(r['status'] == 'PASS' for r in body['frame_tool_access'])

old = read(snapshot / 'mechanical/reports/export_manifest.json')
assert exports['exported_count'] == 21
assert {p['id']: p['sha256'] for p in exports['parts']} == {p['id']: p['sha256'] for p in old['parts']}
assert all(p['status'] == 'PASS' and sha(M / p['file']) == p['sha256'] for p in exports['parts'])
bom = read(M / 'reports/bom.json')
prints = [r['id'] for r in bom if r['category'] == 'PRINTABLE' and r['group'] not in ['dock', 'coupon']]
build = read(M / 'reports/build_manifest.json')
assert len(prints) == 16 and len(build['actuators']) == 4
assert consistency['input_provenance_valid'] and consistency['all_render_hashes_match_final_model']
assert consistency['render_count'] == 62
assert animation['animation_revision'] == rev + '-A1' and animation['rendered_video']
native = set(read(OUT / 'inspection.json')['native_fingerprints'])
assert len(native) == 201
assert set(animation['part_stages']) == native | {'Eye_L', 'Eye_R'}
assert animation['actor_count'] == 203 and animation['stage_count'] == 22
assert animation['duration_seconds'] == 85.75
assert sha(M / 'animation/MORI_assembly.mp4') == animation['video']['sha256'] == av['video']['sha256']
assert sha(M / 'mori_assembly_animation.blend') == animation['animation_blend_sha256']
assert all(sha(M / n) == h for n, h in ad['files'].items())
assert sha(OUT / plot['image']) == plot['image_sha256']
assert sha(OUT / 'sections.json') == plot['sections_sha256']
assert sha(OUT / 'plot.py') == plot['script_sha256']
assert not work['manufacturing_release'] and work['status'] == 'BLOCKED'
assert source in (M / 'reports/组装与打印.md').read_text()
assert source in (OUT.parent / 'ENGINEERING.md').read_text()

# A current full rebuild/idempotence report is not claimed. The previous report
# remains explicitly historical; current build and strict mesh-delta checks own
# this two-object correction.
inherited_rebuild = snapshot / 'mechanical/reports/rebuild_check.json'
assert inherited_rebuild.exists()
commands = read(OUT / 'commands.json')
last = {r['stage']: r for r in commands}
expected = ['build', 'validate', 'body_paths', 'access', 'export', 'render', 'electronics',
            'electronics_check', 'engineering', 'structure_metadata', 'metal', 'consistency',
            'animation', 'catalog', 'review']
assert all(last[k]['returncode'] == 0 for k in expected), {k: last.get(k, {}).get('returncode') for k in expected}
assert all(sha(ROOT / r['log']) == r['log_sha256'] for r in commands)

pages = [M / 'index.html', M / 'animation/index.html', M / 'parts.html', M / 'manufacturing.html',
         OUT / 'index.html', OUT.parent / 'index.html']
class Page(HTMLParser):
    def __init__(self, value):
        super().__init__()
        self.links = []
        self.ids = set()
        self.feed(value)
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.links.extend(a[k] for k in ['src', 'href', 'poster'] if k in a)
        if 'id' in a: self.ids.add(a['id'])

assets = set(pages)
failures, external = [], []
fragments = 0
for p in pages:
    for raw in Page(p.read_text()).links:
        u = urlsplit(raw)
        if u.scheme and (u.scheme not in ['http', 'https'] or u.netloc != '127.0.0.1:58201'):
            external.append(raw)
            continue
        local = unquote(u.path)
        target = ((ROOT / local.lstrip('/') if local.startswith('/') else p.parent / local) if local else p).resolve()
        if target.is_dir(): target = target / 'index.html'
        if not target.exists():
            failures.append(dict(page=str(p.relative_to(ROOT)), href=raw, problem='missing file'))
            continue
        assets.add(target)
        if u.fragment and target.suffix == '.html':
            fragments += 1
            if unquote(u.fragment) not in Page(target.read_text()).ids:
                failures.append(dict(page=str(p.relative_to(ROOT)), href=raw, problem='missing fragment'))
def head(p):
    file = str(p.relative_to(ROOT))
    try:
        with urlopen(Request('http://127.0.0.1:58201/' + quote(file), method='HEAD'), timeout=15) as r:
            return dict(file=file, status=r.status)
    except Exception as e:
        return dict(file=file, error=str(e))
with ThreadPoolExecutor(max_workers=4) as pool:
    http = list(pool.map(head, sorted(assets)))
failures += [x for x in http if x.get('status') != 200]

# New MP4 byte ranges must actually match its bytes, not merely advertise Range.
video = M / 'animation/MORI_assembly.mp4'
size = video.stat().st_size
byte_ranges = []
with video.open('rb') as f:
    for start in [0, size // 2, size - 4096]:
        end = start + 4095
        req = Request('http://127.0.0.1:58201/mechanical/animation/MORI_assembly.mp4', headers={'Range': f'bytes={start}-{end}'})
        with urlopen(req, timeout=15) as r:
            actual, response_status, content_range = r.read(), r.status, r.headers.get('Content-Range')
        f.seek(start)
        exact = actual == f.read(4096)
        ok = response_status == 206 and exact and content_range == f'bytes {start}-{end}/{size}'
        byte_ranges.append(dict(start=start, end=end, status='PASS' if ok else 'FAIL', http_status=response_status,
                                content_range=content_range, bytes_exact=exact))
assert all(r['status'] == 'PASS' for r in byte_ranges)
web = dict(status='FAIL' if failures else 'PASS', pages=[str(p.relative_to(ROOT)) for p in pages], local_assets=len(assets),
           fragments_checked=fragments, http=http, failures=failures, video_byte_ranges=byte_ranges,
           external_links_not_rechecked=sorted(set(external)))
(OUT / 'web_check.json').write_text(json.dumps(web, ensure_ascii=False, indent=2) + '\n')
assert not failures, failures

evidence = [M / p for p in ['mori_v1_2.blend', 'mori_assembly_animation.blend', 'mori_electronics_detail.blend',
            'reports/build_manifest.json', 'reports/validation.json', 'reports/export_manifest.json',
            'reports/delivery_consistency.json', 'reports/electronics_detail_validation.json',
            'reports/reaction_nut_alignment_validation.json', 'reports/组装与打印.md',
            'animation/manifest.json', 'animation/validation.json', 'animation/delivery.json', 'animation/MORI_assembly.mp4']]
evidence += [OUT / p for p in ['preparation.json', 'commands.json', 'access.json', 'body_split_check.json', 'publication.json',
             'sections.json', 'plot_receipt.json', 'nut_alignment.png', 'web_check.json', 'verify_delivery.py']]
evidence += [OUT.parent / p for p in ['engineering_current.json', 'ENGINEERING.md', 'work_status.json']]
evidence += pages
stamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
report = dict(status='PASS', utc=stamp, revision=rev, source_blend_sha256=source,
              scope='Exact two-nut correction, current digital checks and delivery; no full reaction/harness or manufacturing qualification',
              protected_hardware_files=len(protected), protected_hardware_unchanged=True, robot_print_count=len(prints),
              exported_STL=21, unchanged_STL=21, unchanged_native_parts=199, changed_native_parts=changed,
              validation_counts=validation['counts'], fresh_check_count=len(validation['current_rerun_ids']),
              inherited_rebuild=dict(revision='V1.2-M1.51', path=str(inherited_rebuild.relative_to(ROOT)), sha256=sha(inherited_rebuild), rerun_this_revision=False),
              animation_revision=animation['animation_revision'], video_seconds=animation['duration_seconds'],
              local_web_status=web['status'], full_reaction_preassembly='BLOCKED', full_harness='BLOCKED',
              physical_fit='NOT_TESTED', manufacturing_release=False, command=[sys.executable, str(Path(__file__))],
              files={str(p.relative_to(ROOT)): sha(p) for p in evidence})
(OUT / 'delivery.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
audit = read(OUT.parent / 'goal_block_audit.json')
audit.update(main_revision=rev, source_blend_sha256=source, current_goal_turn_classification='progress',
             previous_progress='M1.52 corrected two trial-nut orientations, verified lower access, updated model/previews/animation; upper assembly remains open.',
             consecutive_impasse_turns=0, goal_status='active', completion_proven=False,
             next_action='Await explicit C6 structural decision and exact purchased-interface inputs; continue independent work within authorized scope.',
             last_revalidated_utc=stamp)
audit['live_state_checks'].update(main_matches_current_delivery=True, delivery_status='PASS',
                                 hardware_snapshot_cursor='7bd539b2-4981-4852-b2c7-b1b5beace384:1',
                                 hardware_thread_state='notLoaded', hardware_latest_turn_state='completed',
                                 hardware_result='Current wait snapshot returned notLoaded/completed, no new handed-off result; not a live idle assertion.',
                                 matching_active_blender_or_study_processes=None,
                                 process_query_scope='Delivery-stage processes were not enumerated by this verifier; no idle assertion.')
audit['remaining_requirements'][0]['dependency']='C6/restraint choices, final horn and complete wired endpoints. Lower trial lock access passed; upper clamp initial assembly remains unresolved.'
(OUT.parent / 'goal_block_audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n')
print('M1_52_DELIVERY_PASS', len(assets), 'local assets;', len(protected), 'hardware files preserved', flush=True)

"""Publish the document-only synchronization, preserving rendered assets."""
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
M = STUDY.parents[1]
P = M.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


commands = []
for script in ('publish_service_review.py', 'publish_status.py'):
    cmd = [sys.executable, str(STUDY / script)]
    start = datetime.now(timezone.utc).isoformat()
    result = subprocess.run(cmd, cwd=P, capture_output=True, text=True)
    log = HERE / (script.removesuffix('.py') + '.log')
    log.write_text(result.stdout + result.stderr)
    commands.append(dict(command=cmd, started_utc=start,
                         finished_utc=datetime.now(timezone.utc).isoformat(),
                         returncode=result.returncode, log=str(log.relative_to(P))))
    write(HERE / 'publication_commands.json', commands)
    print(script, result.returncode, flush=True)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)

sys.path.insert(0, str(M / 'scripts'))
import animation_page

section = animation_page.generate(M)
text = (M / 'index.html').read_text()
text, replaced = re.subn(r'<section id="animation">.*?</section>', section, text, flags=re.S)
assert replaced == 1
(M / 'index.html').write_text(text)

equivalence = read(HERE / 'source_equivalence.json')
current = sha(M / 'mori_v1_2.blend')
assert equivalence['status'] == 'PASS'
assert equivalence['current_source_blend_sha256'] == current
assert not equivalence['changed_objects'] and not equivalence['embedded_animation_source_differences']
assert sha(P / 'config/geometry.json') == sha(HERE / 'before/geometry.json')

delivery_path = M / 'animation/delivery.json'
delivery = read(delivery_path)
assert delivery['source_blend_sha256'] == current
unchanged_assets = ['mori_assembly_animation.blend', 'animation/MORI_assembly.mp4']
unchanged_assets += [p for p in delivery['files'] if re.fullmatch(r'animation/step_\d+\.png', p)]
assert all(sha(M / p) == delivery['files'][p] for p in unchanged_assets)
previous_files = delivery['files'].copy()
delivery['files'] = {p: sha(M / p) for p in previous_files}
delivery['metadata_refresh'] = dict(
    utc=datetime.now(timezone.utc).isoformat(),
    command=[sys.executable, str(Path(__file__).resolve())],
    scope='Page, manifest and check-record refresh only. Animation, video and chapter images were not rerendered.',
    changed_file_hashes=[p for p in previous_files if previous_files[p] != delivery['files'][p]],
    original_render_source_blend_sha256=delivery['original_render_source_blend_sha256'],
    geometry_equivalence='../studies/prearrival_finish/interface_sync/source_equivalence.json')
write(delivery_path, delivery)


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ('href', 'src', 'poster') and value:
                self.links.append(value)


pages = [M / 'index.html', M / 'manufacturing.html', M / 'parts.html',
         M / 'animation/index.html', STUDY / 'index.html',
         STUDY / 'reaction_assembly_review.html', STUDY / 'thin_candidate.html']
missing = []
checked = 0
for path in pages:
    parser = Links()
    parser.feed(path.read_text())
    for link in parser.links:
        parsed = urlsplit(link)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        target = (P / unquote(parsed.path).lstrip('/') if parsed.path.startswith('/')
                  else path.parent / unquote(parsed.path))
        checked += 1
        if not target.exists():
            missing.append(dict(page=str(path.relative_to(P)), target=link))

work = read(STUDY / 'work_status.json')
assert work['source_blend_sha256'] == current and not work['manufacturing_release']
assert len(work['remaining']) == 7
assert not read(STUDY / 'thin_candidate_check.json')['applied_to_main']
candidate = STUDY / 'thin_candidate_workspace/mechanical/mori_v1_2.blend'
candidate_hash = sha(candidate)
assert candidate_hash == '53d75e6d022a57f95ebd261084a4995f874e512b62e9f33edcc10fd6b2431d35'
assert read(M / 'reports/delivery_consistency.json')['status'] == 'PASS'
assert read(M / 'animation/validation.json')['status'] == 'PASS'
assert all(x['status'] == 'PASS' for x in read(M / 'reports/export_manifest.json')['parts'])
inputs = read(M / 'reports/build_manifest.json')['input_sha256']
assert all(sha(P / key) == value for key, value in inputs.items())
assert not missing, missing
write(HERE / 'publication_audit.json', dict(
    status='PASS', utc=datetime.now(timezone.utc).isoformat(),
    scope='Source equivalence, current build inputs, publication links and asset preservation only; not engineering qualification.',
    source_blend_sha256=current, candidate_blend_sha256=candidate_hash,
    candidate_applied=False, geometry_input_unchanged=True,
    complete_source_objects_compared=equivalence['complete_source_objects_compared'],
    animation_actor_count=equivalence['animation_actor_count'],
    preserved_render_assets=len(unchanged_assets), pages_checked=len(pages),
    local_links_checked=checked, missing_links=missing,
    remaining_groups_excluding_physical_validation=6,
    interface_contract_sha256=sha(P / 'contracts/mechanical_interfaces.json'),
    publication_commands='publication_commands.json',
    delivery_commands='delivery_commands.json', python_version=sys.version))
print('PUBLICATION_AUDIT_PASS', checked, 'local links', current, flush=True)

"""Publish a verified animation without regenerating unrelated project pages."""
import datetime
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from animation_page import generate

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'animation'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

manifest=json.loads((OUT/'manifest.json').read_text())
validation=json.loads((OUT/'validation.json').read_text())
assert manifest['rendered_video'] and validation['status']=='PASS'
assert digest(ROOT/'mori_v1_2.blend')==manifest['source_blend_sha256']
section=generate(ROOT)
assert section
page=ROOT/'index.html'
text=page.read_text()
text,count=re.subn(r'<section id="animation">.*?</section>',lambda _:section,text,flags=re.S)
assert count==1,count
page.write_text(text)

# Synchronize the review's old-animation notice only after video validation.
review=ROOT/'studies/prearrival_closure/publish.py'
review_python=Path('/Users/dean/.cache/codex-runtimes/mori-cad/bin/python')
review_command=[str(review_python),str(review)]
started=datetime.datetime.now(datetime.timezone.utc).isoformat()
if not manifest.get('p5r7_adopted'):
    with (review.parent/'publish.log').open('w') as log:
        subprocess.run(review_command,cwd=ROOT.parent,stdout=log,stderr=subprocess.STDOUT,check=True)
else:
    # The M1.43 review is historical; current P5R7 reports own its status banner.
    review_command=[]

owned=[ROOT/'mori_assembly_animation.blend',ROOT/'index.html',
       OUT/'MORI_assembly.mp4',OUT/'manifest.json',OUT/'validation.json',
       OUT/manifest['body_sequence_readback']['report'],OUT/'index.html',OUT/'README.md',
       OUT/'commands.json',OUT/('CHANGELOG_'+manifest['animation_revision'].removeprefix('V1.2-').replace('-','_')+'.md'),OUT/'head_retention_path_validation.json',ROOT/'scripts/assembly_animation.py',
       ROOT/'scripts/check_assembly_animation.py',ROOT/'scripts/animation_page.py',
       Path(__file__),ROOT/'scripts/run_animation.py']
owned.extend(sorted(OUT.glob('step_*.png')))
delivery=dict(animation_revision=manifest['animation_revision'],
    published_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    source_revision=manifest['revision'],source_unchanged=True,
    source_blend_sha256=manifest['source_blend_sha256'],
    video_status='PASS',manufacturing_release=False,p5r7_adopted=manifest.get('p5r7_adopted',False),
    body_sequence_readback=manifest['body_sequence_readback'],
    geometry_identity='All actor vertices and face connectivity equal source; declared exact mesh copies have presentation materials only.',
    publish_command=[sys.executable,str(Path(__file__))],
    review_publish=dict(command=review_command,started_utc=started,returncode=0),
    files={str(p.relative_to(ROOT)):digest(p) for p in owned})
(OUT/'delivery.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2)+'\n')
print('ANIMATION_PUBLISHED',manifest['animation_revision'],manifest['duration_seconds'],flush=True)

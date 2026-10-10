"""Record each current derivative command, with unchanged source verification."""
from pathlib import Path
import json,hashlib,subprocess,datetime
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PROJECT=ROOT.parent
blender='/Applications/Blender.app/Contents/MacOS/Blender'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
master=ROOT/'mori_v1_2.blend';digest=sha(master)
check=json.loads((ROOT/'reports/validation.json').read_text())
assert check['revision']=='V1.2-M1.54' and check['source_blend_sha256']==digest and not check['counts']['FAIL']
def cmd(file,script,*args):return [blender,'--background','--python-exit-code','1',str(file),'--python',str(script),*args]
steps=[('body_sequence',cmd(master,ROOT/'scripts/check_body_sequence_current.py')),
       ('electronics',cmd(master,ROOT/'scripts/export_electronics_detail.py')),
       ('electronics_check',cmd(ROOT/'mori_electronics_detail.blend',ROOT/'scripts/check_electronics_detail.py')),
       ('review_images',cmd(master,HERE/'render_current.py')),
       ('animation_build',cmd(master,ROOT/'scripts/assembly_animation.py','--','--width','1280','--samples','16','--render','stills')),
       ('animation_native',cmd(ROOT/'mori_assembly_animation.blend',ROOT/'scripts/check_assembly_animation.py','--','--native-only')),
       ('animation_video',cmd(ROOT/'mori_assembly_animation.blend',HERE/'render_video.py')),
       ('animation_check',cmd(ROOT/'mori_assembly_animation.blend',ROOT/'scripts/check_assembly_animation.py')),
       ('animation_cam_readback',cmd(ROOT/'mori_assembly_animation.blend',HERE/'check_animation_cam.py'))]
records=[]
for stage,command in steps:
    assert sha(master)==digest
    log=HERE/(stage+'.log');started=datetime.datetime.now(datetime.timezone.utc).isoformat();print('DELIVER',stage,flush=True)
    with log.open('w') as out:r=subprocess.run(command,cwd=PROJECT,stdout=out,stderr=subprocess.STDOUT)
    records.append(dict(stage=stage,command=command,started_utc=started,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),returncode=r.returncode,source_blend_sha256=digest,log=str(log.relative_to(ROOT)),log_sha256=sha(log)))
    (HERE/'commands.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
    if r.returncode:raise SystemExit(r.returncode)
    assert sha(master)==digest
print('CAM_RIGHT_DELIVERABLES_COMPLETE',flush=True)

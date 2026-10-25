"""Rebuild current model-review derivatives with sequential commands and logs.

--rebuild also regenerates the main model. Missing inputs are never skipped.
Default: model checks, STL and static views only. Generate animation/video only
with --with-animation after the user has reviewed the model and requested it.
"""
import argparse,datetime,hashlib,json,os,shutil,subprocess,sys
from pathlib import Path

project=Path(__file__).resolve().parents[2];root=project/'mechanical'
parser=argparse.ArgumentParser();parser.add_argument('--rebuild',action='store_true')
parser.add_argument('--with-animation',action='store_true',help='Explicitly update editable animation and video after user review')
parser.add_argument('--list-stages',action='store_true',help='Show planned stages without running commands')
args=parser.parse_args()
p=json.loads((project/'config/geometry.json').read_text())
assert p.get('off_shelf_modules',{}).get('enabled') and p['off_shelf_modules']['approved']
blender=os.environ.get('MORI_BLENDER') or shutil.which('blender') or '/Applications/Blender.app/Contents/MacOS/Blender'
master=root/'mori.blend';animation=root/'mori_assembly_animation.blend'
def command(script,source=master,extra=()):
    return [blender,'--background',str(source),'--python-exit-code','1','--python',str(root/'scripts'/script),*extra]
steps=[]
if args.rebuild:
    steps.append(('build',[blender,'--background','--python-exit-code','1','--python',str(root/'scripts/build.py')]))
elif not args.list_stages:
    build=json.loads((root/'reports/build_manifest.json').read_text())
    for name,digest in build['input_sha256'].items():
        assert hashlib.sha256((project/name).read_bytes()).hexdigest()==digest,'Changed input; run --rebuild: '+name
steps += [
    ('metadata',command('finalize_structure_metadata.py')),
    ('validate',command('validate.py')),
    *([('controls_clearances',command('check_ups_controls_clearances.py'))] if p.get('ups_rear_controls',{}).get('enabled') else []),
    ('body_paths',command('check_body_sequence_current.py')),
    ('export',command('export.py')),
    ('views',command('render_off_shelf_current.py')),
    ('detail',command('export_electronics_detail.py')),
    ('detail_check',command('check_electronics_detail.py',root/'mori_electronics_detail.blend')),
    ('usb_capacity',command('check_off_shelf_usb.py')),
]
if args.with_animation:
    steps += [
    ('animation_build',command('assembly_animation.py',extra=('--','--width','1280','--render','none'))),
    ('animation_native_check',command('check_assembly_animation.py',animation,('--','--native-only'))),
    ('animation_ups_path',command('check_off_shelf_animation.py',animation)),
    ('animation_stills',command('render_current_animation.py',animation,('--','--kind','stills'))),
    ('animation_video',command('render_current_animation.py',animation,('--','--kind','video'))),
    ('animation_video_check',command('check_assembly_animation.py',animation)),
    ('publish',[sys.executable,str(root/'scripts/off_shelf_delivery.py')]),
    ]
else:
    steps.append(('publish_model_review',[sys.executable,str(root/'scripts/off_shelf_delivery.py'),'--model-only']))
if args.list_stages:
    print('\n'.join(stage for stage,cmd in steps));raise SystemExit(0)
records=[];logdir=root/'reports/off_shelf_run';logdir.mkdir(exist_ok=True)
for stage,cmd in steps:
    print('OFF_SHELF',stage,flush=True)
    log=logdir/(stage+'.log');started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    with log.open('w') as handle:
        result=subprocess.run(cmd,cwd=project,stdout=handle,stderr=subprocess.STDOUT)
    records.append(dict(stage=stage,command=cmd,started_utc=started,
        finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),returncode=result.returncode,
        log=str(log.relative_to(project)),log_sha256=hashlib.sha256(log.read_bytes()).hexdigest()))
    (root/'reports/off_shelf_commands.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
    if result.returncode:raise SystemExit(result.returncode)
print('OFF_SHELF_COMPLETE',flush=True)

"""Refresh only deliveries affected by the proven document-only rebuild."""
from pathlib import Path
import subprocess,json,datetime,sys
HERE=Path(__file__).resolve().parent;M=HERE.parents[2];P=M.parent
B='/Applications/Blender.app/Contents/MacOS/Blender'
assert json.loads((HERE/'source_equivalence.json').read_text())['status']=='PASS'
steps=[
    ('structure_metadata',M/'mori_v1_2.blend',M/'scripts/finalize_structure_metadata.py'),
    ('electronics',M/'mori_v1_2.blend',M/'scripts/export_electronics_detail.py'),
    ('electronics_check',M/'mori_electronics_detail.blend',M/'scripts/check_electronics_detail.py'),
    ('consistency',M/'mori_v1_2.blend',M/'scripts/delivery_check.py'),
    ('animation_readback',M/'mori_assembly_animation.blend',M/'scripts/check_assembly_animation.py'),
    ('reaction_sections',M/'mori_v1_2.blend',HERE.parent/'reaction_service_sections.py'),
]
commands=[]
for stage,blend,script in steps:
    cmd=[B,'--background',str(blend),'--python-exit-code','1','--python',str(script)]
    started=datetime.datetime.now(datetime.timezone.utc).isoformat();log=HERE/(stage+'.log')
    print('START',stage,flush=True)
    with log.open('w') as stream:result=subprocess.run(cmd,cwd=P,stdout=stream,stderr=subprocess.STDOUT)
    commands.append(dict(stage=stage,command=cmd,started_utc=started,
        finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),returncode=result.returncode,
        log=str(log.relative_to(P))))
    (HERE/'delivery_commands.json').write_text(json.dumps(commands,ensure_ascii=False,indent=2)+'\n')
    print('DONE',stage,result.returncode,flush=True)
    if result.returncode:sys.exit(result.returncode)
print('INTERFACE_DELIVERY_READY',flush=True)

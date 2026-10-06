"""Final evidence index for the approved M1.44 change, not print release."""
from pathlib import Path
import json,hashlib,datetime
R=Path(__file__).resolve().parents[1];P=R.parent
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=sha(R/'mori_v1_2.blend')
q=read(P/'config/geometry.json')['head_axial_retention']
task_start=R/'revisions/V1.2-M1.43_before_head_retention_M1.44/hardware_hashes.json'
original=read(task_start)
changed=[p for p,h in original.items() if not (P/p).exists() or sha(P/p)!=h]
added=[str(p.relative_to(P)) for p in (P/'hardware').rglob('*') if p.is_file() and str(p.relative_to(P)) not in original]
assert not changed and not added,(changed,added)
for name in ['head_axial_retention_validation','head_retention_body_sequence','head_axial_retention_delivery']:
    d=read(R/'reports'/f'{name}.json');assert d['status']=='PASS' and d['source_blend_sha256']==source,name
assert read(R/'reports/rebuild_check.json')['status']=='PASS'
assert read(R/'reports/validation.json')['counts']['FAIL']==0
inputs=read(R/'reports/build_manifest.json')['input_sha256']
assert all(sha(P/p)==h for p,h in inputs.items())
ex=read(R/'reports/export_manifest.json')
failed=[x['id'] for x in ex['parts'] if x['status']!='PASS']
assert failed==['Head_Rear'],failed
assert all(x['status']=='PASS' for x in ex['parts'] if x['id'] in ['Yaw_Base','Pitch_Yoke','Yaw_Anti_Lift_Keeper'])
assert all(sha(R/x['file'])==x['sha256'] for x in ex['parts'])
am=read(R/'animation/manifest.json');av=read(R/'animation/validation.json')
assert am['source_blend_sha256']==source and am['rendered_video'] and av['status']=='PASS'
assert am['head_retention_readback']['status']=='PASS'
assert sha(R/'mori_assembly_animation.blend')==am['animation_blend_sha256']
assert sha(R/'animation/MORI_assembly.mp4')==am['video']['sha256']==av['video']['sha256']
for x in ['index.html','manufacturing.html','animation/index.html','reports/头身防脱_M1_44.md']:
    assert 'M1.44' in (R/x).read_text(),x
commands=[
 {'command':'python3 mechanical/scripts/run_retention_delivery.py','log':'reports/head_retention_delivery_commands.json'},
 {'command':'python3 mechanical/scripts/run_animation.py --defer-publish','log':'animation/commands.json'},
 {'command':'/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/mori_v1_2.blend --python-exit-code 1 --python mechanical/scripts/check_stl_exact_readback.py','log':'reports/stl_exact_readback_diagnostic.log'},
 {'command':'/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/mori_v1_2.blend --python-exit-code 1 --python mechanical/scripts/export.py','log':'reports/retention_export.log','note':'Rerun after fixing decimal vertex rounding in the reader.'},
 {'command':'/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/mori_v1_2.blend --python-exit-code 1 --python mechanical/scripts/delivery_check.py','log':'reports/retention_delivery_check.log'},
 {'command':'/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/mori_assembly_animation.blend --python-exit-code 1 --python mechanical/scripts/render_retention_access_frame.py','log':'reports/retention_access_frame.log'},
 {'command':'python3 mechanical/scripts/report_head_retention.py','log':'reports/retention_publish.log'},
 {'command':'python3 mechanical/scripts/publish_animation_update.py','log':'reports/retention_animation_publish.log'},
 {'command':'python3 mechanical/scripts/finalize_head_retention_delivery.py','log':'reports/retention_final_audit.log'}]
files=[P/'config/geometry.json',P/'contracts/mechanical_interfaces.json',P/'AGENTS.md',R/'mori_v1_2.blend',R/'mori_assembly_animation.blend',R/'mori_electronics_detail.blend']
files += [R/x for x in ['index.html','manufacturing.html','parts.html','README.md','animation/index.html','animation/MORI_assembly.mp4','animation/manifest.json','animation/validation.json','animation/delivery.json','animation/head_retention_path_validation.json','reports/头身防脱_M1_44.md','reports/delivery_consistency.json','reports/export_manifest.json','reports/head_axial_retention_validation.json','reports/head_retention_body_sequence.json','reports/head_axial_retention_delivery.json','reports/interface_printability.json','reports/validation.json','reports/rebuild_check.json']]
files += [R/x['file'] for x in ex['parts']]
files += list((R/'studies/head_axial_retention/adopted').glob('*.png'))
files += [R/'scripts'/n for n in ['head_axial_retention.py','validate_head_retention.py','assembly_animation.py','check_assembly_animation.py','export.py','delivery_check.py','report_head_retention.py','finalize_head_retention_delivery.py']]
out=dict(revision='V1.2-M1.44',status='PASS',scope='Approved A5 integration and current delivery consistency only',checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_blend_sha256=source,hardware_unchanged={'status':'PASS','checked_files':len(original),'changes':changed,'additions':added},stl={'passed':ex['exported_count'],'total':ex['candidate_count'],'failed_ids':failed,'unresolved':'Head_Rear has six coincident nonmanifold STL edges already present before M1.44; source shape not changed in this task.'},animation_revision=am['animation_revision'],manufacturing_release=False,commands=commands,files={str(f.relative_to(P)):sha(f) for f in files})
(R/'reports/head_retention_delivery_files.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('HEAD_RETENTION_FINAL_AUDIT',out['status'],len(files),'files; hardware unchanged',len(original),flush=True)

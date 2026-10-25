"""Reconcile the M1.34 changed STL scope and retained historical animation."""
from pathlib import Path
import json,hashlib

P=Path(__file__).resolve().parents[2];R=P/'mechanical'
g=json.loads((P/'config/geometry.json').read_text());s=g['head_mount_simplification']
snapshot=P/Path(s['baseline_blend']).parents[1]
old=json.loads((snapshot/'mechanical/reports/export_manifest.json').read_text())
current=json.loads((R/'reports/export_manifest.json').read_text())
oldparts={r['id']:r for r in old['parts']};newparts={r['id']:r for r in current['parts']}
changed=sorted(n for n,r in newparts.items() if r['sha256']!=oldparts.get(n,{}).get('sha256'))
read=lambda name:json.loads((R/'reports'/name).read_text())
v=read('validation.json');local=read('simple_head_mounts_validation.json');motion=read('head_motion.json')
snap=json.loads((snapshot/'snapshot_manifest.json').read_text());hardware=hashlib.sha256((P/'contracts/components.json').read_bytes()).hexdigest()
a=json.loads((R/'animation/manifest.json').read_text())
animation_same=hashlib.sha256((R/'mori_assembly_animation.blend').read_bytes()).hexdigest()==a['animation_blend_sha256']
actual_failure_ids=sorted(r['id'] for r in v['checks'] if r['status']=='FAIL')
errors=[]
if changed!=sorted(s['changed_existing_ids']) or set(oldparts)!=set(newparts):errors.append('Unexpected STL changes/part count')
if local['status']!='PASS':errors.append('Local geometry failed')
if actual_failure_ids!=['static_rigid_solids','waveshare_nominal_fit']:errors.append('Unexpected full-model failures')
if motion['failures']:errors.append('Head motion failed')
for file in ['rebuild_check.json','delivery_consistency.json','electronics_detail_validation.json','waveshare_bench_validation.json']:
    if read(file)['status']!='PASS':errors.append(file)
if any(r['status']!='PASS' or r['blender_reimport']['status']!='PASS' for r in current['parts']):errors.append('Export/reimport failure')
if not animation_same:errors.append('Historical animation changed unexpectedly')
result={'revision':g['revision'],'status':'PASS' if not errors else 'FAIL','scope':'Current local change and artifact consistency, not global hardware qualification',
        'errors':errors,'changed_stl_ids':changed,'unchanged_stl_count':len(newparts)-len(changed),'stl_count':len(newparts),
        'actual_geometry_checks':v['counts'],'unchanged_known_failure_ids':actual_failure_ids,
        'local_geometry_status':local['status'],'head_motion_samples':motion['poses'],'head_motion_failures':len(motion['failures']),
        'animation_revision':a['revision'],'animation_retained_unchanged':animation_same,'animation_current':False,
        'hardware_contract_unchanged_since_start':hardware==snap['hardware_contract_sha256'],
        'print_strength':'NOT_TESTED','manufacturing_release':False,'camera_fit':'Prior M1.33 camera conflicts remain; local adaptation still needs user confirmation'}
(R/'reports/simple_head_mounts_delivery.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
if errors:raise SystemExit(1)

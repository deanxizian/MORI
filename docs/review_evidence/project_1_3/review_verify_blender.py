# -*- coding: utf-8 -*-
import sys,json,hashlib,shutil,runpy,importlib
from pathlib import Path
project=Path('/Users/dean/Documents/MORI')
sys.path.insert(0,str(project/'mechanical/scripts'))
import common
from common import bpy
out=project/'.state/pr15_review'
checks={}
source=project/'mechanical/mori_v1_2.blend'
original_root=common.ROOT
scratch=out/'mechanical'
scratch.mkdir(exist_ok=True)
shutil.copytree(original_root/'reports',scratch/'reports',dirs_exist_ok=True)
(scratch/'mori_v1_2.blend').symlink_to(source)
protected=[source,original_root/'mori_assembly_animation.blend',original_root/'animation/MORI_assembly.mp4']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={str(p.relative_to(project)):sha(p) for p in protected}
common.ROOT=scratch
for i in range(2):
    runpy.run_path(str(project/'mechanical/scripts/finalize_structure_metadata.py'))
    data=json.loads((scratch/'reports/module_assembly.json').read_text())
    if i:assert data==first
    first=data
checks['metadata_repeated_run']='PASS'
common.ROOT=original_root
import assembly_animation as animation
animation.OUT=out/'animation';animation.TARGET=animation.OUT/'verification.blend'
sys.argv=['blender','--','--render','none']
animation.main()
manifest=json.loads((animation.OUT/'manifest.json').read_text())
assert manifest['ups_rear_controls_adopted'] and not manifest['rendered_video']
for n in common.P['ups_rear_controls']['reference_ids']:
    actor=bpy.data.objects[animation.AP+n]
    assert actor.parent.name==animation.AP+'Rear_Shell'
    assert n in manifest['part_stages']
for n in common.P['ups_rear_controls']['retired_ids']:
    assert n not in manifest['part_stages']
checks['animation_scratch_build']={k:manifest[k] for k in ['actor_count','final_transform_max_error_mm','source_is_unchanged','rendered_video','ups_rear_controls_adopted']}
(out/'intermediate.json').write_text(json.dumps(checks,indent=2)+'\n')
common.ROOT=scratch
import validate_off_shelf_modules as validate_current
validation=validate_current.run_current()
checks['current_geometry_validation']=validation['counts']
scope=json.loads((scratch/'reports/off_shelf_scope.json').read_text())
checks['matrix_receipt_scope']=scope['status']
checks['dock_source_provenance']=scope['dock_source_provenance']
checks['historical_hardware_provenance']={k:v for k,v in scope['historical_hardware_provenance'].items() if k not in ['missing_files','different_files']}
checks['historical_hardware_provenance']['missing_count']=len(scope['historical_hardware_provenance']['missing_files'])
checks['historical_hardware_provenance']['different_count']=len(scope['historical_hardware_provenance']['different_files'])
checks['blender']=bpy.app.version_string
assert before=={str(p.relative_to(project)):sha(p) for p in protected}
checks['published_models_and_video_unchanged']='PASS'
checks['protected_sha256']=before
(out/'blender_verification.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
print('REVIEW_BLENDER_VERIFICATION',checks,flush=True)

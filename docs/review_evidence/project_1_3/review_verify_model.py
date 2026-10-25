# -*- coding: utf-8 -*-
import sys,json,hashlib,shutil
from pathlib import Path
project=Path('/Users/dean/Documents/MORI');sys.path.insert(0,str(project/'mechanical/scripts'))
import common
from common import bpy
out=project/'.state/pr15_review';scratch=out/'mechanical'
protected=[project/'mechanical/mori_v1_2.blend',project/'mechanical/mori_assembly_animation.blend',project/'mechanical/animation/MORI_assembly.mp4']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={str(p.relative_to(project)):sha(p) for p in protected}
common.ROOT=scratch
import validate_off_shelf_modules as current
validation=current.run_current()
checks=json.loads((out/'intermediate.json').read_text())
checks['current_geometry_validation']=validation['counts']
scope=json.loads((scratch/'reports/off_shelf_scope.json').read_text())
checks['matrix_receipt_scope']=scope['status']
checks['dock_source_provenance']=scope['dock_source_provenance']
checks['historical_hardware_provenance']={k:v for k,v in scope['historical_hardware_provenance'].items() if k not in ['missing_files','different_files']}
checks['historical_hardware_provenance']['missing_count']=len(scope['historical_hardware_provenance']['missing_files'])
checks['historical_hardware_provenance']['different_count']=len(scope['historical_hardware_provenance']['different_files'])
checks['blender']=bpy.app.version_string
assert before=={str(p.relative_to(project)):sha(p) for p in protected}
checks['published_models_and_video_unchanged']='PASS';checks['protected_sha256']=before
(out/'blender_verification.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
print('REVIEW_MODEL_VERIFICATION',checks,flush=True)

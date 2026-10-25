# -*- coding: utf-8 -*-
import sys,json
from pathlib import Path
source=Path('/Users/dean/Documents/MORI');out=source/'.state/pr15_review'
sys.path.insert(0,str(source/'mechanical/scripts'))
import common
common.PROJECT=out/'portable';common.ROOT=common.PROJECT/'mechanical'
import validate_off_shelf_modules
result=validate_off_shelf_modules.run_current()
(out/'portable_verification.json').write_text(json.dumps({'counts':result['counts'],'source_blend_sha256':result['source_blend_sha256'],'restored_groups':['m1-58-inputs','m1-58-validation'],'unpublished_original_source_available':False,'historical_hardware_tree_available':False},indent=2)+'\n')

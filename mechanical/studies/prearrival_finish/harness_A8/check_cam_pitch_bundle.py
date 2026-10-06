"""Replay the independent packing and analytic bounds on the refined bundle.

The earlier side-pool results remain immutable. Each replay records this
wrapper and the exact source checker hash, using a separate output directory.
"""
from pathlib import Path
import hashlib,json
BUNDLE_CHECK_SCRIPT=Path(__file__).resolve();BUNDLE_CHECK_DIR=BUNDLE_CHECK_SCRIPT.parent
BUNDLE_PACKING_SOURCE=BUNDLE_CHECK_DIR/'check_cam_pitch_flex_packing.py'
BUNDLE_MATH_SOURCE=BUNDLE_CHECK_DIR/'audit_cam_pitch_flex_math.py'
BUNDLE_OUTPUT=BUNDLE_CHECK_DIR/'cam_pitch_flex/bundle'
assert json.loads((BUNDLE_OUTPUT/'flex_pool.json').read_text())['status']=='PASS'
packing_code=BUNDLE_PACKING_SOURCE.read_text()
assert packing_code.count("OUT=PACK_DIR/'cam_pitch_flex/side'")==1
packing_code=packing_code.replace("OUT=PACK_DIR/'cam_pitch_flex/side'","OUT=PACK_DIR/'cam_pitch_flex/bundle'")
exec(compile(packing_code,str(BUNDLE_PACKING_SOURCE),'exec'),globals())
math_code=BUNDLE_MATH_SOURCE.read_text()
assert math_code.count("OUT=HERE/'cam_pitch_flex/side'")==1
math_code=math_code.replace("OUT=HERE/'cam_pitch_flex/side'","OUT=HERE/'cam_pitch_flex/bundle'")
exec(compile(math_code,str(BUNDLE_MATH_SOURCE),'exec'),{'__file__':str(BUNDLE_CHECK_SCRIPT),'__name__':'__main__'})
for fname,checker in [('packing.json',BUNDLE_PACKING_SOURCE),('math_bounds.json',BUNDLE_MATH_SOURCE)]:
    p=BUNDLE_OUTPUT/fname;result=json.loads(p.read_text())
    result['source_replayed_checker_sha256']=hashlib.sha256(checker.read_bytes()).hexdigest()
    result['source_replayed_checker']=str(checker.relative_to(BUNDLE_CHECK_DIR))
    result['replay_scope']='Same checker; output directory and input candidate pool changed explicitly by wrapper'
    p.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('PITCH_BUNDLE_REPLAY_COMPLETE',flush=True)

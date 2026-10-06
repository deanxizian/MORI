"""Second support screen: shorten the bed top, leaving a clear wire exit.

The clearance rule and protected wire interval remain unchanged. This is a
real .2 mm shortening of the bed, not a collision exemption.
"""
from pathlib import Path
V2_SOURCE=Path(__file__).resolve().with_name('screen_CAM_anchor_support.py')
V2_CODE=V2_SOURCE.read_text()
assert V2_CODE.count("OUT=SUPPORT_ROOT/'cam_anchors';OUT.mkdir(exist_ok=True)")==1
V2_CODE=V2_CODE.replace("OUT=SUPPORT_ROOT/'cam_anchors';OUT.mkdir(exist_ok=True)","OUT=SUPPORT_ROOT/'cam_anchors/support_v2';OUT.mkdir(parents=True,exist_ok=True)")
assert V2_CODE.count("[float(xx.max()+1.2),-1.75,233.8]")==1
V2_CODE=V2_CODE.replace("[float(xx.max()+1.2),-1.75,233.8]","[float(xx.max()+1.2),-1.75,233.6]")
V2_CODE=V2_CODE.replace("'trials':trials,'accepted':accepted", "'parent_script_sha256':sha(V2_SOURCE),'bed_top_mm':233.6,'trials':trials,'accepted':accepted")
exec(compile(V2_CODE,str(V2_SOURCE),'exec'),globals())

"""A three-millimetre grip bed with relieved axial approach and departure.

Only the bed's flat axial ends move. All route coordinates, grooves, source
clearances and functional-interface checking limits remain unchanged.
"""
from pathlib import Path
V3_SOURCE=Path(__file__).resolve().with_name('screen_CAM_anchor_support.py')
V3_CODE=V3_SOURCE.read_text()
V3_CODE=V3_CODE.replace("OUT=SUPPORT_ROOT/'cam_anchors';OUT.mkdir(exist_ok=True)","OUT=SUPPORT_ROOT/'cam_anchors/support_v3';OUT.mkdir(parents=True,exist_ok=True)")
assert V3_CODE.count("-4.5,230.4],[float(xx.max()+1.2),-1.75,233.8]")==1
V3_CODE=V3_CODE.replace("-4.5,230.4],[float(xx.max()+1.2),-1.75,233.8]","-4.5,230.6],[float(xx.max()+1.2),-1.75,233.6]")
V3_CODE=V3_CODE.replace("'trials':trials,'accepted':accepted", "'parent_script_sha256':sha(V3_SOURCE),'bed_bottom_mm':230.6,'bed_top_mm':233.6,'trials':trials,'accepted':accepted")
exec(compile(V3_CODE,str(V3_SOURCE),'exec'),globals())

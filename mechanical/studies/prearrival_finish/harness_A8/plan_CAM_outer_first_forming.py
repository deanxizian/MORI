"""Use the same bounded reverse search with the opposite wire order.

The prior left-to-right order collides with the completed neighbouring tail.
Try the physically different right-to-left order; static and completed wires
stay in every packing check. This does not alter the final harness shape.
"""
from pathlib import Path
OF_SCRIPT=Path(__file__).resolve();OF_ROOT=OF_SCRIPT.parent
OF_HELPER=OF_ROOT/'plan_CAM_reverse_angle_forming.py';__file__=str(OF_HELPER)
exec(compile(OF_HELPER.read_text().split('\nfor stage in range(4):',1)[0],str(OF_HELPER),'exec'),globals())
RA_SCRIPT=OF_SCRIPT;RA_HELPER=OF_HELPER;__file__=str(OF_SCRIPT)
RA_OUT=L2_OUT/'outer_first_forming';RA_OUT.mkdir(exist_ok=True)
da_order=(3,2,1,0)
exec(compile('for stage in range(4):'+OF_HELPER.read_text().split('\nfor stage in range(4):',1)[1],str(OF_SCRIPT),'exec'),globals())

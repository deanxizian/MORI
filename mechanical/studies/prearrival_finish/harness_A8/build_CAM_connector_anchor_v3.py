"""A short tapered root gives the cable anchor a broad junction to the rear plate."""
from pathlib import Path
C3_SCRIPT=Path(__file__).resolve();C3_ROOT=C3_SCRIPT.parent
C3_HELPER=C3_ROOT/'build_CAM_connector_anchor.py';__file__=str(C3_HELPER)
code=C3_HELPER.read_text()
code=code.replace('CC_SCRIPT=Path(__file__).resolve();CC_ROOT=CC_SCRIPT.parent','CC_SCRIPT=C3_SCRIPT;CC_ROOT=C3_ROOT')
code=code.replace('for cc_ymin in [-26.,-27.,-28.,-29.,-30.]:','for cc_ymin in [-30.5]:')
code=code.replace('root=box([bb[0],cc_ymin,bb[5]-.01],[bb[3],bb[4],216.2])',
    "root=pw_prism([[cc_ymin,bb[5]-.01],[float(slots[0,1]-1.8),bb[5]-.01],[float(slots[0,1]-1.8),216.1],[-27.5,216.1],[cc_ymin,218.3]],bb[0],bb[3])")
code=code.replace("'root_top_z_mm':216.2", "'root_top_z_mm':[216.1,218.3],'root_front_y_mm':float(slots[0,1]-1.8),'taper_reaches_plate_front_z_mm':218.3-2.2/3.,'plate_lower_edge_z_mm':215.7")
code=code.replace("'root_screen.json'","'root_v3_screen.json'")
code=code.replace("f'root_y{cc_ymin}_addition.npz'","f'root_v3_y{cc_ymin}_addition.npz'")
code=code.replace("'helper_sha256':sha(CC_HELPER)","'helper_sha256':sha(CC_HELPER),'construction_helper_sha256':sha(C3_HELPER)")
exec(compile(code,str(C3_SCRIPT),'exec'),globals())

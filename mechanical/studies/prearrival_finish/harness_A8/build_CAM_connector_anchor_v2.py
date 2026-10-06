"""Keep the short connector-anchor root behind the housing's exit envelope."""
from pathlib import Path
C2_SCRIPT=Path(__file__).resolve();C2_ROOT=C2_SCRIPT.parent
C2_HELPER=C2_ROOT/'build_CAM_connector_anchor.py'
__file__=str(C2_HELPER)
code=C2_HELPER.read_text()
code=code.replace('CC_SCRIPT=Path(__file__).resolve();CC_ROOT=CC_SCRIPT.parent','CC_SCRIPT=C2_SCRIPT;CC_ROOT=C2_ROOT')
code=code.replace('for cc_ymin in [-26.,-27.,-28.,-29.,-30.]:','for cc_ymin in [-30.5,-31.]:')
code=code.replace('[bb[3],bb[4],216.2]','[bb[3],float(slots[0,1]-1.8),216.2]')
code=code.replace("'root_screen.json'","'root_v2_screen.json'")
code=code.replace("f'root_y{cc_ymin}_addition.npz'","f'root_v2_y{cc_ymin}_addition.npz'")
code=code.replace("'helper_sha256':sha(CC_HELPER)","'helper_sha256':sha(CC_HELPER),'construction_helper_sha256':sha(C2_HELPER)")
exec(compile(code,str(C2_SCRIPT),'exec'),globals())

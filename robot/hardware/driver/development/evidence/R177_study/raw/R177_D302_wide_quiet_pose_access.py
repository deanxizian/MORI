"""Widen D302 pose search inside the unchanged board and fixed interfaces.

Both signals are screened against the actual L701 projection after the local
18..34 mm comparison had no joint candidate. A finite-grid result still is not
a proof of global routability or physical/EMC qualification.
"""
from pathlib import Path
import sys
b=Path('robot/.state/c3-completion/trials')
mode=sys.argv[1];assert mode in ['fault','clr']
base=(b/'R177_D302_pose_access.py').read_text()
mods={"range(72,137)":"range(6,275)","range(22,73)":"range(6,135)","bounds_mm=[18,5.5,34,18]":"bounds_mm=[1.5,1.5,68.5,33.5]"}
for old,new in mods.items():assert base.count(old)==1; base=base.replace(old,new)
wrapper=(b/'R177_D302_quiet_pose_access.py').read_text()
old="src=(b/'R177_D302_pose_access.py').read_text()";assert wrapper.count(old)==1
wrapper=wrapper.replace(old,'src='+repr(base))
wrapper=wrapper.replace("R177-D302-quiet-","R177-D302-wide-quiet-")
exec(compile(wrapper,str(__file__),'exec'))

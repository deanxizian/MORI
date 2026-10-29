"""Use Shapely's required tuple mirror origin; preserve the failed v1/log."""
from pathlib import Path
src=Path('robot/.state/c3-completion/trials/R174_prepare_A.py').read_text()
src=src.replace('xfact=-1,yfact=1,origin=old','xfact=-1,yfact=1,origin=tuple(old)')
exec(compile(src,'R174_prepare_A_v2.py','exec'))

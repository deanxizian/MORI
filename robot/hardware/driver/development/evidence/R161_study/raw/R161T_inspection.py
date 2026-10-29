"""Reuse the preserved R inspection method on T and its outward C1303 ground escape."""
from pathlib import Path
source=Path('robot/.state/c3-completion/trials/R161R_inspection.py').read_text()
assert source.count('R161R')>0
exec(compile(source.replace('R161R','R161T'),'R161T_inspection_preserved_method','exec'))

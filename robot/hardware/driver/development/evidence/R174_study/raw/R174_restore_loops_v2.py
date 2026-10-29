"""Correct missing math import; retain original partial search and failure log."""
from pathlib import Path
src=Path('robot/.state/c3-completion/trials/R174_restore_loops.py').read_text()
src=src.replace('import ast,json,sys,time','import ast,json,math,sys,time')
src=src.replace("rev+'-restore-loops'","rev+'-restore-loops-v2'")
exec(compile(src,'R174_restore_loops_v2.py','exec'))

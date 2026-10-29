"""Restrict the insertion to a complete code line, not the loader's string."""
from pathlib import Path
src=Path('robot/.state/c3-completion/trials/R174_expanded_placement.py').read_text()
src=src.replace("base=base.replace('results=[];audits=[]',",r"base=base.replace('\nresults=[];audits=[]\n',")
exec(compile(src,'R174_expanded_placement_v2.py','exec'))

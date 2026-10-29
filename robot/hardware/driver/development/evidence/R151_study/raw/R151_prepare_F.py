"""Retain the screened short F escape at the new filter via.

Straightening that last 0.10 mm leg entered a mounted-face obstacle. Moving the
via left also failed the retained-reference screen. Keep the original proposal
here; the final candidate still requires complete visual and native acceptance.
"""
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
code=(b/'R151_prepare_E.py').read_text()
old="q['routes'][0]['points_mm']=[[58.7,23.675],[58.7,22.25],[59.05,21.9],[60.65,21.9],[61.25,21.3]]"
new="q['routes'][0]['points_mm']=[[58.7,23.675],[58.7,22.25],[59.05,21.9],[60.55,21.9],[61.15,21.3],[61.25,21.3]]"
assert code.count(old)==1
exec(compile(code.replace('R151E','R151F').replace(old,new),str(__file__),'exec'))

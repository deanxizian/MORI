"""Retain the C preflight failure and move the supply bend outside the new hole.

The final 0.10 mm centre attachment lies inside the existing 0.50 mm power-via
land; the external VDD path uses deliberate horizontal/45 degree segments.
"""
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
code=(b/'R167_prepare_C.py').read_text()
old='[56.15,14.65],[55.6,14.65],[55.2,15.05]'
new='[56.15,14.65],[55.5,14.65],[55.2,14.95],[55.2,15.05]'
assert code.count(old)==1;code=code.replace(old,new)
code=code.replace("b/'R167C-route-preflight.json'","b/'R167C-route-preflight-v2.json'")
exec(compile(code,str(__file__),'exec'))

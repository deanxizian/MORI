"""Replan FAULT while preserving the demonstrated R165M 3V3 supply corridor.

All previous copper, native guards, reference checks and mounted-face body
constraints remain. Only an additional planning obstacle is introduced.
"""
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
code=(b/'R166_fault_search.py').read_text()
code=code.replace("out=b/'R166-fault-extended-search.json'","out=b/'R166-fault-protected-search.json'")
old="free=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(blocked,allowed)])"
new="""spine=json.loads((b/'R166-power-spine.json').read_text());assert spine['source_sha256']==c.sha
reserve=LineString(spine['points_mm']).buffer(spine['preserved_width_mm']/2)
blocked[p.layers.index(spine['layer'])]=blocked[p.layers.index(spine['layer'])].union(reserve.buffer(p.internal_clearance+.102))
vf=vf & ~mask(reserve.buffer(p.internal_clearance+.252),p.xx,p.yy)
"""+old
assert code.count(old)==1;code=code.replace(old,new)
code=code.replace("adopted=False),indent=2)","adopted=False,power_reservation=spine),indent=2)")
exec(compile(code,str(__file__),'exec'))

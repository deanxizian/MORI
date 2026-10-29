"""FAULT search in joint placement with an explicit source 3V3 spine reservation.

The reservation adds an obstacle and never weakens native copper/reference or
power validation. All paths still require native fill and complete regression.
"""
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
code=(b/'R161_power_aware_search.py').read_text()
start=code.index('requests=[');end=code.index('\nrows=[]',start)
code=code[:start]+"requests=[('fault_main','/FAULT_N','Q1701.3','U1301.6')]"+code[end:]
code=code.replace("rev+'-power-aware-search'+suffix", "rev+'-fault-reserved-search'+suffix")
code=code.replace(".1,['B.Cu','F.Cu','In2.Cu','In3.Cu']", ".05,['B.Cu','F.Cu','In2.Cu','In3.Cu']")
code=code.replace('),600000)', '),2000000)')
old=' free,vf,blocked,allowed=p.geometry(net)'
new=old+"""
 spine=json.loads((b/'R166-power-spine.json').read_text())
 assert spine['source_sha256']=='899d526fda5da465fe2279448a0d2561bf6d0b5e6e964d478cfda28ddfad4f70'
 reserve=LineString(spine['points_mm']).buffer(spine['preserved_width_mm']/2)
 blocked[p.layers.index(spine['layer'])]=blocked[p.layers.index(spine['layer'])].union(reserve.buffer(p.internal_clearance+.102))
 vf=vf & ~mask(reserve.buffer(p.internal_clearance+.252),p.xx,p.yy)
"""
assert code.count(old)==1;code=code.replace(old,new)
exec(compile(code,str(__file__),'exec'))

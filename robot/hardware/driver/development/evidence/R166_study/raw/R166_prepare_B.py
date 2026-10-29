"""Compare the longer FAULT proposal that reserves the original power corridor.

This remains an independent native trial. No reduction is credited before all
source electrical/reference checks and the local route review pass.
"""
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
code=(b/'R166_prepare_A.py').read_text().replace('R166A','R166B')
changes={
 "R166-fault-extended-search.json":"R166-fault-protected-search.json",
 "[67.35,28.15]":"[45.6,31.2]",
 "[67.45,28.35];routes[0]['points_mm'][1]=[65.6,26.5]":"[45.7,31.4125];routes[0]['points_mm'][1]=[44.55,30.2625]",
 "checks=[]":"spine=d['power_reservation'];reserve=LineString(spine['points_mm']).buffer(spine['preserved_width_mm']/2)\nblocked[0]=blocked[0].union(reserve.buffer(p.internal_clearance+.102))\nchecks=[]"
}
for old,new in changes.items():
 assert code.count(old)==1,old
 code=code.replace(old,new)
exec(compile(code,str(__file__),'exec'))

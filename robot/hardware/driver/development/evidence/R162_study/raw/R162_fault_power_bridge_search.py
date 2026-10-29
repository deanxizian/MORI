"""FAULT routing with an explicit preserved source power corridor.
Protect the derived 0.48 mm In2 MOTION_3V3 path from new track clearances and
via antipads. In3 is available only for a local crossing, retaining the lower
UV routing corridor. These are added planning restrictions, not relaxed rules.
"""
from pathlib import Path
s=Path('robot/.state/c3-completion/trials/R161_power_aware_search.py').read_text().split('"""',2)[2]
start=s.index('requests=[');end=s.index('\nrows=[]',start)
s=s[:start]+"requests=[('fault_restore','/FAULT_N','U1301.6','U1501.1')]"+s[end:]
marker=" reserved={ly:unary_union"
insert=""" spine_data=json.loads((b/'R162-power-spine.json').read_text());assert spine_data['source_sha256']==c.sha
 spine=LineString(spine_data['points_mm']).buffer(spine_data['preserved_width_mm']/2)
 for i,ly in enumerate(p.layers):
  if ly=='In2.Cu':blocked[i]=blocked[i].union(spine.buffer(p.internal_clearance+.102))
  if ly=='In3.Cu':blocked[i]=blocked[i].union(box(-1,-1,71,36).difference(box(54,26.8,60.5,32.3)))
 vf=vf & ~mask(spine.buffer(p.internal_clearance+.252),p.xx,p.yy)
"""
assert s.count(marker)==1;s=s.replace(marker,insert+marker)
exec(compile(s,'R162_FAULT_protected_power_crossing','exec'))

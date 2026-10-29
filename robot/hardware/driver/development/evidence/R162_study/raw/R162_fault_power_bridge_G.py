"""Use G's short FAULT termination while protecting the actual power spine.
Permit a local In3 crossing and its left-side exit to the new FAULT transfer;
the right-hand lower In3 corridor remains excluded from this search.
"""
from pathlib import Path
s=Path('robot/.state/c3-completion/trials/R162_fault_power_bridge_search.py').read_text().split('"""',2)[2]
old="spine_data=json.loads((b/'R162-power-spine.json').read_text());assert spine_data['source_sha256']==c.sha"
assert s.count(old)==1;s=s.replace(old,"spine_data=json.loads((b/'R162-power-spine.json').read_text())")
old="spine=LineString(spine_data['points_mm']).buffer(spine_data['preserved_width_mm']/2)"
assert s.count(old)==1;s=s.replace(old,old+"\n assert spine.difference(c.copper[('MOTION_3V3','In2.Cu')]).area<1e-6")
old='box(54,26.8,60.5,32.3)';assert s.count(old)==1
s=s.replace(old,'box(54,26.8,60.5,32.3).union(box(53.8,31.8,55.25,34.5))')
exec(compile(s,'R162_FAULT_G_power_crossing','exec'))

"""Create a separate planning variant that also releases the exact UPS 5 V bridge.

The previous five-part screen stays immutable. This is an obstacle diagnosis,
not permission to lose the 5 V supply or relax any source power-width check.
"""
from pathlib import Path
import hashlib, json
b=Path('robot/.state/c3-completion/trials')
p=b/'R184_group_geometry.py';s=p.read_text()
s=s.replace('retired = set(prior[\'prospective_retired_tracks\'])', '''retired = set(prior['prospective_retired_tracks'])
retired.update({
    '49584c82-dde6-4c9c-8768-178c0fc8c362',
    'a31a40fd-b233-4146-a63a-03835d358a32',
    '44e2a4e3-ce64-4dba-b7de-b7ed075628be',
})
for u in ['49584c82-dde6-4c9c-8768-178c0fc8c362','a31a40fd-b233-4146-a63a-03835d358a32','44e2a4e3-ce64-4dba-b7de-b7ed075628be']:
    assert c.by_id[u].GetNetname() == '/06 {slash} CAM_Buck/UPS_5V'
    assert c.board.GetLayerName(c.by_id[u].GetLayer()) == 'B.Cu'
    assert abs(c.by_id[u].GetWidth()/1e6 - .3) < 1e-9''')
s=s.replace('assert len(retired) == 36','assert len(retired) == 39')
q=b/'R184_power_group_geometry.py';assert not q.exists();q.write_text(s)
for old,new in [('R184_group_pose_screen.py','R184_power_group_pose_screen.py'),('R184_pair_group.py','R184_pair_power_group.py')]:
    s=(b/old).read_text().replace('from R184_group_geometry import *','from R184_power_group_geometry import *').replace("'R184-group-","'R184-power-group-")
    q=b/new;assert not q.exists();q.write_text(s)
print('Separate three-track UPS_5V planning omission created; native board unchanged.')

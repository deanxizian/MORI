"""Read-only front-face bias-pair comparison using native mirrored footprints.
Both sides' fixed holes/pads are retained. Short outward F routes must preserve
actual In1 reference and all F native track keepouts. This is a placement
proposal only; side changes need explicit construction/delta/physical review.
"""
from pathlib import Path
s=Path('robot/.state/c3-completion/trials/R162_bias_near_enable.py').read_text().split('"""',2)[2]
s=s.replace("out=b/'R162-bias-near-enable.json'","out=b/'R163-front-bias.json'")
s=s.replace('pcb.B_CrtYd','pcb.F_CrtYd').replace('pcb.B_Cu','pcb.F_Cu').replace("'B.Cu'","'F.Cu'")
s=s.replace("('GND','In4.Cu')","('GND','In1.Cu')")
s=s.replace('common_node_route_B_mm','common_node_route_F_mm').replace('enable_route_B_mm','enable_route_F_mm')
old="f=pcb.FOOTPRINT(fs[name]);f.SetPosition(pcb.VECTOR2I(0,0));"
assert s.count(old)==1;s=s.replace(old,"f=pcb.FOOTPRINT(fs[name]);f.Flip(f.GetPosition(),False);f.SetPosition(pcb.VECTOR2I(0,0));")
old="[((255,307),(47,68)),((315,345),(24,48))]";assert s.count(old)==1
s=s.replace(old,"[((225,345),(15,140))]")
old="route_guards[net]=prep(unary_union(foreign).buffer(.302).union(holes.buffer(.402)))"
new="route_guards[net]=prep(unary_union(foreign).buffer(.302).union(holes.buffer(.402)).union(unary_union([k['shape'] for k in c.keepouts if k['tracks'] and 'F.Cu' in k['layers']]).buffer(.102)))"
assert s.count(old)==1;s=s.replace(old,new)
exec(compile(s,'R163_front_bias_native_mirror_search','exec'))

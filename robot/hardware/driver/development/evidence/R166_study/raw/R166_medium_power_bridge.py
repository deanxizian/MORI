"""Screen a 0.60/0.30 mm power transfer without changing any board or rule.

The earlier 0.80 mm proposal screen found no path. Obstacles are recalculated
for the actual smaller annulus; this is not a clearance or width relaxation.
"""
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
code=(b/'R151_power_region_bridge_v2.py').read_text()
for old,new in [('buffer(.15)','buffer(.05)'),('s.buffer(.607)','s.buffer(.507)'),("v['diameter_mm']=.8","v['diameter_mm']=.6"),('0.80','0.60'),('0.15','0.05')]:
 assert old in code,old
 code=code.replace(old,new)
exec(compile(code,str(__file__),'exec'))

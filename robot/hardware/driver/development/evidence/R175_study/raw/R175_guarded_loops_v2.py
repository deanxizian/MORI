"""Reserve INA+ and supervisor GND before the two branches that obstruct them.

This changes proposal order, retaining identical native geometry, references
and power reservations. Any combined proposal still needs native validation.
"""
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
src=(b/'R175_guarded_loops.py').read_text()
old="exec(compile(src,str(__file__),'exec'))"
new='''
src=src.replace("rev+'-R175-guarded-loops'", "rev+'-R175-guarded-loops-v2'")
src=src.replace("('ina_input_minus','R1707.2','U1701.2'),('ina_input_plus','R1706.2','U1701.1')", "('ina_input_plus','R1706.2','U1701.1'),('ina_input_minus','R1707.2','U1701.2')")
src=src.replace("('supervisor_ct','R1310.1','U1302.4'),('supervisor_vdd','C1304.1','U1302.5'),('supervisor_gnd','C1304.2','U1302.2')", "('supervisor_gnd','C1304.2','U1302.2'),('supervisor_ct','R1310.1','U1302.4'),('supervisor_vdd','C1304.1','U1302.5')")
exec(compile(src,str(__file__),'exec'))
'''
assert src.count(old)==1;src=src.replace(old,new)
exec(compile(src,str(__file__),'exec'))

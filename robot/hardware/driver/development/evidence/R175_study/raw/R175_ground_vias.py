"""Check supervisor return with new GND transfers allowed by native rules.

Earlier loop proposals artificially used existing GND vias only. Additional
GND vias do not move or remove any of the 114 originals. Native restrictions,
reference screen, supply reservations and subsequent acceptance all remain.
"""
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
src=(b/'R175_guarded_loops.py').read_text()
old="exec(compile(src,str(__file__),'exec'))"
new='''
src=src.replace("rev+'-R175-guarded-loops'", "rev+'-R175-ground-vias'")
start=src.index('tasks=[');end=src.index('\\nrows=[]',start)
src=src[:start]+"tasks=[('supervisor_gnd','C1304.2','U1302.2')]"+src[end:]
src=src.replace(" if net=='GND':vf=np.zeros_like(vf)", " # New GND transfers retain all normal geometric restrictions.")
src=src.replace("  assert not actual or net!='GND'", "  assert all(v['diameter_mm']==.5 and v['drill_mm']==.3 for v in actual)")
exec(compile(src,str(__file__),'exec'))
'''
assert src.count(old)==1;src=src.replace(old,new)
exec(compile(src,str(__file__),'exec'))

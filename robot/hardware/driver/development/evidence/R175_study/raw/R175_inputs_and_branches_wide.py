"""Include the actual U1702 native destination region in the joint search.

Expand the bounded grid to x=64 mm only. Reference-ground masks are recomputed
by the underlying search from the expanded mesh; native rules are unchanged.
"""
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
src=(b/'R175_inputs_and_branches.py').read_text()
old="exec(compile(src,str(__file__),'exec'))"
new="src=src.replace(\"rev+'-R175-inputs-branches'\",\"rev+'-R175-inputs-branches-wide'\")\nsrc=src.replace('np.arange(40,55.001,p.grid)','np.arange(40,64.001,p.grid)').replace('bounds_mm=[40,5,55,21]','bounds_mm=[40,5,64,21]')\n"+old
assert src.endswith(old+'\n');src=src[:-len(old+'\n')]+new+'\n'
exec(compile(src,str(__file__),'exec'))

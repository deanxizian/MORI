"""Add the observed L701 coupling concern to the checked power-aware search.

This is an explicit optional planning avoidance for this inductor, not a native
rule change and not a blanket ban under all opposite-face component bodies.
"""
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
src=(b/'R177_guarded_route.py').read_text()
old="out=b/(rev+'-R177-'+name)";assert src.count(old)==1
src=src.replace(old,"out=b/(rev+'-R177-quiet-'+name)")
old='blocked=list(blocked)';assert src.count(old)==1
src=src.replace(old,"blocked=list(blocked)\ninductor=fab(next(f for f in c.footprints if f.GetReference()=='L701'))\nblocked=[ob.union(inductor.buffer(.102)) for ob in blocked]")
exec(compile(src,str(__file__),'exec'))

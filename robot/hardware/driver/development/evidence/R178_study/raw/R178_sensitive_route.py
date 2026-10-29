"""D302 route planning with explicit opposite DVDT aperture avoidance.

Retain the R177 full supply reservations and native rules. For a new F trace,
avoid the actual B DVDT copper where neither internal GND plane intervenes.
This is a local design choice for this analog control node, not a global ban on
opposite-face projections or a physical coupling qualification.
"""
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
src=(b/'R177_guarded_route.py').read_text()
src=src.replace("out=b/(rev+'-R177-'+name)","out=b/(rev+'-R178-sensitive-'+name)")
old='blocked=list(blocked)';assert src.count(old)==1
src=src.replace(old,"""blocked=list(blocked)
inductor=fab(next(f for f in c.footprints if f.GetReference()=='L701'))
blocked=[ob.union(inductor.buffer(.102)) for ob in blocked]
dvd=c.copper['Net-(U1201-DVDT)','B.Cu']
unshielded=dvd.difference(c.copper['GND','In1.Cu'].union(c.copper['GND','In4.Cu']))
blocked[p.layers.index('F.Cu')]=blocked[p.layers.index('F.Cu')].union(unshielded.buffer(.102))
""")
exec(compile(src,str(__file__),'exec'))

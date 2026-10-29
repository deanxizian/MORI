"""Reserve original local PTH GND thermal copper in addition to power guards.

R177K exposed a real native R25 starved-thermal failure at J102.2. The 1 mm
source-copper neighbourhood here is a conservative search reservation, not a
new design rule or a substitute for native refill and spoke-count checks.
"""
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
base=(b/'R177_guarded_route.py').read_text()
old="out=b/(rev+'-R177-'+name)";assert base.count(old)==1
base=base.replace(old,"out=b/(rev+'-R177-thermal-'+name)")
old='blocked=list(blocked)';assert base.count(old)==1
base=base.replace(old,"""blocked=list(blocked)
inductor=fab(next(f for f in c.footprints if f.GetReference()=='L701'))
thermal={ly:[] for ly in LAYERS}
for pad in source.pads:
    if pad.GetNetname()!='GND' or pad.GetAttribute()!=pcb.PAD_ATTRIB_PTH:continue
    for ly in LAYERS:
        land=source.shapes.get((uid(pad),ly))
        if land is not None:
            # Preserve only received filled copper outside the fixed pad land.
            ring=land.buffer(1.0).difference(land.buffer(-.001))
            thermal[ly].append(ring.intersection(source.copper.get(('GND',ly),GeometryCollection())))
thermal={ly:unary_union(v) for ly,v in thermal.items()}
blocked=[ob.union(inductor.buffer(.102)).union(thermal[ly].buffer((p.internal_clearance if ly.startswith('In') else .2)+.102)) for ob,ly in zip(blocked,p.layers)]
tg=unary_union([g.buffer((p.internal_clearance if ly.startswith('In') else .2)+.252) for ly,g in thermal.items()])
vf &= ~mask(tg,p.xx,p.yy)
(out/'thermal-guard.json').write_text(json.dumps(dict(source_sha256=source.sha,radius_beyond_native_land_mm=1.0,area_mm2={ly:g.area for ly,g in thermal.items()},scope='Conservative source copper neighbourhood; native R25 must still pass.'),indent=2)+'\\n')
""")
exec(compile(base,str(__file__),'exec'))

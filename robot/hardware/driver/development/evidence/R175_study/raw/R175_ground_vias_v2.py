"""Ground via planning omits the non-ground-via reference-antipad proxy only.

A GND via does not create a foreign-net hole in GND reference planes. Retain
all pad, hole, native body/keepout and supply reservations. All native audits,
including reference copper and width preservation, remain unchanged.
"""
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
src=(b/'R175_ground_vias.py').read_text()
old="exec(compile(src,str(__file__),'exec'))"
# Insert into the final compiled search, not the outer loader.
needle="src=src.replace(\"  assert not actual or net!='GND'\", \"  assert all(v['diameter_mm']==.5 and v['drill_mm']==.3 for v in actual)\")"
extra='''
src=src.replace("rev+'-R175-ground-vias'", "rev+'-R175-ground-vias-v2'")
anchor="rows=[];newroutes=[];newvias=[];geometries={}"
replacement=anchor+chr(10)+"""
common=[]
common.extend(s.buffer(.457) for (u,_),s in c.shapes.items() if isinstance(c.by_id[u],pcb.PAD))
common.extend(k['shape'].buffer(.257) for k in c.keepouts if k['vias'])
common.extend(Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6+.307) for v in c.vias)
common.extend(Point(xy(q.GetPosition())).buffer(max(xy(q.GetDrillSize()))/2+.557) for q in c.pads if max(xy(q.GetDrillSize()))>0)
p.via_common=unary_union(common)
"""
assert src.count(anchor)==1;src=src.replace(anchor,replacement)
'''
assert src.count(needle)==1;src=src.replace(needle,needle+'\n'+extra)
exec(compile(src,str(__file__),'exec'))

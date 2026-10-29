"""Use actual received thermal gaps and current refilled native spoke geometry.

The earlier 1 mm neighbourhood overprotected adjacent plane copper. Here the
reservation extends only 0.05 mm beyond each actual native thermal gap, with
the actual zone clearance. It still does not replace native R25 verification.
"""
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
src=(b/'R177_thermal_guarded_route.py').read_text()
src=src.replace("rev+'-R177-thermal-'+name", "rev+'-R177-native-spokes-'+name")
src=src.replace("for pad in source.pads:", "for pad in c.pads:")
src=src.replace("land=source.shapes.get((uid(pad),ly))", "land=c.shapes.get((uid(pad),ly))")
src=src.replace("ring=land.buffer(1.0).difference(land.buffer(-.001))", "zones=[z for z in c.zones if not z.GetIsRuleArea() and z.GetNetname()=='GND' and z.IsOnLayer(c.ids[ly])]\n            gap=pad.GetThermalGap()/1e6 or max([z.GetThermalReliefGap()/1e6 for z in zones]+[0.0])\n            ring=land.buffer(gap+.05).difference(land.buffer(-.001))")
src=src.replace("source.copper.get(('GND',ly)", "c.copper.get(('GND',ly)")
src=src.replace("thermal={ly:unary_union(v) for ly,v in thermal.items()}", "thermal={ly:unary_union(v) for ly,v in thermal.items()}\nzone_clear={ly:max([z.GetLocalClearance()/1e6 for z in c.zones if not z.GetIsRuleArea() and z.GetNetname()=='GND' and z.IsOnLayer(c.ids[ly])]+[p.internal_clearance if ly.startswith('In') else .2]) for ly in LAYERS}")
src=src.replace("thermal[ly].buffer((p.internal_clearance if ly.startswith('In') else .2)+.102)", "thermal[ly].buffer(zone_clear[ly]+.102)")
src=src.replace("g.buffer((p.internal_clearance if ly.startswith('In') else .2)+.252) for ly,g in thermal.items()", "g.buffer(zone_clear[ly]+.252) for ly,g in thermal.items()")
src=src.replace("source_sha256=source.sha,radius_beyond_native_land_mm=1.0", "source_sha256=c.sha,extra_beyond_native_thermal_gap_mm=.05,zone_clearance_mm=zone_clear")
exec(compile(src,str(__file__),'exec'))

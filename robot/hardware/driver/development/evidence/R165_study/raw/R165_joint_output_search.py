"""Search UV output while preserving the proven In3 3V3 supply corridor.
Additional via reservations avoid the immediate THT ground thermal area.
These conservative planning restrictions supplement native rules and never
waive thermal, reference, power or body checks after native refill.
"""
from pathlib import Path

b=Path('robot/.state/c3-completion/trials')
s=(b/'R161_power_aware_search.py').read_text().split('"""',2)[2]
start=s.index('requests=[');end=s.index('\nrows=[]',start)
s=s[:start]+"requests=[('uv_output','/13 {slash} Head_Fault_Delay/HEAD_UV_N','U1301.1','Q1301.2')]"+s[end:]
marker=" reserved={ly:unary_union"
insert=""" spine_data=json.loads((b/'R165D-power-spine.json').read_text());assert spine_data['source_sha256']==c.sha
 spine=LineString(spine_data['points_mm']).buffer(spine_data['preserved_width_mm']/2)
 for i,ly in enumerate(p.layers):
  if ly=='In3.Cu':blocked[i]=blocked[i].union(spine.buffer(p.internal_clearance+.102))
 vf=vf & ~mask(spine.buffer(p.internal_clearance+.252),p.xx,p.yy)
 thermal_reservation=unary_union([Point(xy(pad.GetPosition())).buffer(2.05)
     for pad in c.pads if pad.GetNetname()=='GND' and pad.GetAttribute()==pcb.PAD_ATTRIB_PTH])
 vf=vf & ~mask(thermal_reservation,p.xx,p.yy)
"""
assert s.count(marker)==1;s=s.replace(marker,insert+marker)
exec(compile(s,'R165_supply_and_thermal_reserved_output_search','exec'))

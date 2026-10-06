"""Re-route the local charge-status signal to clear the new E/SPI corridors."""
import route_motion_P5R7 as r
from update_native_P5R7 import *
name,d,p=paths('motion');OUT=HERE/'reports/motion'
source=OUT/'SPI_manual_before_CHG.kicad_pcb'
if not source.exists():source.write_bytes(p.read_bytes())
b=k.LoadBoard(str(source))
remove={'65379008-dbbc-45ee-b075-5cf238e943e3','9cb6132a-e98a-4bf2-b7af-284f89867331',
 '0e2f0cf8-a2d7-4576-8e54-f327b7682edf','e6576df9-c6e2-48a6-a8bb-3ab7093d2d42',
 '3cb6e421-00f4-4895-b291-0fdcef43fb42','92020e6f-4be8-4dbb-98fa-58e2b40c4a08',
 'cdcaf6e1-f3f8-475b-8dd5-6ee1abd2a482'}
for t in list(b.GetTracks()):
    if t.m_Uuid.AsString()in remove:assert t.GetNetname()=='/CHG_N';b.Delete(t)
r.b=b;r.SEARCH_BOUNDS=(15,31.5,16,34.4);r.START_OPTIONS=None
plan=r.plan('/CHG_N',((24.0792,20.0152),k.F_Cu),[((28.8544,31.5976),k.F_Cu)])
assert (25.5,20.5) in plan['vias']
# The removed backbone also served D3.1 and R18.1; reconnect both numbered
# pads using outward escapes, not just the end-to-end status transport.
taps=[[(25.5,20.5),(27,19.0)],[(28,20.675),(28,20.0),(27,19.0)]]
for points in taps:track(b,'/CHG_N',points,.2,k.B_Cu)
dump(OUT/'CHG_clearance_route.json',{'route':plan,'pad_branch_taps_B_mm':taps,'removed':sorted(remove),
 'scope':'Charge-status signal only; circuit, pin functions, power conductors and component placement unchanged.'})
b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
oldname,oldd,_=paths('motion','P5R6')
(d/(name+'.kicad_pro')).write_text((oldd/(oldname+'.kicad_pro')).read_text().replace(oldname,name).replace('V1.2-H0.5-P5R6','V1.2-H0.5-P5R7'))
checks('motion','chg_clearance')

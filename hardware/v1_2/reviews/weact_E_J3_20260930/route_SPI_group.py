"""Treat the E-adjacent SPI routes as a group so transitions cannot block peers."""
import sys
import route_motion_P5R7 as r
from update_native_P5R7 import *
name,d,p=paths('motion');OUT=HERE/'reports/motion'
b=k.LoadBoard(str(OUT/'CS_outer_source.kicad_pcb'))
oldname,oldd,oldp=paths('motion','P5R6')
old=k.LoadBoard(str(oldp));original={t.m_Uuid.AsString()for t in old.GetTracks()}
for t in list(b.GetTracks()):
    if t.m_Uuid.AsString()not in original and t.GetNetname()in ['/IMU_CS','/IMU_MOSI','/IMU_SCK']:b.Delete(t)
r.b=b;r.SEARCH_BOUNDS=(.6,69.4,.6,34.4);r.START_OPTIONS=None
specs={
 'CS':('/IMU_CS',((23.5,26.175),k.B_Cu),[((45.719999,21.336),k.B_Cu)]),
 'MOSI':('/IMU_MOSI',((29.5,26.175),k.B_Cu),[((46.228,21.843999),k.B_Cu),((46.228,21.843999),k.F_Cu)]),
 'SCK':('/IMU_SCK',((27.325,27),k.B_Cu),[((41.147999,22.6568),k.B_Cu)]),
}
order=sys.argv[1:] or ['CS','MOSI','SCK'];tag='spi_'+'_'.join(order).lower()
plans=[]
for key in order:
    plans.append(r.plan(*specs[key]))
    dump(OUT/(tag+'_route.json'),plans)
    k.SaveBoard(str(OUT/(tag+'_partial.kicad_pcb')),b)
b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
(d/(name+'.kicad_pro')).write_text((oldd/(oldname+'.kicad_pro')).read_text().replace(oldname,name).replace('V1.2-H0.5-P5R6','V1.2-H0.5-P5R7'))
checks('motion',tag)

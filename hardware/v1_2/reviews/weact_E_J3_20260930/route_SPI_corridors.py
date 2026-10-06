"""Open a separate SCK corridor and put each signal via outside that corridor."""
import route_motion_P5R7 as r
from update_native_P5R7 import *
from geometry_guard_P5 import Guard
name,d,p=paths('motion');OUT=HERE/'reports/motion'
b=k.LoadBoard(str(OUT/'spi_cs_mosi_sck_partial.kicad_pcb'))
oldname,oldd,oldp=paths('motion','P5R6')
old=k.LoadBoard(str(oldp));original={t.m_Uuid.AsString()for t in old.GetTracks()}
ground=None
for t in list(b.GetTracks()):
    if t.m_Uuid.AsString()in original:continue
    if isinstance(t,k.PCB_VIA):
        if t.GetNetname()=='/IMU_MOSI' and xy(t.GetPosition())==(32.2,28.6):t.SetPosition(pt(32.2,28.0))
        if t.GetNetname()=='/GND' and xy(t.GetPosition())==(39.1,29.4):ground=t;b.Delete(t)
        continue
    a,z=xy(t.GetStart()),xy(t.GetEnd())
    if t.GetNetname()=='/IMU_CS' and t.GetLayer()==k.F_Cu:b.Delete(t);continue
    if t.GetNetname()=='/IMU_MOSI':
        if t.GetLayer()==k.F_Cu and max(a[0],z[0])<35:b.Delete(t);continue
        if t.GetLayer()==k.B_Cu and set([a,z])=={(32.2,28.6),(39.2,28.6)}:b.Delete(t)
plans=[
 ('/IMU_CS',k.F_Cu,[(25.3,24.4),(27,24.4),(31.6,29),(43.3,29),(43.3,23.3),(45,21.6)]),
 ('/IMU_MOSI',k.F_Cu,[(30.7,27.1),(31.3,27.1),(32.2,28.0)]),
 ('/IMU_MOSI',k.B_Cu,[(32.2,28.0),(32.8,28.6),(39.2,28.6)]),
]
for net,layer,points in plans:track(b,net,points,.2,layer)
for net,layer,points in plans:
    g=Guard(b,net)
    for a,z in zip(points,points[1:]):
        if not g.line_clear(a,z,layer):print('GUARD',net,a,z,flush=True)
g=Guard(b,'/GND');q=None
for candidate in [(42,25.5),(42,26),(42,24.5),(41.5,26),(41,25.5),(44.5,26)]:
    if g.via_clear(candidate,.8):q=candidate;break
assert q,'Need a clear GND stitch site'
via(b,'/GND',*q,vd=.8,dr=.3,grid=False)
print('GND stitch',q,flush=True)
k.SaveBoard(str(OUT/'SPI_corridors_source.kicad_pcb'),b)
r.b=b;r.SEARCH_BOUNDS=(.6,69.4,.6,34.4);r.START_OPTIONS=None
plan=r.plan('/IMU_SCK',((27.325,27),k.B_Cu),[((41.147999,22.6568),k.B_Cu)])
dump(OUT/'SPI_corridors_route.json',{'SCK':plan,'GND_stitch':q,'manual_routes':[(n,b.GetLayerName(l),v)for n,l,v in plans]})
b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
(d/(name+'.kicad_pro')).write_text((oldd/(oldname+'.kicad_pro')).read_text().replace(oldname,name).replace('V1.2-H0.5-P5R6','V1.2-H0.5-P5R7'))
checks('motion','spi_corridors')

"""Open the bottom outer corridors by placing the MOSI transition before E."""
import route_motion_P5R7 as r
from update_native_P5R7 import *
from geometry_guard_P5 import Guard
name,d,p=paths('motion');OUT=HERE/'reports/motion'
b=k.LoadBoard(str(OUT/'CLR_CS_partial.kicad_pcb'))
oldname,oldd,oldp=paths('motion','P5R6')
old=k.LoadBoard(str(oldp));original={t.m_Uuid.AsString()for t in old.GetTracks()}
for t in list(b.GetTracks()):
    if t.GetNetname()=='/ARM_FEEDBACK':b.Delete(t);continue
    if t.GetNetname()!='/IMU_MOSI' or t.m_Uuid.AsString()in original:continue
    if isinstance(t,k.PCB_VIA):
        if xy(t.GetPosition())==(34.1,29.3):t.SetPosition(pt(32.15,28.55))
    elif (t.GetLayer()==k.F_Cu and max(xy(t.GetStart())[0],xy(t.GetEnd())[0])<35)or(t.GetLayer()==k.B_Cu and min(xy(t.GetStart())[0],xy(t.GetEnd())[0])>33):
        b.Delete(t)
plans=[
 ('/ARM_FEEDBACK',k.B_Cu,[(32.825,16.5),(32.825,23.5),(31.425,24.9),(31.425,29.005),(30.23,30.2)]),
 ('/IMU_MOSI',k.F_Cu,[(30.7,27.1),(32.15,28.55)]),
 ('/IMU_MOSI',k.B_Cu,[(32.15,28.55),(40.8,28.55)]),
]
for net,layer,points in plans:track(b,net,points,.2,layer)
for net,layer,points in plans:
    g=Guard(b,net)
    for a,z in zip(points,points[1:]):
        if not g.line_clear(a,z,layer):print('GUARD',net,a,z,flush=True)
k.SaveBoard(str(OUT/'CS_outer_source.kicad_pcb'),b)
r.b=b;r.SEARCH_BOUNDS=(.6,69.4,.6,34.4);r.START_OPTIONS=None
plan=r.plan('/IMU_CS',((23.5,26.175),k.B_Cu),[((45.719999,21.336),k.B_Cu)])
dump(OUT/'CS_outer_route.json',plan)
b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
(d/(name+'.kicad_pro')).write_text((oldd/(oldname+'.kicad_pro')).read_text().replace(oldname,name).replace('V1.2-H0.5-P5R6','V1.2-H0.5-P5R7'))
checks('motion','cs_outer')

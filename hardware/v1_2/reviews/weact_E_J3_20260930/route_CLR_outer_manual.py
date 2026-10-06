"""Reorder CS/CLR upper corridors, preserving source R13 and all component poses."""
from update_native_P5R7 import *
from geometry_guard_P5 import Guard,obstacles
name,d,p=paths('motion');OUT=HERE/'reports/motion'
b=k.LoadBoard(str(OUT/'polished_CLR_source.kicad_pcb'))
oldname,oldd,oldp=paths('motion','P5R6')
old=k.LoadBoard(str(oldp));original={t.m_Uuid.AsString()for t in old.GetTracks()}
for t in list(b.GetTracks()):
    if t.m_Uuid.AsString()in original:continue
    if t.GetNetname()=='/CLR_N' and (isinstance(t,k.PCB_VIA)or t.GetLayer()==k.F_Cu):
        b.Delete(t);continue
    if t.GetNetname()=='/IMU_CS' and not isinstance(t,k.PCB_VIA)and t.GetLayer()==k.F_Cu:
        a,z=xy(t.GetStart()),xy(t.GetEnd())
        if max(a[1],z[1])<=17.3:b.Delete(t)
plans=[
 ('/IMU_CS',k.F_Cu,[(28.7,17.3),(28.7,15),(38.4,15),(38.4,15.5)]),
 ('/CLR_N',k.F_Cu,[(30,16.6),(30.85,15.75),(33.2,15.75),(33.7,16.25),(47.5,16.25),(48,16.75),(48,27.9),(48.2,28.1),(48.5,28.1)]),
]
for net,layer,points in plans:track(b,net,points,.2,layer)
via(b,'/CLR_N',30,16.6,vd=.8,dr=.3,grid=False)
for net,layer,points in plans:
    guard=Guard(b,net)
    for a,z in zip(points,points[1:]):
        if not guard.line_clear(a,z,layer):print('GUARD',net,a,z,flush=True)
print('VIA obstacles',[(b.GetLayerName(l),obstacles(b,'/CLR_N',(30,16.6),l,.8,True))for l in [k.F_Cu,k.B_Cu]],flush=True)
b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
(d/(name+'.kicad_pro')).write_text((oldd/(oldname+'.kicad_pro')).read_text().replace(oldname,name).replace('V1.2-H0.5-P5R6','V1.2-H0.5-P5R7'))
checks('motion','clr_outer_manual')

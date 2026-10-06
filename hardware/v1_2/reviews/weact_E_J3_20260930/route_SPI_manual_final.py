"""Explicit outward outer-layer corridors, with layer transitions before E."""
from update_native_P5R7 import *
from geometry_guard_P5 import Guard,obstacles
name,d,p=paths('motion');OUT=HERE/'reports/motion'
b=k.LoadBoard(str(OUT/'SPI_corridors_source.kicad_pcb'))
oldname,oldd,oldp=paths('motion','P5R6')
old=k.LoadBoard(str(oldp));original={t.m_Uuid.AsString()for t in old.GetTracks()}
for t in list(b.GetTracks()):
    if t.m_Uuid.AsString()not in original and t.GetNetname()in ['/IMU_CS','/IMU_MOSI','/IMU_SCK']:b.Delete(t)
plans=[
 ('/IMU_CS',k.B_Cu,[(23.5,26.175),(23.5,24.4),(25.3,24.4)]),
 ('/IMU_CS',k.F_Cu,[(25.3,24.4),(28.6,24.4),(33.24,29.04),(43.3,29.04),(43.3,23.3),(45,21.6)]),
 ('/IMU_CS',k.B_Cu,[(45,21.6),(45.264,21.336),(45.719999,21.336)]),
 ('/IMU_MOSI',k.B_Cu,[(29.5,26.175),(29.5,25.8),(32.1,23.2)]),
 ('/IMU_MOSI',k.F_Cu,[(32.1,23.2),(33.2,24.3),(33.2,25)]),
 ('/IMU_MOSI',k.B_Cu,[(33.2,25),(33.2,28.6),(39.2,28.6),(39.2,25.7),(41.5,23.4),(44.4,23.4)]),
 ('/IMU_MOSI',k.F_Cu,[(44.4,23.4),(44.671999,23.4),(46.228,21.843999)]),
 ('/IMU_SCK',k.B_Cu,[(27.325,27),(27.325,25.725),(28.8,24.25),(29.5,24.25)]),
 ('/IMU_SCK',k.F_Cu,[(29.5,24.25),(33.5,28.25),(33.5,28.6),(40.8,28.6),(40.8,23.004799)]),
 ('/IMU_SCK',k.B_Cu,[(40.8,23.004799),(41.147999,22.6568)]),
]
new_vias={'/IMU_CS':[(25.3,24.4),(45,21.6)],'/IMU_MOSI':[(32.1,23.2),(33.2,25),(44.4,23.4)],'/IMU_SCK':[(29.5,24.25),(40.8,23.004799)]}
for net,layer,points in plans:track(b,net,points,.2,layer)
for net,points in new_vias.items():
    for q in points:via(b,net,*q,vd=.8,dr=.3,grid=False)
issues=[]
for net,layer,points in plans:
    g=Guard(b,net)
    for a,z in zip(points,points[1:]):
        if not g.line_clear(a,z,layer):issues.append([net,b.GetLayerName(layer),a,z]);print('GUARD',issues[-1],flush=True)
for net,points in new_vias.items():
    for q in points:
        hit=[(b.GetLayerName(l),obstacles(b,net,q,l,.8,True))for l in [k.F_Cu,k.B_Cu]]
        if any(x[1]for x in hit):print('VIA',net,q,hit,flush=True)
dump(OUT/'SPI_manual_final_route.json',{'runs':[(n,b.GetLayerName(l),v)for n,l,v in plans],'vias':new_vias,'guard_candidates':issues,'inner_signal_tracks':0})
b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
(d/(name+'.kicad_pro')).write_text((oldd/(oldname+'.kicad_pro')).read_text().replace(oldname,name).replace('V1.2-H0.5-P5R6','V1.2-H0.5-P5R7'))
checks('motion','spi_manual_final')

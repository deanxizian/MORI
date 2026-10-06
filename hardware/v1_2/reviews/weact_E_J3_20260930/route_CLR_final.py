"""Complete CLR routing after the reviewed R19 rotation, retaining all other routes."""
import route_motion_P5R7 as r
from update_native_P5R7 import *
name,d,p=paths('motion');OUT=HERE/'reports/motion'
src=OUT/'polished_CLR_source.kicad_pcb'
if not src.exists():src.write_bytes(p.read_bytes())
b=k.LoadBoard(str(src));oldname,oldd,oldp=paths('motion','P5R6')
old=k.LoadBoard(str(oldp));original={t.m_Uuid.AsString()for t in old.GetTracks()}
for t in list(b.GetTracks()):
    if t.GetNetname()=='/CLR_N' and t.m_Uuid.AsString()not in original:
        if isinstance(t,k.PCB_VIA)or t.GetLayer()==k.F_Cu:b.Delete(t)
r.b=b;r.SEARCH_BOUNDS=(.6,69.4,.6,34.4)
# These existing plated vias/B4 belong to the same retained left CLR backbone.
# Reuse their actual layer transitions instead of treating them as a new via.
r.START_OPTIONS=[(q,l)for q in [(11.785599,12.090399),(22.2504,16.052799),(16.052799,13.817599),(9.91,2.26)]for l in [k.F_Cu,k.B_Cu]]
r.START_OPTIONS.append(((27,15.85),k.B_Cu))
plan=r.plan('/CLR_N',((27,15.85),k.B_Cu),[((48.5,28.1),k.F_Cu)])
dump(OUT/'CLR_final_route.json',plan)
b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
(d/(name+'.kicad_pro')).write_text((oldd/(oldname+'.kicad_pro')).read_text().replace(oldname,name).replace('V1.2-H0.5-P5R6','V1.2-H0.5-P5R7'))
checks('motion','clr_final')

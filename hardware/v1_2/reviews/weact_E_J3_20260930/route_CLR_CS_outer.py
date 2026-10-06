"""Route the two conflicting outer-layer nets together; original rules preserved."""
import route_motion_P5R7 as r
from update_native_P5R7 import *
name,d,p=paths('motion');OUT=HERE/'reports/motion'
b=k.LoadBoard(str(OUT/'polished_CLR_source.kicad_pcb'))
oldname,oldd,oldp=paths('motion','P5R6')
old=k.LoadBoard(str(oldp));original={t.m_Uuid.AsString()for t in old.GetTracks()}
for t in list(b.GetTracks()):
    if t.m_Uuid.AsString()in original:continue
    if t.GetNetname()=='/IMU_CS' or (t.GetNetname()=='/CLR_N' and (isinstance(t,k.PCB_VIA)or t.GetLayer()==k.F_Cu)):
        b.Delete(t)
shifts={
 '/IMU_SCK':{(33.4,28.6):(33.35,28.55),(39.2,28.6):(39.2,28.55)},
 '/IMU_MOSI':{(34.8,28.6):(34.85,28.55),(40.8,28.6):(40.8,28.55),(46.228,23.171999):(46.228,23.121999)},
}
for t in b.GetTracks():
    if t.m_Uuid.AsString()in original or t.GetNetname()not in shifts:continue
    table=shifts[t.GetNetname()]
    if isinstance(t,k.PCB_VIA):
        q=xy(t.GetPosition())
        if q in table:t.SetPosition(pt(*table[q]))
    else:
        for get,setter in [(t.GetStart,t.SetStart),(t.GetEnd,t.SetEnd)]:
            q=xy(get())
            if q in table:setter(pt(*table[q]))
r.b=b;r.SEARCH_BOUNDS=(.6,69.4,.6,34.4)
starts=set()
for t in b.GetTracks():
    if t.GetNetname()!='/CLR_N':continue
    for q in [xy(t.GetStart()),xy(t.GetEnd())]:
        if q[0]>=32:continue
        for layer in ([k.F_Cu,k.B_Cu]if isinstance(t,k.PCB_VIA)else[t.GetLayer()]):starts.add((q,layer))
r.START_OPTIONS=sorted(starts)
plans=[r.plan('/CLR_N',((27,15.85),k.B_Cu),[((48.5,28.1),k.F_Cu)])]
k.SaveBoard(str(OUT/'CLR_CS_partial.kicad_pcb'),b)
r.START_OPTIONS=None
plans.append(r.plan('/IMU_CS',((23.5,26.175),k.B_Cu),[((45.719999,21.336),k.B_Cu)]))
dump(OUT/'CLR_CS_outer_route.json',{'routes':plans,'source_R13_unchanged':True,'inner_signal_tracks':0})
b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
(d/(name+'.kicad_pro')).write_text((oldd/(oldname+'.kicad_pro')).read_text().replace(oldname,name).replace('V1.2-H0.5-P5R6','V1.2-H0.5-P5R7'))
checks('motion','clr_cs_outer')

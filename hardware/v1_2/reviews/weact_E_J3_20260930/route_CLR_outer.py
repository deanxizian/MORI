"""R13-compliant outer-layer CLR trial, from the immutable polished checkpoint.

Move two new parallel signal corridors by 0.05 mm without moving any component
or changing copper rules; then find and review the remaining CLR connection.
"""
import route_motion_P5R7 as r
from update_native_P5R7 import *

name,d,p=paths('motion');OUT=HERE/'reports/motion'
b=k.LoadBoard(str(OUT/'polished_CLR_source.kicad_pcb'))
oldname,oldd,oldp=paths('motion','P5R6')
old=k.LoadBoard(str(oldp));original={t.m_Uuid.AsString()for t in old.GetTracks()}
for t in list(b.GetTracks()):
    if t.GetNetname()=='/CLR_N' and t.m_Uuid.AsString()not in original:
        if isinstance(t,k.PCB_VIA)or t.GetLayer()==k.F_Cu:b.Delete(t)

shifts={
 '/IMU_SCK':{(33.4,28.6):(33.35,28.55),(39.2,28.6):(39.2,28.55)},
 '/IMU_MOSI':{(34.8,28.6):(34.85,28.55),(40.8,28.6):(40.8,28.55),
               (46.228,23.171999):(46.228,23.121999)},
}
for t in b.GetTracks():
    if t.m_Uuid.AsString()in original or t.GetNetname()not in shifts:continue
    table=shifts[t.GetNetname()]
    if isinstance(t,k.PCB_VIA):
        q=xy(t.GetPosition())
        if q in table:t.SetPosition(pt(*table[q]))
        continue
    for get,setter in [(t.GetStart,t.SetStart),(t.GetEnd,t.SetEnd)]:
        q=xy(get())
        if q in table:setter(pt(*table[q]))

r.b=b;r.SEARCH_BOUNDS=(.6,69.4,.6,34.4)
starts=set();ends=set()
for t in b.GetTracks():
    if t.GetNetname()!='/CLR_N':continue
    points=[xy(t.GetStart()),xy(t.GetEnd())]
    layers=[k.F_Cu,k.B_Cu]if isinstance(t,k.PCB_VIA)else[t.GetLayer()]
    for q in points:
        for layer in layers:
            if q[0]<32:starts.add((q,layer))
            elif q[0]>=48.5:ends.add((q,layer))
starts.update([((9.91,2.26),l)for l in [k.F_Cu,k.B_Cu]])
r.START_OPTIONS=sorted(starts)
plan=r.plan('/CLR_N',((27,15.85),k.B_Cu),sorted(ends))
dump(OUT/'CLR_outer_route.json',{'route':plan,'corridor_shifts_mm':str(shifts),
 'source_R13_unchanged':True,'inner_signal_tracks':0})
b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
(d/(name+'.kicad_pro')).write_text((oldd/(oldname+'.kicad_pro')).read_text().replace(oldname,name).replace('V1.2-H0.5-P5R6','V1.2-H0.5-P5R7'))
checks('motion','clr_outer')

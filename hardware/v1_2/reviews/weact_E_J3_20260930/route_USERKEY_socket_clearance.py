"""Remove the temporary key-signal detour under the long socket housing."""
import route_motion_P5R7 as r
from update_native_P5R7 import *
from geometry_guard_P5 import Guard
name,d,p=paths('motion');OUT=HERE/'reports/motion'
source=OUT/'CS_pass_before_USERKEY.kicad_pcb'
if not source.exists():source.write_bytes(p.read_bytes())
b=k.LoadBoard(str(source));oldname,oldd,oldp=paths('motion','P5R6')
old=k.LoadBoard(str(oldp));original={t.m_Uuid.AsString()for t in old.GetTracks()}
for t in list(b.GetTracks()):
    if t.GetNetname()=='/USER_KEY_N' and t.m_Uuid.AsString()not in original:b.Delete(t)
class SocketGuard(Guard):
    def clear(self,q,layer,width=.2,is_via=False):
        for x1,y1,x2,y2 in [(5.85,.99,44.45,6.07),(5.85,28.93,44.45,34.01)]:
            if x1-width/2<=q[0]<=x2+width/2 and y1-width/2<=q[1]<=y2+width/2:return False
        return super().clear(q,layer,width,is_via)
r.Guard=SocketGuard;r.b=b;r.SEARCH_BOUNDS=(.6,69.4,.6,34.4)
starts=set();ends=set()
for t in b.GetTracks():
    if t.GetNetname()!='/USER_KEY_N':continue
    for q in [xy(t.GetStart()),xy(t.GetEnd())]:
        for layer in ([k.F_Cu,k.B_Cu]if isinstance(t,k.PCB_VIA)else[t.GetLayer()]):
            if q[0]<32:starts.add((q,layer))
            if q[0]>41:ends.add((q,layer))
r.START_OPTIONS=sorted(starts)
plan=r.plan('/USER_KEY_N',((30.581599,28.1432),k.F_Cu),sorted(ends))
dump(OUT/'USERKEY_socket_clearance_route.json',plan)
b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
(d/(name+'.kicad_pro')).write_text((oldd/(oldname+'.kicad_pro')).read_text().replace(oldname,name).replace('V1.2-H0.5-P5R6','V1.2-H0.5-P5R7'))
checks('motion','userkey_socket_clearance')

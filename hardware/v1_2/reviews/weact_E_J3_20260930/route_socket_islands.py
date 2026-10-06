"""Connect actual copper islands, including existing via layer transitions.

Do not force new paths through arbitrary old segment endpoints; this avoids
re-entering an already connected island or producing long same-net loops.
"""
import route_motion_P5R7 as r
from update_native_P5R7 import *
from geometry_guard_P5 import Guard
from close_P5 import clusters
name,d,p=paths('motion');OUT=HERE/'reports/motion'
b=k.LoadBoard(str(OUT/'long_socket_screen_source.kicad_pcb'))
remove=set(json.loads((OUT/'long_socket_routes.json').read_text())['removed'])
for t in list(b.GetTracks()):
    if t.m_Uuid.AsString()in remove:b.Delete(t)
track(b,'/+3V3',[(10.7442,7.95),(10.7442,6.65)],.2,k.B_Cu)
via(b,'/+3V3',10.7442,6.65,vd=.8,dr=.3,grid=False)
track(b,'/CURRENT_ADC_IN',[(45.0088,34.036),(44.704,34.3408),(33.4264,34.3408)],.2,k.F_Cu)
class SocketGuard(Guard):
    def clear(self,q,layer,width=.2,is_via=False):
        for x1,y1,x2,y2 in [(5.85,.99,44.45,6.07),(5.85,28.93,44.45,34.01)]:
            if x1-width/2<=q[0]<=x2+width/2 and y1-width/2<=q[1]<=y2+width/2:return False
        return super().clear(q,layer,width,is_via)
r.Guard=SocketGuard;r.b=b;r.SEARCH_BOUNDS=(.6,69.4,.6,34.4)
plans=[]
for net in ['/CHG_N','/S288_BUS','/WHEEL_ADC_IN','/CURRENT_ADC_IN']:
    cs=clusters(b,net);print(net,'initial islands',len(cs),flush=True)
    for iteration in range(3):
        cs=clusters(b,net)
        if len(cs)==1:break
        assert len(cs)==2,(net,'unexpected island count',len(cs))
        options=[[(q,l)for q,ls in group.items()for l in ls]for group in cs]
        options.sort(key=len,reverse=True)
        r.START_OPTIONS=options[0]
        plans.append(r.plan(net,options[0][0],options[1]))
        dump(OUT/'socket_island_routes.json',{'removed':sorted(remove),'routes':plans})
        k.SaveBoard(str(OUT/'socket_islands_partial.kicad_pcb'),b)
    assert len(clusters(b,net))==1,net
b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
oldname,oldd,_=paths('motion','P5R6')
(d/(name+'.kicad_pro')).write_text((oldd/(oldname+'.kicad_pro')).read_text().replace(oldname,name).replace('V1.2-H0.5-P5R6','V1.2-H0.5-P5R7'))
checks('motion','socket_islands')

"""Keep the CS route above E and outside the actual long socket housings."""
import route_motion_P5R7 as r
from update_native_P5R7 import *
from geometry_guard_P5 import Guard
name,d,p=paths('motion');OUT=HERE/'reports/motion'
source=OUT/'all_connected_before_socket_screen.kicad_pcb'
if not source.exists():source.write_bytes(p.read_bytes())
b=k.LoadBoard(str(source));oldname,oldd,oldp=paths('motion','P5R6')
old=k.LoadBoard(str(oldp));original={t.m_Uuid.AsString()for t in old.GetTracks()}
adc={'e6ec4a1c-410a-45c9-a238-c069a329bc3a','7218a609-ab55-4735-bf68-697d2d951577','24e287ff-ac11-4619-b9b2-677b02ab5bb5'}
for t in list(b.GetTracks()):
    if t.GetNetname()=='/IMU_CS' and t.m_Uuid.AsString()not in original or t.m_Uuid.AsString()in adc:b.Delete(t)
# Move one voltage-monitor signal transition 0.3mm right/up. Filter, sensing
# components, power conductors and all numbered pad functions stay unchanged.
track(b,'/BAT_ADC_IN',[(37.592,13.6144),(34.4376,16.7688)],.2,k.B_Cu)
track(b,'/BAT_ADC_IN',[(34.4376,16.7688),(34.1376,17.0688),(29.971999,17.0688)],.2,k.F_Cu)
via(b,'/BAT_ADC_IN',34.4376,16.7688,vd=.8,dr=.3,grid=False)
class SocketGuard(Guard):
    def clear(self,q,layer,width=.2,is_via=False):
        for x1,y1,x2,y2 in [(5.85,.99,44.45,6.07),(5.85,28.93,44.45,34.01)]:
            if x1-width/2<=q[0]<=x2+width/2 and y1-width/2<=q[1]<=y2+width/2:return False
        return super().clear(q,layer,width,is_via)
r.Guard=SocketGuard;r.b=b;r.SEARCH_BOUNDS=(.6,69.4,.6,34.4);r.START_OPTIONS=None
k.SaveBoard(str(OUT/'CS_above_E_source.kicad_pcb'),b)
plan=r.plan('/IMU_CS',((23.5,26.175),k.B_Cu),[((45.719999,21.336),k.B_Cu)])
dump(OUT/'CS_above_E_route.json',{'CS':plan,'ADC_transition_before_mm':[34.1376,17.0688],'ADC_transition_after_mm':[34.4376,16.7688],
 'preserved_ADC_filter_and_power_components':True,'CS_no_tracks_below_actual_A_D_housings':True,'inner_signal_tracks':0})
b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
(d/(name+'.kicad_pro')).write_text((oldd/(oldname+'.kicad_pro')).read_text().replace(oldname,name).replace('V1.2-H0.5-P5R6','V1.2-H0.5-P5R7'))
checks('motion','cs_above_E')

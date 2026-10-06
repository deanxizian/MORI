"""Apply actual A-D socket bodies to retained routes as well as new routes."""
import route_motion_P5R7 as r
from update_native_P5R7 import *
from geometry_guard_P5 import Guard
name,d,p=paths('motion');OUT=HERE/'reports/motion'
source=OUT/'long_socket_screen_source.kicad_pcb'
if not source.exists():source.write_bytes(p.read_bytes())
b=k.LoadBoard(str(source))
remove={
 '247da4e7-9505-4bca-ba00-31739a1de189','42bbbac1-6aee-4903-bf92-7be3d0c38a9c',
 '9b3e7b2e-132a-4ed5-8e15-b4833138b18e','296b38a9-f6b3-4fae-a975-4bcad7694abd','d604e7e6-e6eb-4941-a9b4-1f26b03b5a3a',
 '41a12201-a182-414f-828a-9068c202cb84','615f31ad-95fe-41eb-ae51-321e16fd07b8','caf3e5a9-156f-4342-b329-0b4a30cc6887',
 '25688b0a-822c-4a2a-950b-15cefa9bdab7','2a754c1f-7b72-43a8-bece-da72814d0fb8','503ccb93-9c62-4af4-b9f6-88f58c46fc0d',
 '3dff4447-0e62-4489-bd72-a8f797911fcb','9fbd9032-4b18-4799-a19d-dd3ff35a69be','dcc2166e-f2cc-499e-ae00-59055e0adec9',
 '08adfa26-8d12-4d4b-8a5c-611d467b9a74','b8372dc7-083a-4426-a072-e46b3f31765c','bc180061-f518-4bab-9176-181ab1605395',
 'f7f2212c-fbd8-4a0f-bd5e-64b1443c6a6f','fac26cb8-1f4e-4376-8561-46729790d06c',
}
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
r.Guard=SocketGuard;r.b=b;r.SEARCH_BOUNDS=(.6,69.4,.6,34.4);r.START_OPTIONS=None
specs=[
 ('/WHEEL_ADC_IN',((33.8328,8.128),k.B_Cu),[((62.5856,6.2992),k.F_Cu),((62.5856,6.2992),k.B_Cu)]),
 ('/S288_BUS',((31.394399,6.7056),k.F_Cu),[((48.2,.7),k.F_Cu),((51,3),k.F_Cu),((51,3),k.B_Cu)]),
 ('/CHG_N',((36.474399,7.0104),k.F_Cu),[((45.0088,3.556),k.F_Cu)]),
 ('/CURRENT_ADC_IN',((20.32,25.4),k.F_Cu),[((25.0952,34.3408),k.F_Cu)]),
]
plans=[]
for spec in specs:
    plans.append(r.plan(*spec))
    dump(OUT/'long_socket_routes.json',{'removed':sorted(remove),'routes':plans,'3V3_via_move_mm':[[10.7442,6.1468],[10.7442,6.65]],'3V3_track_width_mm':.2})
    k.SaveBoard(str(OUT/'long_socket_routing_partial.kicad_pcb'),b)
b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
oldname,oldd,_=paths('motion','P5R6')
(d/(name+'.kicad_pro')).write_text((oldd/(oldname+'.kicad_pro')).read_text().replace(oldname,name).replace('V1.2-H0.5-P5R6','V1.2-H0.5-P5R7'))
checks('motion','all_socket_bodies')

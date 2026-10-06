import pcbnew as k,json
from layout_P3 import paths,xy,pt,F,B,track
from route_local_P3 import connect
from geometry_guard_P3 import Guard
_,d,p,r=paths('motion');b=k.LoadBoard(str(p))
remove={'f1ceb1c3-cbcf-4137-9635-bc124be9ad8f','5a6f3b1c-5c4e-494c-8fdc-c9743a463851','a85cb4ff-8133-4ae3-bb31-83db8a4d4c93','71e2a2ae-6992-4d72-9b53-73e3ffa82ae0','cd34ad40-0832-4df4-8742-e38fa4d10f25'}
for t in list(b.GetTracks()):
 uid=t.m_Uuid.AsString()
 if uid in remove:b.Delete(t)
 elif uid=='3deae37d-7565-4fd3-8bfa-d86d23b28af0':t.SetPosition(pt(52.2989,31.4923))
 elif uid=='42de83e4-2989-49f4-8273-ce4c2c193ac7':t.SetEnd(pt(52.2989,31.4923))
 elif t.GetNetname()=='/GND' and not isinstance(t,k.PCB_VIA) and set([xy(t.GetStart()),xy(t.GetEnd())])==set([(36.775,9),(36.775,8.8)]):b.Delete(t)
k.SaveBoard(str(p),b);log=[]
for net,a,z,al,zl in [('/ARM_Q',(53.875,32.95),(52.2989,31.4923),[F],[F,B]),('/GND',(15.45,10.25),(16.225,8.5),[B],[B]),('/+3V3',(22.25,22.95),(24.25,20.225),[B],[B])]:
 log.append(connect(b,net,a,z,al,zl,(70,35),step=.025));k.SaveBoard(str(p),b)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);(r/'motion_last_repairs.json').write_text(json.dumps(log,indent=2)+'\n')

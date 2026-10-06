import pcbnew as k,json
from layout_P3 import paths,xy,pt,F,B,track,via
from geometry_guard_P3 import Guard
from route_local_P3 import connect
_,d,p,r=paths('motion');b=k.LoadBoard(str(p));ids=['47eb1d0f-aaed-4003-b1d4-2bf4d0d43655','1a9e55ad-4cda-42e8-8ffa-5600639c3224','757f38f5-4b39-4247-ba69-e5a9c28770d9','98f8288d-93ca-4d38-86be-5050d77ab8bb']
for t in list(b.GetTracks()):
 uid=t.m_Uuid.AsString()
 if uid in ids:b.Delete(t)
 elif uid=='3deae37d-7565-4fd3-8bfa-d86d23b28af0':t.SetPosition(pt(52.6667,31.4923))
 elif uid in ['42de83e4-2989-49f4-8273-ce4c2c193ac7','f1ceb1c3-cbcf-4137-9635-bc124be9ad8f']:
  v=pt(52.2989,31.4923)
  if (t.GetStart()-v).EuclideanNorm()<(t.GetEnd()-v).EuclideanNorm():t.SetStart(pt(52.6667,31.4923))
  else:t.SetEnd(pt(52.6667,31.4923))
 elif t.GetNetname()=='/GND' and not isinstance(t,k.PCB_VIA):
  v=pt(35.175,7.2)
  if t.GetStart()==v:t.SetStart(pt(35.348,7.3929))
  if t.GetEnd()==v:t.SetEnd(pt(35.348,7.3929))
g=Guard(b,'/GND');v=(16.225,7.2);assert g.via_clear(v) and g.line_clear((16.225,8.5),v,B);via(b,'GND',*v,grid=False);track(b,'GND',[(16.225,8.5),v],.2,B)
k.SaveBoard(str(p),b)
log=connect(b,'/+3V3',(17.775,8.5),(14,8.825),[B],[B],(70,35),step=.05)
for f in b.GetFootprints():
 if f.GetReference()=='C2':print('C2',[(q.GetNumber(),q.GetNetname(),xy(q.GetPosition())) for q in f.Pads()])
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);(r/'last_ground_close.json').write_text(json.dumps(log,indent=2)+'\n')

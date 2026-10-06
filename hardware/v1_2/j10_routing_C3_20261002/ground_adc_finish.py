from candidate import *
b=load();ids={'250bf3a3-098a-4448-bcfc-99a1cc58e007','2feda6c8-5fc7-43c7-9723-36f1f944b3df','4104aaa3-efc7-4861-895b-61ced7920c75','a1441abd-8e29-4869-8713-bfd60ffb3eab'}
for t in list(b.GetTracks()):
 if t.m_Uuid.AsString()in ids:b.Delete(t)
 elif t.m_Uuid.AsString()=='91c9a325-02bb-4a0f-8baa-bbb1bf79e889':t.SetWidth(mm(.6))
g=Guard(b,'/GND');p=(42.7,22);assert g.via_clear(p,.5);line=[(41.825,22),p];assert g.line_clear(*line,F,.2)
for t in list(b.GetTracks()):
 if t.m_Uuid.AsString()=='95c58c6c-841c-4756-932c-fd7538e559b3':b.Delete(t)
 elif isinstance(t,k.PCB_VIA)and math.dist(xy(t.GetPosition()),(41.4,44.8))<.001:b.Delete(t)
track(b,'/GND',line,.2,F);via(b,'/GND',*p,.5,.25,grid=False)
pts=[(39.8272,20.9296),(39.9976,21.1),(42.7,21.1),(43.7,22.1),(46.7,22.1),(46.7,21.975)]
g=Guard(b,'/BAT_ADC');bad=[]
for a,z in zip(pts,pts[1:]):
 if not g.line_clear(a,z,B,.2):bad.append((a,z))
print('BAT ADC proposed',bad,flush=True)
if not bad:track(b,'/BAT_ADC',pts,.2,B)
# Save reserved return path for a guarded signal-only continuation if needed.
save(b);dump(R/'28_ground_adc_changes.json',{'old_ADC_removed':sorted(ids),'ground_via':[42.7,22,.5,.25],'ground_via_43_561_diameter_old':.8,'ground_via_43_561_diameter_new':.6,'proposed_B_ADC':pts,'blocked_segments':bad,'pad_clusters':len(clusters(b,'/BAT_ADC'))})

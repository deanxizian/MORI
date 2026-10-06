from candidate import *
b=load();changes=[]
def replace(ids,net,l,pts,w):
 ts=[t for t in b.GetTracks()if t.m_Uuid.AsString()in ids];assert len(ts)==len(ids)
 g=Guard(b,net);bad=[(a,z)for a,z in zip(pts,pts[1:])if not g.line_clear(a,z,l,w)];print(net,'blocked',bad,flush=True);assert not bad
 before=len(clusters(b,net))
 for t in ts:b.Delete(t)
 track(b,net,pts,w,l);assert len(clusters(b,net))<=before
 changes.append({'net':net,'points':pts,'width':w,'layer':b.GetLayerName(l),'removed':ids})
replace(['8e8a88f5-5a56-44f2-b30f-1f597598aec5','3ca9ca8f-997e-4a04-95bb-2da70ba36779','9264a888-e38f-4267-8c6a-59b8cff4e401'],'/+3V3',F,[(38.5,22.300001),(39.189999,22.99),(43.35,22.99),(44.5,24.14)],.2)
replace(['250bf3a3-098a-4448-bcfc-99a1cc58e007','2feda6c8-5fc7-43c7-9723-36f1f944b3df','4104aaa3-efc7-4861-895b-61ced7920c75','a1441abd-8e29-4869-8713-bfd60ffb3eab'],'/BAT_ADC',F,[(39.8272,20.9296),(39.4,21.3568),(39.4,22.6),(43.8,22.6),(45,23.8)],.2)
g=Guard(b,'/GND');p=(42.7,22);assert g.via_clear(p,.5);pts=[(41.825,22),p];assert all(g.line_clear(a,z,F,.2)for a,z in zip(pts,pts[1:]))
track(b,'/GND',pts,.2,F);via(b,'/GND',*p,.5,.25,grid=False)
for t in list(b.GetTracks()):
 if isinstance(t,k.PCB_VIA)and math.dist(xy(t.GetPosition()),(41.4,44.8))<.001:b.Delete(t)
 elif isinstance(t,k.PCB_VIA)and math.dist(xy(t.GetPosition()),p)<.001:
  t.SetFrontTentingMode(k.TENTING_MODE_TENTED);t.SetBackTentingMode(k.TENTING_MODE_TENTED)
# Old 0.5 mm ground stub overlaps the new path; remove redundant copper.
for t in list(b.GetTracks()):
 if t.m_Uuid.AsString()=='95c58c6c-841c-4756-932c-fd7538e559b3':b.Delete(t)
r=json.loads((R/'24_local_drc.json').read_text());ids={x['uuid']for v in r['violations']if v['type']=='silk_over_copper'for x in v['items']};clipped=[]
for f in b.GetFootprints():
 for s in list(f.GraphicalItems()):
  if s.m_Uuid.AsString()in ids:
   assert f.GetReference()in ['TP61','TP71']and s.GetLayer()==k.F_SilkS
   clipped.append({'ref':f.GetReference(),'uuid':s.m_Uuid.AsString()});f.Remove(s)
save(b);dump(R/'27_ground_corridor_changes.json',{'changes':changes,'R51_ground_path':pts,'via':[.5,.25],'clipped_silk':clipped});check('27_ground');snapshot('27_ground')

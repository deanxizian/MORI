from candidate import *
b=load();ids={'ef7872fe-8762-49db-956b-d2f7217c80c6'}
# Identify the only horizontal companion ending at (45,24.5).
for t in b.GetTracks():
 if t.GetNetname()=='/BAT_ADC'and not isinstance(t,k.PCB_VIA)and set([xy(t.GetStart()),xy(t.GetEnd())])=={(46.2,24.5),(45,24.5)}:ids.add(t.m_Uuid.AsString())
assert len(ids)==2
p=[(46.7,24.5),(45,24.5)];assert Guard(b,'/BAT_ADC').line_clear(*p,F,.2)
for t in list(b.GetTracks()):
 if t.m_Uuid.AsString()in ids|{'0dbd8609-e3eb-4174-a183-88689afe4803'}:b.Delete(t)
track(b,'/BAT_ADC',p,.2,F);assert len(clusters(b,'/BAT_ADC'))==1
r=json.loads((R/'29_adc_drc.json').read_text());ids={x['uuid']for v in r['violations']if v['type']=='silk_over_copper'for x in v['items']};clipped=[];retain=[]
for f in b.GetFootprints():
 for s in list(f.GraphicalItems()):
  if s.m_Uuid.AsString()in ids:
   assert f.GetReference()in ['TP61','TP71']and s.GetLayer()==k.F_SilkS
   clipped.append({'ref':f.GetReference(),'uuid':s.m_Uuid.AsString()});retain.append(s);f.Remove(s)
for t in b.GetTracks():
 if isinstance(t,k.PCB_VIA)and math.dist(xy(t.GetPosition()),(42.7,22))<.001:
  t.SetFrontTentingMode(k.TENTING_MODE_TENTED);t.SetBackTentingMode(k.TENTING_MODE_TENTED)
save(b);dump(R/'30_cleanup_actions.json',{'BAT_ADC_join':p,'clipped_silk':clipped});check('30_clean');snapshot('30_clean')

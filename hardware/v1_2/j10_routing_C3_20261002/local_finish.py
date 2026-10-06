from candidate import *
import time
b=load();actions=[]
ids={'16da647a-7fea-4766-a8ed-acb2c425c600','4f8775c8-6053-47f5-aae2-3965628ed19a','91b6ecc1-1c90-4041-b547-bd60426418c1','5b0e346d-00d1-4cc5-90c9-7a8fa76a48d0','a9926548-29be-49c9-8d2d-a4980f2c0b39','16332e96-3029-4fb6-8360-01a8c1881267'}
pts=[(45.9,19.8),(45.5,20.2),(44.675,20.2),(44.675,21)]
g=Guard(b,'/WHEEL_ADC');assert all(g.line_clear(a,z,F,.2)for a,z in zip(pts,pts[1:]))
for t in list(b.GetTracks()):
 if t.m_Uuid.AsString() in ids:b.Delete(t)
track(b,'/WHEEL_ADC',pts,.2,F);assert len(clusters(b,'/WHEEL_ADC'))==1
for t in list(b.GetTracks()):
 if t.m_Uuid.AsString()=='46c2fb03-4b2a-4491-be7c-ead96a3732d9':b.Delete(t)
assert len(clusters(b,'/CURRENT_ADC'))==1
# Ground stitch into the actual remaining ground polygon; no zone deletion.
g=Guard(b,'/GND');assert g.via_clear((41.4,44.8),.5)
via(b,'/GND',41.4,44.8,.5,.25,grid=False)
# Cover new small signal/ground vias in solder mask. This changes no copper.
source=k.LoadBoard(str(SD/(OLD+'.kicad_pcb')));oldids={t.m_Uuid.AsString()for t in source.GetTracks()}
for t in b.GetTracks():
 if isinstance(t,k.PCB_VIA) and t.m_Uuid.AsString()not in oldids and k.ToMM(t.GetDrillValue())<=.30001:
  t.SetFrontTentingMode(k.TENTING_MODE_TENTED);t.SetBackTentingMode(k.TENTING_MODE_TENTED)
  actions.append({'action':'tent_new_small_via','uuid':t.m_Uuid.AsString(),'net':t.GetNetname(),'xy':xy(t.GetPosition()),'drill':k.ToMM(t.GetDrillValue())})
for x in b.GetDrawings():
 if isinstance(x,k.PCB_TEXT)and x.GetText()=='TP71 GND':
  x.SetPosition(pt(24,34));actions.append({'action':'relocate_stale_TP71_label','position':[24,34],'layer':'B.Silkscreen'})
save(b);dump(R/'24_local_actions.json',actions)
check('24_local');snapshot('24_local')

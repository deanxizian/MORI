"""Explicit local copper cleanups; guarded and logged, candidate only."""
from candidate import *
import time
b=load();log=[]
def replace(ids,net,l,points,w=.2):
    ts=[t for t in b.GetTracks() if t.m_Uuid.AsString() in ids]
    if len(ts)!=len(ids):return
    g=Guard(b,net)
    if not all(g.line_clear(a,z,l,w) for a,z in zip(points,points[1:])):
        print('BLOCKED',net,points,flush=True);return
    old=[{'uuid':t.m_Uuid.AsString(),'start':xy(t.GetStart()),'end':xy(t.GetEnd())} for t in ts]
    before=len(clusters(b,net))
    for t in ts:b.Delete(t)
    added=track(b,net,points,w,l)
    assert len(clusters(b,net))<=before,(net,points)
    log.append({'net':net,'layer':b.GetLayerName(l),'old':old,'new':points,'width':w})
    print('changed',net,points,flush=True)
replace(['02df78e8-382b-49f6-81b1-2de508970f91','b08bfef3-8cbb-4777-8b4b-cb3156ab141b','29927453-eb40-4dd4-a0a4-a5348309f959'], '/CHG_N',B,[(5,37.5),(2.953552,35.453552),(2.953552,35.246447)])
replace(['238bf8d4-e2d7-46c1-8827-7395f7f1bba6','6e5de95c-0bed-40c2-8d91-ea1544acb99d','60f6f00d-8111-4c35-8adf-c0c4cbdbcd6c','8a58ab16-693e-4f56-abb8-2cfda5f9020e'], '/CHG_N',B,[(11.9888,40.3352),(11.4,39.7464),(11.4,35.3)])
replace(['02d345c9-02cc-495c-a0dc-92cf16dcae3e'], '/ARM_Q',B,[(47.3,43.7),(47.3,44.4),(48,44.4)])
replace(['2d15622a-1975-4578-a09e-1ff90c695200','df2771d1-92b3-45ad-9a43-bd0922bdb55c','b9c8f698-2903-4751-9787-68c1c1820302'], '/FAULT_N',B,[(56.6928,27.1272),(56.6928,30.2)])
replace(['17cb0571-1dc8-4124-bbb3-2ec2b609063c','99372acd-375a-4b83-b94e-cf139fdece7b'], '/FAULT_N',B,[(59.5376,24.2824),(59.5376,30.2)])
replace(['16da647a-7fea-4766-a8ed-acb2c425c600','4f8775c8-6053-47f5-aae2-3965628ed19a','91b6ecc1-1c90-4041-b547-bd60426418c1'], '/WHEEL_ADC',F,[(45.9,19.8),(45.9,20.14),(44.907199,21.1328)])
save(b);dump(R/('finish_copper_'+str(time.time_ns())+'.json'),log)

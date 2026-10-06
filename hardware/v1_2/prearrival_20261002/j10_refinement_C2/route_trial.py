"""Native-shape guarded candidate routing; no rule changes or exclusions."""
from candidate import *
import close_P5 as c
def paths(kind):return NAME,D,PCB,R
c.paths=paths
original=c.connect
def bounded(*args,**kw):
 kw.update(step=.2032,time_limit=5,max_nodes=70000)
 return original(*args,**kw)
c.connect=bounded
def clean(label):
 j=json.loads((R/(label+'_drc.json')).read_text());b=load()
 ids={i['uuid']for v in j['violations']if v['type']not in ['starved_thermal','silk_over_copper','silk_overlap','courtyards_overlap']for i in v['items']}
 removed=[]
 for t in list(b.GetTracks()):
  if t.m_Uuid.AsString()in ids:removed.append(dict(uuid=t.m_Uuid.AsString(),net=t.GetNetname()));b.Delete(t)
 save(b);dump(R/(label+'_copper_removed.json'),removed)
def route():
 b=load();bulk=[(f.GetReference(),p.GetNumber())for f in b.GetFootprints()for p in f.Pads()if p.GetNetname()=='/BAT_MON'and f.GetReference()!='R50']
 c.run('power',['BAT_MON'],targets={'/BAT_MON':bulk})
 c.run('power',['BAT_MON'],targets={'/BAT_MON':[('R50','1'),('F60','1')]},widths={'/BAT_MON':.2})
 c.run('power',['H6_IN','H_PRE','C5_VIN','+5V_CAM','C5_EN','ARM_Q','BAT_ADC','WHEEL_ADC'])
 check('03_routes')
if __name__=='__main__':
 if sys.argv[1]=='clean':clean(sys.argv[2])
 elif sys.argv[1]=='route':route()

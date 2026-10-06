"""Remove obsolete signal copper only, preserving all pad-to-pad connectivity."""
from candidate import *
NETS={'/ARM_Q','/FAULT_N','/CHG_N','/BAT_ADC','/WHEEL_ADC','/CURRENT_ADC','/+5V_CAM','/M5_EN','/C5_EN'}
def orphan_islands(b):
    c=connected(b);actual={t.m_Uuid.AsString():t for t in b.GetTracks()}
    actual.update({p.m_Uuid.AsString():p for f in b.GetFootprints()for p in f.Pads()})
    todo={t.m_Uuid.AsString():t for t in b.GetTracks()if t.GetNetname()in NETS};removed=[]
    while todo:
        _,t=next(iter(todo.items()));seen={};queue=[t]
        while queue:
            t=queue.pop();uid=t.m_Uuid.AsString()
            if uid in seen:continue
            seen[uid]=actual.get(uid,t)
            queue.extend(c.GetConnectedTracks(t));queue.extend(c.GetConnectedPads(t))
        for uid in seen:todo.pop(uid,None)
        if not any(isinstance(t,k.PAD)for t in seen.values()):
            for uid,t in seen.items():
                if isinstance(t,k.PCB_TRACK):removed.append({'uuid':uid,'net':t.GetNetname(),'reason':'isolated copper component has no physical pad'});b.Delete(t)
    return removed
def run(report=None):
    b=load();before={n:len(clusters(b,n))for n in NETS};removed=orphan_islands(b)
    if report:
        j=json.loads((R/(report+'_drc.json')).read_text())
        ids={x['uuid']:v['type']for v in j['violations']if v['type']in ['via_dangling','track_dangling']for x in v['items']}
        for t in list(b.GetTracks()):
            uid=t.m_Uuid.AsString();net=t.GetNetname()
            if uid in ids and net in NETS and before[net]==1:
                removed.append({'uuid':uid,'net':net,'reason':ids[uid]});b.Delete(t)
    after={n:len(clusters(b,n))for n in NETS}
    assert all(after[n]<=before[n]for n in NETS),(before,after)
    save(b);dump(R/('pruned_'+str(__import__('time').time_ns())+'.json'),{'before_pad_islands':before,'after_pad_islands':after,'removed':removed})
    print('pruned',len(removed),flush=True)
if __name__=='__main__':run(sys.argv[1]if len(sys.argv)>1 else None)

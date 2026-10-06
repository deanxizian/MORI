"""Measure local changes from native geometry; no electrical/thermal measurements."""
from review_P5R6 import *
import heapq

def pads(b,ref,pin):return next(p for f in b.GetFootprints() if f.GetReference()==ref for p in f.Pads() if p.GetNumber()==str(pin))
def route_distance(b,net,start,end):
    tracks=[t for t in b.GetTracks() if not isinstance(t,k.PCB_VIA) and t.GetNetname()==net]
    vv=[v for v in b.GetTracks() if isinstance(v,k.PCB_VIA) and v.GetNetname()==net]
    nodes=set()
    key=lambda p,l:(round(p[0],6),round(p[1],6),l)
    for t in tracks:
        for point in [xy(t.GetStart()),xy(t.GetEnd())]:nodes.add(key(point,t.GetLayer()))
    for v in vv:
        for layer in [F,B]:nodes.add(key(xy(v.GetPosition()),layer))
    graph={q:[] for q in nodes}
    def edge(a,z,w):graph.setdefault(a,[]).append((z,w));graph.setdefault(z,[]).append((a,w))
    def project(point,a,z):
        dd=sum((y-x)**2 for x,y in zip(a,z));f=max(0,min(1,sum((x-y)*(t-y) for x,y,t in zip(point,a,z))/dd)) if dd else 0
        q=tuple(x+f*(y-x) for x,y in zip(a,z));return f,q
    for t in tracks:
        a,z=xy(t.GetStart()),xy(t.GetEnd());layer=t.GetLayer();points=[]
        for node in nodes:
            if node[2]!=layer:continue
            f,q=project(node[:2],a,z)
            if math.dist(q,node[:2])<.000002:points.append((f,node))
        points.sort()
        for (_,u),(_,v) in zip(points,points[1:]):edge(u,v,math.dist(u[:2],v[:2]))
    for v in vv:edge(key(xy(v.GetPosition()),F),key(xy(v.GetPosition()),B),0)
    src,dst=('START',),('END',)
    for name,p in [(src,pads(b,*start)),(dst,pads(b,*end))]:
        graph[name]=[]
        for node in nodes:
            if p.IsOnLayer(node[2]) and p.HitTest(pt(*node[:2])):edge(name,node,0)
        assert graph[name],(name,start,end)
    dist={src:0};queue=[(0,0,src)];count=0
    while queue:
        cost,_,node=heapq.heappop(queue)
        if cost!=dist[node]:continue
        if node==dst:return cost
        for target,delta in graph[node]:
            nc=cost+delta
            if nc<dist.get(target,float('inf')):
                count+=1;dist[target]=nc;heapq.heappush(queue,(nc,count,target))
    raise AssertionError((net,start,end,'path missing'))

n,d,p,r=paths('power');new=k.LoadBoard(str(p));old=k.LoadBoard(str(source('power')[2]));loops=[]
for num,pre in [(60,'M5'),(70,'C5')]:
    row={'IC':f'U{num}','bootstrap_capacitor':f'C{num+2}'}
    for phase,b in [('before',old),('after',new)]:
        row[phase]={name:route_distance(b,'/'+pre+'_'+name,(f'U{num}',pin),(f'C{num+2}',cp)) for name,pin,cp in [('BOOT',6,1),('SW',2,2)]}
        row[phase]['trace_sum_mm']=sum(row[phase].values())
    assert row['after']['trace_sum_mm']<row['before']['trace_sum_mm']
    loops.append(row)
banks=[('/M5_SW',[(24.4,25.6),(24.4,26.5)],'U60'),('/M5_SW',[(21.5,24),(22.4,24)],'L60'),('/C5_SW',[(23.65,39.6),(23.65,40.5)],'U70'),('/C5_SW',[(21.5,38),(22.4,38)],'L70')]
rows=[]
for net,points,ref in banks:
    entries=[]
    for point in points:
        v=next(t for t in new.GetTracks() if isinstance(t,k.PCB_VIA) and t.GetNetname()==net and math.dist(xy(t.GetPosition()),point)<1e-6)
        contacts={}
        for layer in [F,B]:
            contacts[new.GetLayerName(layer)]=[t.m_Uuid.AsString() for t in new.GetTracks() if not isinstance(t,k.PCB_VIA) and t.GetNetname()==net and t.GetLayer()==layer and t.GetEffectiveShape(layer).Collide(v.GetEffectiveShape(layer),0)]
            assert contacts[new.GetLayerName(layer)]
        assert abs(k.ToMM(v.GetWidth(F))-.8)<1e-6 and abs(k.ToMM(v.GetDrillValue())-.3)<1e-6
        entries.append({'xy_mm':point,'land_mm':.8,'drill_mm':.3,'explicit_copper_contacts':contacts})
    rows.append({'net':net,'adjacent_component':ref,'vias':entries,'native_geometric_contacts':'PASS','uniform_current_sharing':'NOT_TESTED'})

def netgeo(b,net):
    return sorted((b.GetLayerName(t.GetLayer()),tuple(sorted([xy(t.GetStart()),xy(t.GetEnd())])),round(k.ToMM(t.GetWidth(F) if isinstance(t,k.PCB_VIA) else t.GetWidth()),6)) for t in b.GetTracks() if t.GetNetname()==net)
unchanged={net:netgeo(new,net)==netgeo(old,net) for net in ['/GND','/M5_FB','/C5_FB','/M5_VIN','/C5_VIN']}
assert all(unchanged.values())
dump(r/'bootstrap_and_SW_banks.json',{'pcb_sha256':sha(p),'status':'PASS','method':'Shortest native endpoint-centreline route, including T nodes and pad area contacts. Complete track segments are counted, including portions within pads; extra pad-centre-to-entry links and via barrels are excluded. See reviews/P5R6_and_width_external_20260925/evidence/bootstrap_length_definitions.json for both endpoint and pad-centre metrics. Sum is a trace-length indicator, not loop inductance or oscilloscope evidence.','bootstrap_trace_lengths_mm':loops,'SW_banks':rows,'unchanged_copper_geometry':unchanged,'bench':'NOT_TESTED'})

n,d,p,r=paths('motion');b=k.LoadBoard(str(p));rows=[]
for ref in ['D1','D2','D3']:
    f=next(f for f in b.GetFootprints() if f.GetReference()==ref)
    pp=list(f.Pads());assert len(pp)==2
    row={'ref':ref,'footprint':f.GetFPIDAsString(),'side':'B' if f.IsFlipped() else 'F','pads':[]}
    for pd in pp:
        size=xy(pd.GetSize());margin=k.ToMM(pd.GetLocalSolderPasteMargin());ratio=pd.GetLocalSolderPasteMarginRatio()
        assert size==(1.2,1.2) and abs(margin+.05)<1e-6 and ratio==0
        row['pads'].append({'pin':pd.GetNumber(),'net':pd.GetNetname(),'copper_mm':size,'paste_mm':[round(v+2*margin,5) for v in size],'local_paste_margin_mm':margin,'local_paste_ratio':ratio})
    pitch=math.dist(xy(pp[0].GetPosition()),xy(pp[1].GetPosition()));assert abs(pitch-2.8)<1e-6
    row['pad_pitch_mm']=pitch;rows.append(row)
dump(r/'diode_final_native_evidence.json',{'pcb_sha256':sha(p),'status':'PASS','pads':rows,'vendor_source':'Nexperia BAT54H 2024-10-08 soldering land pattern, p5 Figure 5. Mask inherits project; no exact vendor mask/physical soldering qualification.','physical_assembly':'NOT_TESTED'})
print(json.dumps(loops,indent=2))

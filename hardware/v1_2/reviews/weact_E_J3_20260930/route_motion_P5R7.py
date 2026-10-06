"""Scoped octilinear routing around corrected E socket. No original files changed."""
from update_native_P5R7 import *
import math, heapq, itertools
from geometry_guard_P5 import Guard
from body_keepouts_P3R1 import rectangle

OUT=HERE/'reports/motion'
name,d,p=paths('motion')
source=OUT/'initial_routing_source.kicad_pcb'
if not source.exists():source.write_bytes(p.read_bytes())
b=k.LoadBoard(str(source))

# Keep the remaining branches to external connectors; replace only local paths.
remove={
 '/ARM_Q':{'2ebd696d-2250-4fbc-b686-d601755a8b02','cde4911c-37c6-4e68-be4a-882d3b163c08'},
 '/CLR_N':{'eaef1451-6fe0-4a20-9739-75bc7fddaa9b','bbc4c95b-a178-4135-b99e-8f03756009c9','ea47a6d7-66c6-4784-b3cf-0c864972dbd0','3eec43a8-7ccb-43b9-ab91-9afb180a5301','fdcd0f53-8670-481f-9c5f-722ec8d1c106'},
 '/USER_KEY_N':{'836a810b-ef7d-4769-86d3-024572c08a8e','bf8d9372-a6cc-424e-9de0-25a4233be876','dad5474f-b6ea-4432-878d-0a1023a2510a'},
 '/IMU_CS':{'3cdd5802-eef3-4c24-ab60-1d48657019c9','933e6e95-5f06-4118-aafa-de3797952e9e','bd617cac-9ffe-408a-a0cc-10c773e1afaf','d3253679-d98e-485b-883a-2764ea339573','d3d91877-92ff-416d-a7e2-b546eb677e38','67d9c0ae-263b-4603-b583-d9d2558b4f6e','948bcb4b-036a-42bf-910d-2338ab675b1f','58c2ec79-11f1-49ff-9da7-de81cea8798e','eb50dafe-3254-4617-a5ce-e0767e079f36','ed444f85-46d4-4f91-83fc-1e3d44669d9f'},
 '/IMU_SCK':{'5f081839-49fd-467b-8063-5fab2a6dda43','6519d986-ec3a-4bbf-af77-ff3faa2f8694','8aab47c5-9f37-4929-895b-123727284c27','d144c7f2-16cb-444a-b4e7-d986be50373d','db98c9d1-f437-4a33-a546-f70da16a6841','ebd10c8d-537e-43c5-bb1c-f94955da74e4','7968d57b-044a-4642-9fb0-cd3ea7f67d22','a3627708-f8c0-48e6-8cae-64d9b23f2e5c','2342d92e-dc8c-4ca8-b6e6-893724611a3c','aa129814-137f-4525-a47b-023a548ad910'},
 '/IMU_MOSI':{'0d3f6c1c-3090-401d-9832-a21e40aa1f98','2a41ac5f-89ef-4888-9aff-14236c68d569','399e1501-371e-4eb6-9976-2d6e1a742b99','4088977c-1173-411c-a4c5-760bc1f1ec76','8ca976db-460c-454b-a036-b9047a2d23da','920782fd-6617-4c74-95c5-339765d3e481','9da9f88c-cddd-4dfe-8913-9e7ba5c23515','c84dfc9a-3460-46ef-a4cc-7d3fc60fb981','36e120a6-218d-4540-9147-67fdc31514e2'},
}
removed=[]
stitches={'3393ec02-1220-432d-a3a5-a2992f208223','91e02d90-fe4e-4c77-946f-6fdc70340b3d'}
for t in list(b.GetTracks()):
    if t.GetNetname() in ['/NRST','/ARM_FEEDBACK'] or t.m_Uuid.AsString() in remove.get(t.GetNetname(),set()) or t.m_Uuid.AsString()in stitches:
        removed.append({'uuid':t.m_Uuid.AsString(),'net':t.GetNetname()});b.Delete(t)

E_RECT=[33.66,17.76,38.74,28.42]
resistor=next(f for f in b.GetFootprints() if f.GetReference()=='R19')
resistor.Move(pt(0,-1.5))
for zone in b.Zones():
    if zone.GetZoneName() in [prefix+'R19'+suffix for prefix in ['BODY_','NETBODY_','VIA_BODY_']for suffix in ['','_OPPOSITE']]:
        zone.Move(pt(0,-1.5))
track(b,'/ARM_Q',[(29.6592,15.138399),(30.6,14.197599),(30.6,13.5),(33.1088,13.5),(33.9344,14.3256)],.2,k.B_Cu)
for layer in [k.F_Cu,k.B_Cu]:
    # Only the connected E7 own-pad normal escape has a narrow corridor.
    shape=rectangle(E_RECT);shape.BooleanSubtract(rectangle([33.65,26.6,35.8,27.2]))
    zone=k.ZONE(b);zone.SetIsRuleArea(True);zone.SetLayer(layer)
    zone.SetZoneName('P5R7_E_SOCKET_'+b.GetLayerName(layer))
    zone.SetDoNotAllowTracks(True);zone.SetDoNotAllowVias(True);zone.SetDoNotAllowPads(False)
    zone.SetDoNotAllowFootprints(False);zone.SetDoNotAllowZoneFills(False)
    zone.Outline().BooleanAdd(shape);b.Add(zone)

F,B=k.F_Cu,k.B_Cu
DIR=[(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1),(0,-1),(1,-1)]
step=.1
GRID_OFFSET=(0,0)
SEARCH_BOUNDS=(20,49,10,34.4)
START_OPTIONS=None
def routes2(a,z):
    dx,dy=z[0]-a[0],z[1]-a[1];m=min(abs(dx),abs(dy))
    sx=1 if dx>=0 else -1;sy=1 if dy>=0 else -1
    for mid in [(a[0]+sx*m,a[1]+sy*m),(z[0]-sx*m,z[1]-sy*m),(a[0],z[1]),(z[0],a[1])]:
        out=[a]
        for q in [mid,z]:
            if math.dist(out[-1],q)>1e-6:out.append(q)
        yield out

def smooth(route,g,layer):
    # Visibility shortcut using straight/45-degree paths only, no sub-0.25mm jogs.
    out=[route[0]];i=0
    while i<len(route)-1:
        best=None
        for j in range(len(route)-1,i,-1):
            candidates=[]
            for candidate in routes2(route[i],route[j]):
                if len(candidate)>2 and min(math.dist(a,z) for a,z in zip(candidate,candidate[1:]))<.25:continue
                if all(g.line_clear(a,z,layer)for a,z in zip(candidate,candidate[1:])):
                    candidates.append((sum(math.dist(a,z)for a,z in zip(candidate,candidate[1:]))+.65*(len(candidate)-2),candidate))
            if candidates:best=(j,min(candidates)[1]);break
        assert best
        i,seg=best;out+=seg[1:]
    # Remove collinear intermediate vertices.
    ans=[]
    for q in out:
        while len(ans)>1:
            a,z=ans[-2:];u=(z[0]-a[0],z[1]-a[1]);v=(q[0]-z[0],q[1]-z[1])
            if abs(u[0]*v[1]-u[1]*v[0])<1e-7 and u[0]*v[0]+u[1]*v[1]>0:ans.pop()
            else:break
        ans.append(q)
    return ans

def plan(net,start,ends):
    g=Guard(b,net)
    # Do not use the NRST socket slot for an unrelated signal.
    old_clear=g.clear
    def clear(q,layer,width=.2,is_via=False):
        if net!='/NRST' and E_RECT[0]-width/2<=q[0]<=E_RECT[2]+width/2 and E_RECT[1]-width/2<=q[1]<=E_RECT[3]+width/2:return False
        return old_clear(q,layer,width,is_via)
    g.clear=clear
    a,l0=start;targets={};starts={}
    def nearby(point,layer):
        points=[]
        for ix in range(round((point[0]-GRID_OFFSET[0])/step)-5,round((point[0]-GRID_OFFSET[0])/step)+6):
            for iy in range(round((point[1]-GRID_OFFSET[1])/step)-5,round((point[1]-GRID_OFFSET[1])/step)+6):
                q=(round(ix*step+GRID_OFFSET[0],6),round(iy*step+GRID_OFFSET[1],6))
                if not g.clear(q,layer):continue
                for r in routes2(point,q):
                    if len(r)>2 and min(math.dist(u,v)for u,v in zip(r,r[1:]))<.25:continue
                    if all(g.line_clear(u,v,layer)for u,v in zip(r,r[1:])):
                        points.append(((ix,iy,layer),r,sum(math.dist(u,v)for u,v in zip(r,r[1:]))));break
        return points
    for start_point,start_layer in (START_OPTIONS or [start]):
        for state,r,cost in nearby(start_point,start_layer):
            if state not in starts or cost<starts[state][1]:starts[state]=(r,cost)
    for z,layer in ends:
        for state,r,cost in nearby(z,layer):
            if state not in targets or cost<targets[state][1]:targets[state]=(list(reversed(r)),cost)
    assert starts and targets,(net,len(starts),len(targets))
    def point(state):return (round(state[0]*step+GRID_OFFSET[0],6),round(state[1]*step+GRID_OFFSET[1],6))
    def heuristic(s):return min(math.dist(point(s),z)+(0 if s[2]==l else 3)for z,l in ends)
    pq=[];costs={};parents={};serial=itertools.count();sourcepaths={}
    for state,(r,c) in starts.items():
        v=state+(-1,);costs[v]=c;sourcepaths[v]=r;parents[v]=None
        heapq.heappush(pq,(c+heuristic(v),next(serial),v,c))
    cache={};vcache={}
    def edge_clear(s,v):
        key=(s[:3],v[:3])
        if key not in cache:
            cache[key]=g.line_clear(point(s),point(v),s[2])
        return cache[key]
    end=None;visited=0
    while pq:
        _,_,s,c=heapq.heappop(pq)
        if c!=costs[s]:continue
        visited+=1
        if s[:3] in targets:end=s;break
        options=[]
        for direction,(dx,dy)in enumerate(DIR):
            v=(s[0]+dx,s[1]+dy,s[2],direction)
            if not (SEARCH_BOUNDS[0]<=v[0]*step+GRID_OFFSET[0]<=SEARCH_BOUNDS[1] and SEARCH_BOUNDS[2]<=v[1]*step+GRID_OFFSET[1]<=SEARCH_BOUNDS[3]):continue
            if s[3]>=0 and (direction-s[3])%8 in [3,4,5]:continue
            if edge_clear(s,v):options.append((v,step*math.hypot(dx,dy)+(0 if s[3]in[-1,direction]else .8)))
        if s[:2]not in vcache:vcache[s[:2]]=g.via_clear(point(s),.8)
        if vcache[s[:2]]:options.append(((s[0],s[1],B if s[2]==F else F,-1),5.0))
        for v,delta in options:
            nc=c+delta
            if nc>=costs.get(v,float('inf')):continue
            costs[v]=nc;parents[v]=s;heapq.heappush(pq,(nc+heuristic(v),next(serial),v,nc))
    if not end:
        print('NO PATH DIAGNOSTIC',net,'start',list(starts)[:10], 'target',list(targets)[:10],
              'closest',sorted((heuristic(s),s)for s in costs)[:8],flush=True)
    assert end,(net,'no path',visited)
    seq=[];s=end
    while parents[s] is not None:seq.append(s);s=parents[s]
    seq.append(s);seq.reverse()
    runs=[(s[2],sourcepaths[s][:])];vias=[]
    for state in seq[1:]:
        q=point(state)
        if state[2]!=runs[-1][0]:
            vias.append(q);runs.append((state[2],[q]))
        else:runs[-1][1].append(q)
    runs[-1][1].extend(targets[end[:3]][0][1:])
    result=[]
    for layer,r in runs:
        clean=smooth(r,g,layer)
        if len(clean)>1:track(b,net,clean,.2,layer)
        result.append({'layer':b.GetLayerName(layer),'points':clean})
    for x,y in vias:via(b,net,x,y,vd=.8,dr=.3,grid=False)
    print(net,visited,result,'vias',vias,flush=True)
    return {'net':net,'runs':result,'vias':vias,'width_mm':.2}

specs=[
 ('/CLR_N',((31.496,17.779999),B),[((48.5,28.1),F)]),
 ('/NRST',((30,22.4),B),[((33.2,26.9),B),((33.2,26.9),F)]),
 ('/ARM_FEEDBACK',((33,15.325),B),[((30.23,30.2),B),((30.23,30.2),F)]),
 ('/USER_KEY_N',((30.581599,28.1432),F),[((42.5704,28.1432),B)]),
 ('/IMU_SCK',((27.325,27),B),[((41.147999,22.6568),B)]),
 ('/IMU_MOSI',((29.5,26.175),B),[((46.228,21.843999),B),((46.228,21.843999),F)]),
 ('/IMU_CS',((23.5,26.175),B),[((45.5,21.336),B)]),
]
def run_all():
    plans=[]
    priority=['/ARM_FEEDBACK','/NRST','/CLR_N','/IMU_SCK','/IMU_MOSI','/IMU_CS','/USER_KEY_N']
    specs.sort(key=lambda s:priority.index(s[0]))
    for spec in specs:
        result=plan(*spec)
        if spec[0]=='/NRST':
            layer=F if result['runs'][-1]['layer']=='F.Cu' else B
            track(b,'/NRST',[(33.2,26.9),(34.93,26.9)],.2,layer)
            result['runs'][-1]['points'].append((34.93,26.9))
        plans.append(result)
        dump(OUT/'route_plan.json',{'removed':removed,'routes':plans,'E_socket_body_mm':E_RECT})
        k.SaveBoard(str(OUT/'routing_progress.kicad_pcb'),b)
    relocated=[]
    for original in [(35.5,17),(36.5,29)]:
        guard=Guard(b,'/GND');options=[]
        for i in range(-25,26):
            for j in range(-25,26):
                q=(round(original[0]+i*.2,4),round(original[1]+j*.2,4))
                if E_RECT[0]-.8<q[0]<E_RECT[2]+.8 and E_RECT[1]-.8<q[1]<E_RECT[3]+.8:continue
                if 15<q[1]<29.5 and guard.via_clear(q,.8):options.append((math.dist(q,original),q))
        assert options
        distance,q=min(options);via(b,'/GND',*q,vd=.8,dr=.3,grid=False)
        relocated.append({'from':original,'to':q,'distance_mm':distance,'purpose':'Relocated free GND plane stitching, not a capacitor return or series ground connection'})
    dump(OUT/'route_plan.json',{'removed':removed,'routes':plans,'E_socket_body_mm':E_RECT,'ground_stitch_relocation':relocated})
    b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
    for lib in d.rglob('*.kicad_sym'):
        text=lib.read_text();text=text.replace('MORI_Custom:WeAct_F4_64Pin_V11"','MORI_Custom:WeAct_F4_64Pin_V11_ECorrected_P5R7"');lib.write_text(text)
    checks('motion','routed')

if __name__ == "__main__":
    run_all()

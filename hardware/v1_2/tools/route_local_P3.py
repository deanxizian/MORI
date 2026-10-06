"""Small native-shape-aware routing repair; every result requires KiCad DRC.

This is geometry assistance, not a replacement for the project rule checker.
"""
import math,heapq,time
from collections import defaultdict
import pcbnew as k
from detail_P2 import track

mm=k.FromMM;pt=lambda x,y:k.VECTOR2I(mm(x),mm(y))

def connect(b,netname,start,goal,start_layers,goal_layers,size,step=.05,width=.2,vd=.8,dr=.3):
    net=b.GetNetsByName()[netname];code=net.GetNetCode();W,H=size
    buckets=defaultdict(list);items=[];own_vias=[]
    def add(shape,layer,pad,own,bbox):
        idx=len(items);items.append((shape,pad,own))
        x1,y1,x2,y2=[k.ToMM(v) for v in [bbox.GetX(),bbox.GetY(),bbox.GetRight(),bbox.GetBottom()]]
        for ix in range(math.floor((x1-1)/2),math.floor((x2+1)/2)+1):
            for iy in range(math.floor((y1-1)/2),math.floor((y2+1)/2)+1):buckets[(ix,iy,layer)].append(idx)
    for f in b.GetFootprints():
        for p in f.Pads():
            for layer in [k.F_Cu,k.B_Cu]:
                if p.IsOnLayer(layer):add(p.GetEffectiveShape(layer),layer,True,p.GetNetCode()==code,p.GetBoundingBox())
    for t in b.GetTracks():
        if t.GetNetCode()==code:
            if isinstance(t,k.PCB_VIA):own_vias.append(t)
            continue
        for layer in [k.F_Cu,k.B_Cu]:
            if t.IsOnLayer(layer):add(t.GetEffectiveShape(layer),layer,False,False,t.GetBoundingBox())
    for z in b.Zones():
        if not z.GetIsRuleArea():continue
        for layer in [k.F_Cu,k.B_Cu]:
            if z.IsOnLayer(layer):
                # Keepouts already include the required mounting clearance.
                idx=len(items);items.append((z.Outline(),False,'keepout_via' if z.GetZoneName().startswith('OUTWARD_U') and netname in ['/GND','/+3V3','/CAM_3V3'] and not z.GetDoNotAllowTracks() else 'keepout'))
                bb=z.GetBoundingBox();x1,y1,x2,y2=[k.ToMM(v) for v in [bb.GetX(),bb.GetY(),bb.GetRight(),bb.GetBottom()]]
                for ix in range(math.floor((x1-1)/2),math.floor((x2+1)/2)+1):
                    for iy in range(math.floor((y1-1)/2),math.floor((y2+1)/2)+1):buckets[(ix,iy,layer)].append(idx)
    cache={}
    def clear(x,y,l,via=False):
        key=(x,y,l,via)
        if key in cache:return cache[key]
        px,py=x*step,y*step;radius=vd/2 if via else width/2
        ok=radius+.501<px<W-radius-.501 and radius+.501<py<H-radius-.501
        if ok:
            p=pt(px,py)
            if via and any(mm(.002)<(v.GetPosition()-p).EuclideanNorm()<mm(dr/2+.152)+v.GetDrill()/2 for v in own_vias):ok=False
            for i in buckets[(math.floor(px/2),math.floor(py/2),l)]:
                shape,pad,own=items[i]
                if own is True and (not via or not pad):continue
                if own=='keepout_via' and not via:continue
                dist=radius+(.002 if own in ['keepout','keepout_via'] else .202)
                if shape.Collide(p,mm(dist)):
                    ok=False;break
        cache[key]=ok;return ok
    sx,sy=[round(x/step) for x in start];gx,gy=[round(x/step) for x in goal]
    if not any(clear(gx,gy,l) for l in goal_layers):
        raise RuntimeError(('blocked goal',netname,goal))
    def h(x,y,l):return math.hypot(x-gx,y-gy)*step
    q=[];cost={};prev={};heading={}
    for l in start_layers:
        if not clear(sx,sy,l):continue
        node=(sx,sy,l);cost[node]=0;heapq.heappush(q,(h(*node),0,node));heading[node]=None
    if not q:raise RuntimeError(('blocked start',netname,start))
    moves=[(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]
    found=None;count=0;t0=time.monotonic()
    while q:
        _,g,u=heapq.heappop(q)
        if cost.get(u)!=g:continue
        x,y,l=u;count+=1
        if (x,y)==(gx,gy) and l in goal_layers:found=u;break
        if count>650000 or time.monotonic()-t0>110:raise RuntimeError(('routing limit',netname,count))
        neigh=[]
        for dx,dy in moves:
            if not clear(x+dx,y+dy,l):continue
            # Check the midpoint too, including diagonal passage beside pads.
            if not clear(x+dx/2,y+dy/2,l):continue
            v=(x+dx,y+dy,l);d=(dx,dy)
            penalty=.35 if heading[u] is not None and heading[u]!=d else 0
            neigh.append((v,math.hypot(dx,dy)*step+penalty,d))
        other=k.B_Cu if l==k.F_Cu else k.F_Cu
        if clear(x,y,l,True) and clear(x,y,other,True):neigh.append(((x,y,other),5.0,None))
        for v,edge,d in neigh:
            ng=g+edge
            if ng+1e-8<cost.get(v,1e20):cost[v]=ng;prev[v]=u;heading[v]=d;heapq.heappush(q,(ng+h(*v),ng,v))
    if found is None:raise RuntimeError(('no route',netname,count))
    route=[found]
    while route[-1] in prev:route.append(prev[route[-1]])
    route.reverse();segments=[];a=route[0];last=a;direction=None;vias=[]
    for c in route[1:]:
        if c[2]!=last[2]:
            if a!=last:segments.append((a,last))
            if not any((v.GetPosition()-pt(c[0]*step,c[1]*step)).EuclideanNorm()<mm(.002) for v in own_vias):
                v=k.PCB_VIA(b);v.SetPosition(pt(c[0]*step,c[1]*step));v.SetWidth(mm(vd));v.SetDrill(mm(dr));v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(net);v.SetFrontTentingMode(k.TENTING_MODE_NOT_TENTED);b.Add(v);vias.append([c[0]*step,c[1]*step])
            a=c;direction=None
        else:
            d=(c[0]-last[0],c[1]-last[1])
            if direction is not None and d!=direction:
                if a!=last:segments.append((a,last))
                a=last
            direction=d
        last=c
    if a!=last:segments.append((a,last))
    for a,c in segments:track(b,net,(a[0]*step,a[1]*step),(c[0]*step,c[1]*step),width,a[2])
    print('local route',netname,'segments',len(segments),'vias',len(vias),'nodes',count,flush=True)
    return dict(net=netname,start=start,goal=goal,segments=len(segments),vias= vias)

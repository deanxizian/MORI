"""Connect P5 netlist islands through the new outward corridors.

Uses native copper connectivity and body/clearance shapes. Native DRC and
visual route review are mandatory afterwards. No rule exclusions are added.
"""
import json,sys,math,time
from collections import defaultdict
import pcbnew as k
from layout_P5 import paths,xy,pt,mm,F,B,track,via
from geometry_guard_P5 import Guard
from route_native_P5 import connect
from plane_finish_P5 import simple

def connected(b):
    # KiCad connectivity propagates a net to an isolated via from filled zones.
    # While routes are being edited the stored fills are stale; using them can
    # silently turn a newly added signal via into GND. Refill only for DRC.
    for z in b.Zones():
        if not z.GetIsRuleArea():z.UnFill()
    c=k.CONNECTIVITY_DATA();c.Build(b);c.RecalculateRatsnest();return c

def clusters(b,net,targets=None):
    c=connected(b);remaining={t.m_Uuid.AsString():t for f in b.GetFootprints() for t in f.Pads() if t.GetNetname()==net and (targets is None or (f.GetReference(),t.GetNumber()) in targets)}
    # The SWIG connectivity API returns some vias as base PCB_TRACK wrappers.
    # Resolve by UUID to the board's concrete PCB_VIA object, otherwise the
    # search sees only F.Cu at a through via and incorrectly reports no route.
    actual={t.m_Uuid.AsString():t for t in b.GetTracks()}
    actual.update({q.m_Uuid.AsString():q for f in b.GetFootprints() for q in f.Pads()})
    out=[]
    while remaining:
        uid,p=next(iter(remaining.items()));seen={};queue=[p]
        while queue:
            t=queue.pop();u=t.m_Uuid.AsString()
            if u in seen:continue
            seen[u]=t
            queue.extend(c.GetConnectedTracks(t));queue.extend(c.GetConnectedPads(t))
        items=[actual.get(u,t) for u,t in seen.items()];ids=set(seen)
        for u in ids:remaining.pop(u,None)
        pts={}
        for t in items:
            if isinstance(t,k.PAD):
                a=xy(t.GetPosition());layers=[l for l in [F,B] if t.IsOnLayer(l)]
            elif isinstance(t,k.PCB_VIA):a=xy(t.GetPosition());layers=[F,B]
            elif isinstance(t,k.PCB_TRACK):
                for a in [xy(t.GetStart()),xy(t.GetEnd())]:pts.setdefault(a,set()).add(t.GetLayer())
                continue
            else:continue
            pts.setdefault(a,set()).update(layers)
        out.append(pts)
    return out

def width_for(kind,net):
    if kind=='rear' and net in ['/VBUS_RAW','/VBUS_FUSED']:return .6
    if kind=='motion' and net=='/+5V_MOTION':return .5
    if kind=='power':
        if net in ['/PACK_FUSED','/BAT_IN','/BAT_REV','/BAT_MON']:return 2.
        if net in ['/W9_IN','/W_PRE','/W_VM']:return 1.5
        if net in ['/H6_IN','/H_PRE','/H_VM','/W_DUMP_D','/H_DUMP_D']:return 1.
        if net in ['/+5V_MOTION','/+5V_CAM','/M5_VIN','/C5_VIN']:return .8
        if net in ['/M5_SW','/C5_SW']:return .6
        if net in ['/KELVIN_N','/KELVIN_P']:return .381
    return .2

def run(kind,nets=None,targets=None,widths=None):
    name,d,p,r=paths(kind);b=k.LoadBoard(str(p));size=json.loads((d/'connectivity.json').read_text())['size'];log=[]
    if not nets:
        allnets={q.GetNetname() for f in b.GetFootprints() for q in f.Pads()}
        nets=sorted(n for n in allnets if n and n!='/GND' and not n.startswith('unconnected-') and not (kind=='motion' and n=='/+3V3'))
    for net in nets:
        if not net.startswith('/'):net='/'+net
        attempts=set();w=(widths or {}).get(net,width_for(kind,net));vd=1. if w>.6 else .8;dr=.45 if vd==1. else .3
        for iteration in range(25):
            cs=clusters(b,net,(targets or {}).get(net))
            if len(cs)<=1:break
            pairs=[]
            for i,x in enumerate(cs):
                for y in cs[i+1:]:
                    for a,als in x.items():
                        for z,zls in y.items():
                            key=(a,z)
                            if key in attempts or (math.dist(a,z)<.001 and set(als)&set(zls)):continue
                            pairs.append((math.dist(a,z),a,z,sorted(als),sorted(zls)))
            if not pairs:break
            # Multiple endpoints of the same copper island are legitimate
            # candidates; try simple, straight alternatives before search.
            done=False;g=Guard(b,net)
            for dist,a,z,als,zls in sorted(pairs)[:30]:
                for l in set(als)&set(zls):
                    for points in simple(a,z):
                        if all(g.line_clear(u,v,l,w) for u,v in zip(points,points[1:])):
                            track(b,net,points,w,l);log.append(dict(net=net,method='simple',points=points,width=w,layer=b.GetLayerName(l)));done=True;break
                    if done:break
                if done:break
            if not done:
                for dist,a,z,als,zls in sorted(pairs)[:8]:
                    attempts.add((a,z))
                    try:
                        q=connect(b,net,a,z,als,zls,size,step=.1016,width=w,vd=vd,dr=dr,time_limit=20,max_nodes=240000,heuristic_weight=2.3)
                        log.append(dict(method='corridor_search',width=w,**q));done=True;break
                    except RuntimeError as e:log.append(dict(net=net,method='search',start=a,end=z,status='BLOCKED',reason=str(e)))
            if not done:
                print(kind,net,'BLOCKED islands',len(cs),flush=True);break
            k.SaveBoard(str(p),b)
        print(kind,net,'islands',len(clusters(b,net,(targets or {}).get(net))),flush=True)
    k.SaveBoard(str(p),b)
    out=r/('native_routes_'+str(int(time.time()))+'.json');out.write_text(json.dumps(log,indent=2)+'\n')
if __name__=='__main__':run(sys.argv[1],sys.argv[2:] or None)

"""Logged, bounded native-copper routing. Placements and rules are immutable."""
from candidate import *
from route_native_P5 import connect
import time

def delete_ids(b, ids):
    removed=[]
    for t in list(b.GetTracks()):
        if t.m_Uuid.AsString()in ids:
            removed.append(t.m_Uuid.AsString());b.Delete(t)
    return removed

def guarded(b,net,points,w,l):
    g=Guard(b,net)
    for a,z in zip(points,points[1:]):
        if not g.line_clear(a,z,l,w):
            n=max(1,math.ceil(math.dist(a,z)/.04))
            for i in range(n+1):
                q=tuple(u+(v-u)*i/n for u,v in zip(a,z))
                hits=obstacles(b,net,q,l,w)
                if hits:raise RuntimeError((net,a,z,q,hits))
            raise RuntimeError((net,'guard rejected',a,z))
    track(b,net,points,w,l)

def prepare():
    b=load(); changes=[]
    # Delete obsolete orphan stub and the no-longer-needed one-layer via.
    remove=[]
    for t in b.GetTracks():
        if t.GetNetname()=='/GND'and not isinstance(t,k.PCB_VIA)and xy(t.GetStart())==(39.04,44.5):remove.append(t.m_Uuid.AsString())
        if t.GetNetname()=='/C5_VIN'and isinstance(t,k.PCB_VIA)and xy(t.GetPosition())==(30.5,41.3):remove.append(t.m_Uuid.AsString())
        if t.GetNetname()=='/BAT_MON'and not isinstance(t,k.PCB_VIA):
            if t.GetLayer()==F and xy(t.GetStart())in [(30.5,34.545),(31.1912,33.4264),(32.105599,32.512),(37.675,23.0)]:remove.append(t.m_Uuid.AsString())
            if xy(t.GetStart())==(36.8808,42.2148):remove.append(t.m_Uuid.AsString()) # disconnected orphan
    changes.append({'removed_obsolete_copper':delete_ids(b,remove)})
    # F70 now on B.Cu. Both input and output leave the physical fuse body outward.
    guarded(b,'/C5_VIN',[(30.5,39.455),(30.5,41.3)],.8,B)
    guarded(b,'/BAT_MON',[(30.5,34.545),(30.5,33.5),(31.488,32.512),(32.105599,32.512)],.8,B)
    # Q30 source bank: short outward 0.6mm individual leads, joined outside body.
    for x in [50.365,51.635,52.905]:guarded(b,'/H_PRE',[(x,31.525),(x,30.3)],.6,F)
    guarded(b,'/H_PRE',[(50.365,30.3),(52.905,30.3)],1.0,F)
    guarded(b,'/H_PRE',[(49.825,29.5),(50.8,29.5),(51.6,30.3)],.2,F)
    save(b);dump(R/'01_prepare_changes.json',changes);snapshot('01_prepared')

def solve(net,width=.2,targets=None,label='routes',time_limit=18,step=.1):
    if not net.startswith('/'):net='/'+net
    b=load();log=[]
    for iteration in range(20):
        cs=clusters(b,net,targets)
        if len(cs)<=1:break
        g=Guard(b,net);pairs=[]
        for i,aa in enumerate(cs):
            for jj,zz in enumerate(cs[i+1:],i+1):
                for a,als in aa.items():
                    for z,zls in zz.items():
                        pairs.append((math.dist(a,z),a,z,sorted(als),sorted(zls),i,jj))
        done=False
        for dist,a,z,als,zls,i,j in sorted(pairs)[:100]:
            for l in set(als)&set(zls):
                for points in simple(a,z):
                    if all(g.line_clear(u,v,l,width)for u,v in zip(points,points[1:])):
                        track(b,net,points,width,l);log.append({'method':'simple','net':net,'width':width,'points':points,'layer':b.GetLayerName(l)});done=True;break
                if done:break
            if done:break
        if not done:
            # Multi-source/goal grid search can choose a legal branch endpoint;
            # blocked nearest pad centres must not hide reachable copper islands.
            seen=set()
            for dist,a,z,als,zls,i,j in sorted(pairs):
                if (i,j)in seen:continue
                seen.add((i,j))
                before={t.m_Uuid.AsString()for t in b.GetTracks()}
                try:
                    q=connect(b,net,a,z,als,zls,[80,55],step=step,width=width,vd=1. if width>.6 else .8,dr=.45 if width>.6 else .3,time_limit=time_limit,max_nodes=300000,heuristic_weight=1.65,start_points=cs[i],goal_points=cs[j])
                    new=[t for t in b.GetTracks()if t.m_Uuid.AsString()not in before]
                    # The native search rounds to grid. Bridge true start/end
                    # coordinates using deliberate doglegs, not floating stubs.
                    for ends in [cs[i],cs[j]]:
                        hits=[]
                        for p,ls in ends.items():
                            snapped=tuple(round(v/step)*step for v in p)
                            if math.dist(p,snapped)>step:continue
                            for t in new:
                                if isinstance(t,k.PCB_VIA):continue
                                if t.GetLayer()in ls and any(math.dist(xy(v),snapped)<2e-6 for v in [t.GetStart(),t.GetEnd()]):hits.append((math.dist(p,snapped),p,snapped,t))
                        if hits:
                            _,p,s,t=min(hits,key=lambda q:q[0])
                            if math.dist(p,s)>1e-6:
                                # Extend endpoint exactly; later smoothing and
                                # DRC assess the actual native geometry.
                                if math.dist(xy(t.GetStart()),s)<2e-6:t.SetStart(pt(*p))
                                else:t.SetEnd(pt(*p))
                    log.append({'method':'search','width':width,**q});done=True;break
                except RuntimeError as e:
                    log.append({'method':'search','net':net,'width':width,'status':'BLOCKED','reason':str(e),'island_pair':[i,j]})
            if not done:break
        connected(b);save(b)
    remaining=len(clusters(b,net,targets));save(b)
    print('RESULT',net,width,'islands',remaining,flush=True)
    dump(R/(label+'_'+net.strip('/').replace('+','p')+'_'+str(width)+'_'+str(time.time_ns())+'.json'),{'net':net,'width':width,'remaining_pad_islands':remaining,'operations':log})
    return remaining

if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare()
    elif sys.argv[1]=='solve':solve(sys.argv[2],float(sys.argv[3])if len(sys.argv)>3 else .2)

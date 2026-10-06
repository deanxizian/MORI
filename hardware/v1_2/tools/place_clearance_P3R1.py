"""Compare local placement/orientation alternatives before repairing routing.

Preserves mounting holes, connectors, MCU/IMU axes and switching components.
Only selected small parts are moved. A candidate must not collide with other
packages, pads, holes or different-net copper. Old pad tails are removed for
explicit reconnection; no endpoint is dragged across intervening components.
"""
import sys,json,math
import pcbnew as k
from layout_P3R1 import paths,xy,pt,mm,setplace,bounds,intersects
from audit_body_routes_P3 import rect,clip
from body_keepouts_P3R1 import create

kind=sys.argv[1];assert kind in ['motion','power'];name,d,p,r=paths(kind);b=k.LoadBoard(str(p));fps={f.GetReference():f for f in b.GetFootprints()}
refs=['R19','D1','R10','R17','R18','R5','R9','C11'] if kind=='motion' else ['R24','R43','R44','R45','R50','R56','R60','C20']
log=[]
for ref in refs:
    f=fps[ref];old=(*xy(f.GetPosition()),f.GetOrientationDegrees());side='B' if f.IsFlipped() else 'F'
    oldpads={p.GetNumber():xy(p.GetPosition()) for p in f.Pads()};ownnets={p.GetNetname() for p in f.Pads()};traces=[t for t in b.GetTracks() if not isinstance(t,k.PCB_VIA) and t.IsOnLayer(f.GetLayer())]
    # Conservative package-to-package and actual pad-to-other-net checks.
    def legal():
        box=bounds(f);w,h=(70,35) if kind=='motion' else (80,55)
        if box[0]<.6 or box[1]<.6 or box[2]>w-.6 or box[3]>h-.6:return False
        for other in fps.values():
            if other==f:continue
            if other.GetLayer()==f.GetLayer() and intersects(box,bounds(other),.12):return False
            for pad in other.Pads():
                if pad.GetAttribute() not in [k.PAD_ATTRIB_PTH,k.PAD_ATTRIB_NPTH]:continue
                x,y=xy(pad.GetPosition());rad=2.7 if other.GetReference().startswith('H') else max(k.ToMM(pad.GetSize().x),k.ToMM(pad.GetSize().y))/2+.3
                if intersects(box,[x-rad,y-rad,x+rad,y+rad]):return False
        for pad in f.Pads():
            shape=pad.GetEffectiveShape(f.GetLayer())
            for t in b.GetTracks():
                if t.IsOnLayer(f.GetLayer()) and t.GetNetCode()!=pad.GetNetCode() and shape.Collide(t.GetEffectiveShape(f.GetLayer()),mm(.202)):return False
        return True
    def score():
        body=rect(f);foreign=own=0.
        for t in traces:
            a,z=xy(t.GetStart()),xy(t.GetEnd());span=clip(a,z,body)
            if span:
                length=math.dist(a,z)*(span[1]-span[0])
                if t.GetNetname() in ownnets:own+=length
                else:foreign+=length
        movement=sum(math.dist(xy(pad.GetPosition()),oldpads[pad.GetNumber()]) for pad in f.Pads())
        return 30*foreign+own+movement,foreign,movement
    initial=score();best=(initial[0],old,initial);attempts=0;legal_count=0
    radius=1 if ref.startswith('C') else 2.5
    n=int(radius/.5)
    for dx in range(-n,n+1):
        for dy in range(-n,n+1):
            for angle in [0,90,180,270]:
                attempts+=1;setplace(f,old[0]+dx*.5,old[1]+dy*.5,angle,side)
                if not legal():continue
                legal_count+=1;s=score()
                if s[0]<best[0]-.05:best=(s[0],(*xy(f.GetPosition()),angle),s)
    setplace(f,*old,side=side)
    changed=best[1]!=old
    removed=[]
    if changed:
        for t in list(b.GetTracks()):
            if isinstance(t,k.PCB_VIA):continue
            if any(t.IsOnLayer(f.GetLayer()) and t.GetNetCode()==pad.GetNetCode() and t.GetEffectiveShape(f.GetLayer()).Collide(pad.GetEffectiveShape(f.GetLayer()),mm(.001)) for pad in f.Pads()):
                removed.append(dict(uuid=t.m_Uuid.AsString(),net=t.GetNetname(),width=k.ToMM(t.GetWidth()),start=xy(t.GetStart()),end=xy(t.GetEnd())));b.Delete(t)
        setplace(f,*best[1],side=side)
    entry=dict(ref=ref,before=old,after=best[1],trials=attempts,legal_candidates=legal_count,initial_score=initial,final_score=best[2],changed=changed,removed_tails=removed)
    log.append(entry);print(kind,ref,old,'->',best[1],'foreign length',initial[1],'->',best[2][1],flush=True)
zones=create(b);k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
(r/'body_keepouts.json').write_text(json.dumps(zones,ensure_ascii=False,indent=2)+'\n')
(r/'placement_optimization.json').write_text(json.dumps(log,ensure_ascii=False,indent=2)+'\n')

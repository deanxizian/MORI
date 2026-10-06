"""Native body keepouts, with explicit outward pad-escape channels.

No blanket power/ground net exemptions. Copper zones remain permitted.
Rules apply to the component assembly side. Mezzanine module projections are
reported separately: they are not solid bodies on the carrier copper surface.
"""
import sys,json,math
import pcbnew as k
from layout_P3R1 import paths,xy,pt,mm
from audit_body_routes_P3 import rect

def polygon(points):
    s=k.SHAPE_POLY_SET();s.NewOutline()
    for x,y in points:s.Append(mm(x),mm(y))
    return s

def rectangle(r):
    x,y,z,w=r
    return polygon([(x,y),(z,y),(z,w),(x,w)])

def create(b):
    for z in list(b.Zones()):
        if z.GetIsRuleArea() and z.GetZoneName().startswith(('BODY_','OUTWARD_','NETBODY_')):b.Delete(z)
    log=[]
    for f in b.GetFootprints():
        ref=f.GetReference();r=rect(f)
        if not r or ref.startswith(('H','TP')) or ref=='U100':continue
        x1,y1,x2,y2=r;body=rectangle(r)
        circles=[s for s in f.GraphicalItems() if isinstance(s,k.PCB_SHAPE) and s.GetLayer() in [k.F_Fab,k.B_Fab] and s.GetShape()==k.S_CIRCLE]
        if circles:
            c=max(circles,key=lambda s:s.GetRadius());cx,cy=xy(c.GetCenter());rr=k.ToMM(c.GetRadius())
            if rr>min(x2-x1,y2-y1)*.4:body=polygon([(cx+rr*math.cos(i*math.pi/48),cy+rr*math.sin(i*math.pi/48)) for i in range(96)])
        # The full envelope is also a named, net-selective rule area. Pad
        # escape cutouts must not become tunnels for unrelated signals.
        full=k.ZONE(b);full.SetIsRuleArea(True);full.SetLayer(f.GetLayer());full.SetZoneName('NETBODY_'+ref)
        full.SetDoNotAllowTracks(False);full.SetDoNotAllowVias(False);full.SetDoNotAllowPads(False);full.SetDoNotAllowFootprints(False);full.SetDoNotAllowZoneFills(False)
        full.Outline().BooleanAdd(body);b.Add(full)
        exits=[]
        for p in f.Pads():
            if p.GetAttribute()==k.PAD_ATTRIB_NPTH:continue
            bb=p.GetBoundingBox();a,c,z,w=[k.ToMM(v) for v in [bb.GetX(),bb.GetY(),bb.GetRight(),bb.GetBottom()]]
            # Tiny numerical allowance around the pad, not a blanket corridor.
            a-=.005;c-=.005;z+=.005;w+=.005;body.BooleanSubtract(rectangle([a,c,z,w]))
            px,py=xy(p.GetPosition())
            # Pin normal uses its position relative to the body centre. For
            # THT connector/cap pins, allow their two nearest outer edges;
            # a straight local exit from inside a housing is unavoidable.
            distances=[(abs(px-x1),'left'),(abs(x2-px),'right'),(abs(py-y1),'top'),(abs(y2-py),'bottom')]
            distances.sort();directions=[distances[0][1]]
            if p.GetAttribute()==k.PAD_ATTRIB_PTH:directions=[v[1] for v in distances[:2]]
            # J2's equally distant top/bottom exits are not interchangeable
            # in the power corridor. Select the top exit for its BAT pin.
            if ref=='J2' and p.GetNumber()=='2' and p.GetNetname()=='/BAT_MON':directions=['right','top']
            for direction in directions:
                channel={'left':[x1-1,c,z,w],'right':[a,c,x2+1,w],'top':[a,y1-1,z,w],'bottom':[a,c,z,y2+1]}[direction]
                body.BooleanSubtract(rectangle(channel))
            exits.append(dict(pin=p.GetNumber(),net=p.GetNetname(),directions=directions))
        body.Simplify()
        if body.OutlineCount()==0:continue
        z=k.ZONE(b);z.SetIsRuleArea(True);z.SetLayer(f.GetLayer());z.SetZoneName('BODY_'+ref)
        z.SetDoNotAllowTracks(True);z.SetDoNotAllowVias(True);z.SetDoNotAllowPads(False);z.SetDoNotAllowFootprints(False);z.SetDoNotAllowZoneFills(False);z.Outline().BooleanAdd(body);b.Add(z)
        log.append(dict(reference=ref,side=b.GetLayerName(f.GetLayer()),body_source='Native Fab body; circular outline used where available',body_rect_mm=r,outward_pad_channels=exits,net_exemptions=[]))
    return log

if __name__=='__main__':
    kind=sys.argv[1];name,d,p,r=paths(kind);b=k.LoadBoard(str(p));log=create(b);k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
    marker='# P3R1 net-selective body escape rules'
    rulefile=d/(name+'.kicad_dru');base=rulefile.read_text().split(marker)[0].rstrip()+'\n\n'+marker+'\n'
    for f in b.GetFootprints():
        ref=f.GetReference()
        if not any(z.GetZoneName()=='NETBODY_'+ref for z in b.Zones()):continue
        allowed=sorted({str(p.GetNetname()) for p in f.Pads() if p.GetNetname()})
        cond="A.intersectsArea('NETBODY_"+ref+"')"+''.join(" && A.NetName != '"+n+"'" for n in allowed)
        base+='(rule '+json.dumps('P3R1 '+ref+' unrelated nets outside body')+'\n  (condition '+json.dumps(cond)+')\n  (constraint disallow track via)\n)\n'
    rulefile.write_text(base)
    (r/'body_keepouts.json').write_text(json.dumps(log,ensure_ascii=False,indent=2)+'\n')
    print(name,'native body rule areas:',len(log),flush=True)

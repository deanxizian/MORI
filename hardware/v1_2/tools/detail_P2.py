"""Local electrical routing details. Run by layout_P2 before general routing."""
import pcbnew as k
import math
mm=k.FromMM
pt=lambda x,y:k.VECTOR2I(mm(x),mm(y))

def track(b,net,a,c,width,layer):
    t=k.PCB_TRACK(b);t.SetStart(pt(*a));t.SetEnd(pt(*c));t.SetWidth(mm(width));t.SetLayer(layer);t.SetNet(net);b.Add(t)
    return t

def seed(kind,b):
    if kind=='motion':
        # Reserve the head UART input escape before adjacent buses are routed.
        net=b.GetNetsByName()['/HEAD_TX']
        track(b,net,(20.45,23.25),(19.15,23.25),.2,k.B_Cu)
        v=k.PCB_VIA(b);v.SetPosition(pt(19.15,23.25));v.SetWidth(mm(.8));v.SetDrill(mm(.3));v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(net);b.Add(v)
    if kind=='imu':
        f=next(f for f in b.GetFootprints() if f.GetReference()=='U1')
        # Radial escapes are placed explicitly so the autorouter cannot send a
        # digital trace under the die or refuse to start inside an expanded rule area.
        for p in f.Pads():
            n=int(p.GetNumber());a=(k.ToMM(p.GetPosition().x),k.ToMM(p.GetPosition().y))
            dx,dy=(-1,0) if n<=4 else (0,1) if n<=7 else (1,0) if n<=11 else (0,-1)
            track(b,p.GetNet(),a,(a[0]+dx*1.2,a[1]+dy*1.2),.2,k.F_Cu)
    if kind in ['motion','power']:
        # Four 45-degree ground escape spokes plus stitching at each socket
        # ground reserve copper before the signal router. Adjacent 2.54 mm
        # socket pads share a stitching via at their corner.
        made=set()
        for f in b.GetFootprints():
            if kind=='power' and f.GetReference() not in ['J4','J5','J8']:continue
            for p in f.Pads():
                if p.GetAttribute()!=k.PAD_ATTRIB_PTH or p.GetNetname()!='/GND':continue
                x,y=k.ToMM(p.GetPosition().x),k.ToMM(p.GetPosition().y)
                sx,sy=k.ToMM(p.GetSize().x),k.ToMM(p.GetSize().y)
                off=1.27 if f.GetReference()=='U100' else max(sx,sy)/2+.7
                if kind=='power' and f.GetReference()=='J8':off=1.42
                for dx,dy in [(-off,-off),(-off,off),(off,-off),(off,off)]:
                    c=(round(x+dx,5),round(y+dy,5))
                    for layer in [k.F_Cu,k.B_Cu]:track(b,p.GetNet(),(x,y),c,.3,layer)
                    if c in made:continue
                    vd,dr=(.75,.25) if kind=='motion' else (.8,.3) if f.GetReference()=='J8' else (1.0,.45)
                    made.add(c);v=k.PCB_VIA(b);v.SetPosition(pt(*c));v.SetWidth(mm(vd));v.SetDrill(mm(dr));v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(p.GetNet());v.SetFrontTentingMode(k.TENTING_MODE_NOT_TENTED);b.Add(v)
    if kind=='power':
        # Shunt load current exits its OUTER pad sides. Sense branches leave
        # each INNER pad edge independently, with no shared load-carrying neck.
        fps={f.GetReference():f for f in b.GetFootprints()}
        def pins(ref):return {p.GetNumber():p for p in fps[ref].Pads()}
        assert pins('R3')['1'].GetPosition()==pt(20,15.175)
        assert pins('R4')['1'].GetPosition()==pt(28,15.175)
        routes=[('/BAT_REV',[(17.475,10.595),(17.475,12.83)],2,k.B_Cu),
                ('/BAT_REV',[(17.475,12.83),(17.475,13.135)],.6,k.B_Cu),
                ('/BAT_REV',[(17.475,12),(21.0375,12)],2,k.B_Cu),
                ('/BAT_REV',[(21.5,13.5),(21.5,13.675),(20,15.175)],.2,k.B_Cu),
                ('/BAT_MON',[(26.5,13.5),(26.5,13.675),(28,15.175)],.2,k.B_Cu),
                ('/BAT_MON',[(26.9625,12),(28.7,12),(28.7,13.6)],2,k.B_Cu),
                ('/BAT_MON',[(29,7),(28.7,7.3),(28.7,31.5)],2,k.F_Cu),
                ('/BAT_MON',[(28.7,31.5),(21.5,31.5),(15,38)],2,k.F_Cu),
                ('/BAT_MON',[(28.7,31.5),(36.5,39.3),(36.5,42.5),(45.5,42.5),(49,39)],2,k.F_Cu)]
        for n,points,width,layer in routes:
            for a,c in zip(points,points[1:]):track(b,b.GetNetsByName()[n],a,c,width,layer)
        for x,y in [(28.7,12),(28.7,13.6)]:
            v=k.PCB_VIA(b);v.SetPosition(pt(x,y));v.SetWidth(mm(1));v.SetDrill(mm(.45));v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(b.GetNetsByName()['/BAT_MON']);b.Add(v)
        # Comparator reference pin fanout and the low-current pull-up feed
        # must be reserved before routing the surrounding wide motor bus.
        ref=b.GetNetsByName()['/W_REF'];track(b,ref,(65.525,14.635),(63.95,14.635),.2,k.B_Cu)
        v=k.PCB_VIA(b);v.SetPosition(pt(63.95,14.635));v.SetWidth(mm(.8));v.SetDrill(mm(.3));v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(ref);b.Add(v)
        points=[(59.5,22.325),(59.5,23.9),(60.1,24.5),(63.175,24.5),(64.175,23.5)]
        for a,c in zip(points,points[1:]):track(b,b.GetNetsByName()['/W_VM'],a,c,.2,k.B_Cu)
        gate=b.GetNetsByName()['/W_GATE'];track(b,gate,(38.405,14.525),(38.405,12.925),.2,k.B_Cu)
        v=k.PCB_VIA(b);v.SetPosition(pt(38.405,12.925));v.SetWidth(mm(.8));v.SetDrill(mm(.3));v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(gate);b.Add(v)
        # Drain escape neck is 0.6 mm for < 2 mm, followed by 1.5 mm pulse bus.
        net=b.GetNetsByName()['/W_DUMP_D']
        track(b,net,(75.9375,12),(78,12),.6,k.B_Cu)
        v=k.PCB_VIA(b);v.SetPosition(pt(78,12));v.SetWidth(mm(1));v.SetDrill(mm(.45));v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(net);b.Add(v)
        points=[(66,7),(66,10),(68,12),(78,12)]
        for a,c in zip(points,points[1:]):track(b,net,a,c,1.5,k.F_Cu)

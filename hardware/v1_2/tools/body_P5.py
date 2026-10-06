"""P5 native, two-face body protection and explicit local pin escape.

The only apertures are actual pad lands and outward rays for the same part.
NETBODY rules prohibit unrelated nets in these apertures. Copper planes are
not tracks; the IMU additionally retains the vendor no-copper die area.
"""
import math,json,sys
import pcbnew as k
from layout_P5 import paths,xy,pt,mm,F,B,rect
from body_keepouts_P3R1 import rectangle,polygon

def normal(kind,f,p):
    ref=f.GetReference();x,y=xy(p.GetPosition());r=rect(f)
    if kind=='imu' and ref=='J1':return (0,1)
    if kind=='motion':
        if ref=='J1':return (0,1)
        if ref=='J2':return (0,-1)
        if ref=='J4' and abs(f.GetOrientationDegrees())<.01 and p.GetNumber() in ['5','7']:return (0,1)
        if ref in ['J3','J4','J5','J7']:return (0,-1) if abs(f.GetOrientationDegrees())<.01 else (-1,0)
        if ref in ['J6','J8']:return (0,-1)
    if kind=='power' and ref=='J10' and p.GetNumber() in ['5','6']:return (-1,0)
    if kind=='power' and ref in ['J17','J10']:return (1,0)
    if kind=='rear':
        if ref=='J2':return (-1,0)
        if ref=='J3':return (0,-1)
        if ref=='USB1':return ((-1 if x<12 else 1),0) if p.GetNumber()=='SH' else (0,1)
    cx,cy=(r[0]+r[2])/2,(r[1]+r[3])/2
    dx,dy=x-cx,y-cy
    if abs(dx)/max((r[2]-r[0])/2,.1)>=abs(dy)/max((r[3]-r[1])/2,.1):return (1 if dx>=0 else -1,0)
    return (0,1 if dy>=0 else -1)

def create(b,kind):
    for z in list(b.Zones()):
        if z.GetIsRuleArea() and z.GetZoneName().startswith(('BODY_','NETBODY_','VIA_BODY_','TDK_')):b.Delete(z)
    log=[]
    for f in b.GetFootprints():
        ref=f.GetReference();r=rect(f)
        if not r or ref.startswith(('H','TP')) or ref=='U100':continue
        x1,y1,x2,y2=r;full=rectangle(r);body=rectangle(r);exits=[]
        circles=[s for s in f.GraphicalItems() if isinstance(s,k.PCB_SHAPE) and s.GetLayer() in [k.F_Fab,k.B_Fab] and s.GetShape()==k.S_CIRCLE]
        if circles:
            c=max(circles,key=lambda s:s.GetRadius());cx,cy=xy(c.GetCenter());rr=k.ToMM(c.GetRadius())
            if rr>min(x2-x1,y2-y1)*.4:
                points=[(cx+rr*math.cos(i*math.pi/48),cy+rr*math.sin(i*math.pi/48)) for i in range(96)]
                full=polygon(points);body=polygon(points)
        for p in f.Pads():
            if p.GetAttribute()==k.PAD_ATTRIB_NPTH:continue
            bb=p.GetBoundingBox();a,c,z,w=[k.ToMM(v) for v in [bb.GetX(),bb.GetY(),bb.GetRight(),bb.GetBottom()]]
            a-=.005;c-=.005;z+=.005;w+=.005
            body.BooleanSubtract(rectangle([a,c,z,w]));nx,ny=normal(kind,f,p)
            channel=([x1-1,c,z,w] if nx<0 else [a,c,x2+1,w] if nx>0 else [a,y1-1,z,w] if ny<0 else [a,c,z,y2+1])
            body.BooleanSubtract(rectangle(channel))
            exits.append(dict(pin=p.GetNumber(),net=p.GetNetname(),normal=[nx,ny]))
        body.Simplify()
        # Exact GND stitching drill windows, not signal-track permissions.
        # USB shield ESD return and the two connector ground islands need
        # local layer stitching; all body track keepouts stay intact.
        stitches=({'USB1':[(12,2.8),(12,5)],'J2':[(20.5,17.7)],'J3':[(10.45,21.2)],'SW1':[(12,12.8)]}.get(ref,[]) if kind=='rear' else [])
        for layer in [F,B]:
            suffix='' if layer==f.GetLayer() else '_OPPOSITE'
            for prefix,shape,forbid in [('NETBODY_',full,False),('BODY_',body,True)]:
                if shape.OutlineCount()==0:continue
                z=k.ZONE(b);z.SetIsRuleArea(True);z.SetLayer(layer);z.SetZoneName(prefix+ref+suffix)
                z.SetDoNotAllowTracks(forbid);z.SetDoNotAllowVias(forbid)
                if prefix=='BODY_' and stitches:z.SetDoNotAllowVias(False)
                z.SetDoNotAllowPads(False);z.SetDoNotAllowFootprints(False);z.SetDoNotAllowZoneFills(False)
                z.Outline().BooleanAdd(shape);b.Add(z)
            if stitches:
                vb=rectangle(r)
                for sx,sy in stitches:vb.BooleanSubtract(rectangle([sx-.45,sy-.45,sx+.45,sy+.45]))
                z=k.ZONE(b);z.SetIsRuleArea(True);z.SetLayer(layer);z.SetZoneName('VIA_BODY_'+ref+suffix)
                z.SetDoNotAllowTracks(False);z.SetDoNotAllowVias(True);z.SetDoNotAllowPads(False);z.SetDoNotAllowFootprints(False);z.SetDoNotAllowZoneFills(False)
                z.Outline().BooleanAdd(vb);b.Add(z)
        log.append(dict(ref=ref,body_rect_mm=r,escapes=exits,unrelated_nets_allowed=False,both_outer_layers=True))
    if kind=='imu':
        f=next(f for f in b.GetFootprints() if f.GetReference()=='U1');x,y=xy(f.GetPosition())
        assert abs(f.GetOrientationDegrees())<.001,'Transform vendor keepout before changing IMU axes'
        for layer,dx,dy in [(F,.9,.65),(B,1.5,1.25)]:
            z=k.ZONE(b);z.SetIsRuleArea(True);z.SetLayer(layer);z.SetZoneName('TDK_AN000393_under_IMU_'+b.GetLayerName(layer))
            z.SetDoNotAllowTracks(True);z.SetDoNotAllowVias(True);z.SetDoNotAllowZoneFills(True)
            z.SetDoNotAllowPads(False);z.SetDoNotAllowFootprints(False)
            z.Outline().BooleanAdd(rectangle([x-dx,y-dy,x+dx,y+dy]));b.Add(z)
    return log

if __name__=='__main__':
    kind=sys.argv[1];name,d,p,r=paths(kind);b=k.LoadBoard(str(p));log=create(b,kind)
    k.SaveBoard(str(p),b);(r/'body_areas.json').write_text(json.dumps(log,indent=2)+'\n')

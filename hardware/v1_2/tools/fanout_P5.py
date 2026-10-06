"""Reserve short, straight outward escape before routing long nets."""
import json,sys,math
import pcbnew as k
from layout_P5 import paths,xy,pt,mm,F,B,track,rect
from body_P5 import normal,create
from geometry_guard_P5 import Guard

def run(kind):
    name,d,p,r=paths(kind);b=k.LoadBoard(str(p));body=create(b,kind)
    log=[];failed=[];seen=set()
    for f in sorted(b.GetFootprints(),key=lambda f:(not f.GetReference().startswith('U'),f.GetReference())):
        ref=f.GetReference()
        if ref.startswith(('H','TP')) or ref=='U100':continue
        rr=rect(f)
        for q in f.Pads():
            net=q.GetNetname();a=xy(q.GetPosition());key=(net,a)
            if key in seen or not net or net.startswith('unconnected-') or q.GetAttribute()==k.PAD_ATTRIB_NPTH:continue
            seen.add(key)
            if any(t.GetNetname()==net and t.IsOnLayer(f.GetLayer()) and t.GetEffectiveShape(f.GetLayer()).Collide(q.GetEffectiveShape(f.GetLayer()),0) for t in b.GetTracks()):continue
            nx,ny=normal(kind,f,q);edge=rr[2] if nx>0 else rr[0] if nx<0 else rr[3] if ny>0 else rr[1]
            axis=0 if nx else 1;sign=nx or ny
            # SMD pins often extend beyond the Fab body already. Preserve
            # at least a half-millimetre straight departure from the pad.
            goal=max(sign*edge+.5,sign*a[axis]+.5)*sign
            z=(goal,a[1]) if nx else (a[0],goal)
            width=.2
            if kind=='rear' and net in ['/VBUS_RAW','/VBUS_FUSED'] and ref!='USB1':width=.6
            g=Guard(b,net)
            if g.line_clear(a,z,f.GetLayer(),width):
                ts=track(b,net,[a,z],width,f.GetLayer())
                log.append(dict(ref=ref,pin=q.GetNumber(),net=net,start=a,end=z,normal=[nx,ny],layer=b.GetLayerName(f.GetLayer()),width=width,tracks=[t.m_Uuid.AsString() for t in ts]))
            else:failed.append(dict(ref=ref,pin=q.GetNumber(),net=net,start=a,end=z,normal=[nx,ny]))
    k.SaveBoard(str(p),b)
    (r/'body_areas.json').write_text(json.dumps(body,indent=2)+'\n')
    (r/'fanout.json').write_text(json.dumps(dict(routes=log,unresolved=failed),indent=2)+'\n')
    print(kind,'fresh outward ports',len(log),'unresolved',len(failed),flush=True)
if __name__=='__main__':run(sys.argv[1])

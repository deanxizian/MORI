"""Put a visible board/revision identifier in unused silkscreen space."""
import sys
import pcbnew as k
from layout_P2 import paths,pt,mm

def mark(kind):
    name,d,p=paths(kind);b=k.LoadBoard(str(p))
    import json
    w,h=json.loads((d/'connectivity.json').read_text())['size']
    text={'motion':'MORI MOTION\nP2 PROTOTYPE','power':'MORI POWER\nP2 PROTOTYPE','imu':'MORI\nIMU P2'}[kind]
    if any(isinstance(g,k.PCB_TEXT) and g.GetText()==text for g in b.GetDrawings()):return
    t=k.PCB_TEXT(b);t.SetText(text);t.SetTextSize(pt(.8,.8));t.SetTextThickness(mm(.12))
    sides=[k.B_SilkS,k.F_SilkS] if kind in ['motion','imu'] else [k.F_SilkS,k.B_SilkS]
    for side in sides:
        t.SetLayer(side);t.SetMirrored(side==k.B_SilkS)
        for _,x,y in sorted(((x*.5-w/2)**2+(y*.5-h/2)**2,x*.5,y*.5) for x in range(2,int(w*2)-1) for y in range(2,int(h*2)-1)):
            t.SetPosition(pt(x,y));bb=t.GetBoundingBox();bb.Inflate(mm(.15))
            if bb.GetX()<mm(.5) or bb.GetY()<mm(.5) or bb.GetRight()>mm(w-.5) or bb.GetBottom()>mm(h-.5):continue
            bad=False
            for f in b.GetFootprints():
                if f.IsFlipped()==(side==k.B_SilkS) and bb.Intersects(f.GetBoundingBox(False,False)):bad=True;break
                for pad in f.Pads():
                    if pad.IsOnLayer(k.B_Mask if side==k.B_SilkS else k.F_Mask) and bb.Intersects(pad.GetBoundingBox()):bad=True;break
                if f.GetReference().startswith('H'):
                    hb=k.BOX2I(f.GetPosition()-pt(2.7,2.7),pt(5.4,5.4))
                    if bb.Intersects(hb):bad=True;break
                if bad:break
            if bad:continue
            if any((isinstance(g,k.PCB_TEXT) and g.GetLayer()==side or isinstance(g,k.PCB_VIA)) and bb.Intersects(g.GetBoundingBox()) for g in list(b.GetDrawings())+list(b.GetTracks())):continue
            b.Add(t);k.SaveBoard(str(p),b);print(name,'board identity',side,x,y);return
    raise RuntimeError('No readable board identity space: '+name)

if __name__=='__main__':mark(sys.argv[1])

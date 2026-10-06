"""Final power-board junction and thermal-spoke geometry corrections."""
import pcbnew as k
from layout_P2 import paths,pt,mm
from detail_P2 import track
from close_routes_P2 import snap_via_ends,merge_lines

name,d,p=paths('power');b=k.LoadBoard(str(p))
for t in b.GetTracks():
    if isinstance(t,k.PCB_VIA):continue
    if t.GetNetname()=='/BAT_MON' and t.GetLayer()==k.F_Cu:
        if t.GetStart()==pt(31.05,13.95) and t.GetEnd()==pt(29.05,13.95):t.SetEnd(pt(30.7,13.6))
        if t.GetStart()==pt(29.05,13.95) and t.GetEnd()==pt(28.7,13.6):t.SetStart(pt(30.7,13.6))
    if t.GetNetname()=='/WHEEL_ADC' and t.GetStart()==pt(32.3746,24.8004):t.SetStart(pt(32.37455,24.80045))
    if t.GetNetname()=='/W_GATE' and t.GetStart()==pt(38.405,12.925):t.SetStart(pt(38.405,14.525))

net=b.GetNetsByName()['/GND'];code=net.GetNetCode();added=[]
def clear_spoke(a,c,layer):
    seg=k.SEG(pt(*a),pt(*c))
    for f in b.GetFootprints():
        for pad in f.Pads():
            if pad.GetNetCode()!=code and pad.IsOnLayer(layer) and pad.GetEffectiveShape(layer).Collide(seg,mm(.351)):return False
    for t in b.GetTracks():
        if t.GetNetCode()!=code and t.IsOnLayer(layer) and t.GetEffectiveShape(layer).Collide(seg,mm(.351)):return False
    return True
def clear_via(c):
    p=pt(*c)
    for layer in [k.F_Cu,k.B_Cu]:
        for f in b.GetFootprints():
            for pad in f.Pads():
                if pad.IsOnLayer(layer) and pad.GetEffectiveShape(layer).Collide(p,mm(.601)):return False
        for t in b.GetTracks():
            if t.GetNetCode()!=code and t.IsOnLayer(layer) and t.GetEffectiveShape(layer).Collide(p,mm(.601)):return False
    return True
for sx,sy in [(-1,-1),(-1,1),(1,-1),(1,1)]:
    for delta in [1.42,1.6,1.8,2,2.2]:
        c=(48+sx*delta,21+sy*delta)
        if not clear_spoke((48,21),c,k.B_Cu) or not clear_via(c):continue
        if not any(isinstance(t,k.PCB_VIA) and t.GetPosition()==pt(*c) for t in b.GetTracks()):
            v=k.PCB_VIA(b);v.SetPosition(pt(*c));v.SetWidth(mm(.8));v.SetDrill(mm(.3));v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(net);v.SetFrontTentingMode(k.TENTING_MODE_NOT_TENTED);b.Add(v)
            track(b,net,(48,21),c,.3,k.B_Cu);added.append(c)
        break
merge_lines(b);snap_via_ends(b);k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
print('Power junctions corrected; J7 ground stitches',added)

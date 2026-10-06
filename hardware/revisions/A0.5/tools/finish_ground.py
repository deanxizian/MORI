"""KiCad Python: explicit short U6 ground fanout, followed by native DRC.

The local 0.25mm / 0.6-0.3mm connection is for the low-current translator only.
It is not a substitute for the motor-bus return geometry.
"""
from pathlib import Path
import pcbnew as k
R=Path(__file__).resolve().parents[1];p=R/'kicad/MORI_carrier.kicad_pcb'
b=k.LoadBoard(str(p));net=b.GetNetsByName()['/GND'];mm=k.FromMM
for fp in b.GetFootprints():
    if fp.GetReference()=='U1':
        for pad in fp.Pads():
            if pad.GetNumber()=='10':pad.SetLocalZoneConnection(k.ZONE_CONNECTION_FULL)
vpos=k.VECTOR2I(mm(127.575),mm(141.85))
assert not any(isinstance(t,k.PCB_VIA) and t.GetPosition()==vpos for t in b.GetTracks()),'Already applied'
v=k.PCB_VIA(b);v.SetPosition(vpos);v.SetWidth(mm(.6));v.SetDrill(mm(.3))
v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(net);b.Add(v)
points=[(126.4375,141.4),(126.75,141.7),(127.575,141.7),(127.575,141.85)]
for a,c in zip(points,points[1:]):
    t=k.PCB_TRACK(b);t.SetStart(k.VECTOR2I(mm(a[0]),mm(a[1])));t.SetEnd(k.VECTOR2I(mm(c[0]),mm(c[1])))
    t.SetWidth(mm(.25));t.SetLayer(k.F_Cu);t.SetNet(net);b.Add(t)
assert k.ZONE_FILLER(b).Fill(b.Zones())
k.SaveBoard(str(p),b)
print('U6 GND fanout and U1 ground-plane junction applied; run DRC')

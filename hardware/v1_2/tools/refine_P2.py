"""Recorded local P2 copper corrections, followed by native refill and DRC."""
from pathlib import Path
import json,sys,math
import pcbnew as k
from layout_P2 import paths,configure,pt,mm
from detail_P2 import track

def via(b,net,x,y,size=.8,drill=.3):
    if any(isinstance(t,k.PCB_VIA) and t.GetPosition()==pt(x,y) for t in b.GetTracks()):return
    v=k.PCB_VIA(b);v.SetPosition(pt(x,y));v.SetNet(b.GetNetsByName()[net]);v.SetWidth(mm(size));v.SetDrill(mm(drill));v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetFrontTentingMode(k.TENTING_MODE_NOT_TENTED);b.Add(v)

def path(b,net,points,layer,width=.2):
    for a,c in zip(points,points[1:]):
        if not any(not isinstance(t,k.PCB_VIA) and t.GetNetname()==net and t.GetLayer()==layer and {tuple(t.GetStart()),tuple(t.GetEnd())}=={tuple(pt(*a)),tuple(pt(*c))} for t in b.GetTracks()):
            track(b,b.GetNetsByName()[net],a,c,width,layer)

def refine(kind):
    name,d,p=paths(kind);b=k.LoadBoard(str(p));configure(kind,b,d,name)
    removed=[]
    for t in list(b.GetTracks()):
        if not isinstance(t,k.PCB_VIA) and t.GetLength()<mm(.005):removed.append(str(t.m_Uuid));b.Delete(t)
    if kind=='motion':
        corners={(round(k.ToMM(t.GetPosition().x),5),round(k.ToMM(t.GetPosition().y),5)) for t in b.GetTracks() if isinstance(t,k.PCB_VIA) and t.GetNetname()=='/GND' and any(abs(k.ToMM(t.GetPosition().y)-y)<.001 for y in [31.47,28.93,.99,3.53,6.07])}
        for t in b.GetTracks():
            if isinstance(t,k.PCB_VIA) and (round(k.ToMM(t.GetPosition().x),5),round(k.ToMM(t.GetPosition().y),5)) in corners and t.GetNetname()=='/GND':t.SetWidth(mm(.75));t.SetDrill(mm(.25))
        path(b,'/HEAD_TX',[(20.45,23.25),(19.25,23.25)],k.B_Cu)
        via(b,'/HEAD_TX',19.25,23.25)
        path(b,'/HEAD_TX',[(19.25,23.25),(19.25,31.92),(20.07,32.74)],k.F_Cu)
    if kind=='imu':
        # U1.9 is ground; avoid the nearby VDD capacitor pad when joining 9/10/11.
        for t in b.GetTracks():
            if not isinstance(t,k.PCB_VIA) and t.GetStart()==pt(11.1625,9.25) and t.GetEnd()==pt(12.3625,9.25):t.SetEnd(pt(11.9,9.25))
        path(b,'/+3V3',[(9.5,11.1125),(8.6125,12),(8.225,12)],k.F_Cu)
        path(b,'/GND',[(10,11.1125),(10.5,11.1125),(10.8,10.8125)],k.F_Cu)
        via(b,'/GND',10.8,10.8125)
        path(b,'/GND',[(11.9,9.25),(11.9,8.25),(12.975,8.25),(13,8.225)],k.F_Cu)
        path(b,'/GND',[(13,8.225),(13.225,8.225),(14,9)],k.F_Cu)
        via(b,'/GND',14,9)
        # Additional low-current ground stitch near the connector, away from MEMS.
        via(b,'/GND',7.2,7.0)
    k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
    print(name,'local copper corrections; removed numerical slivers',len(removed))

if __name__=='__main__':refine(sys.argv[1])

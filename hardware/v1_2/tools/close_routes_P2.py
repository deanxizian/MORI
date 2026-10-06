"""Close the remaining P2 nets using real copper obstacles, then native DRC."""
from pathlib import Path
import sys,json,math
import pcbnew as k
from layout_P2 import paths,configure,pt,mm
from route_local_P2 import connect

def snap_via_ends(b):
    vias=[t for t in b.GetTracks() if isinstance(t,k.PCB_VIA)]
    for t in b.GetTracks():
        if isinstance(t,k.PCB_VIA):continue
        for get,setter in [(t.GetStart,t.SetStart),(t.GetEnd,t.SetEnd)]:
            p=get()
            near=[v for v in vias if v.GetNetCode()==t.GetNetCode() and (v.GetPosition()-p).EuclideanNorm()<mm(.005)]
            if near:setter(near[0].GetPosition())
    for t in list(b.GetTracks()):
        if not isinstance(t,k.PCB_VIA) and t.GetLength()<mm(.005):b.Delete(t)

def merge_lines(b):
    # Merge exactly collinear overlapping pieces; preserve their real copper.
    groups={}
    for t in b.GetTracks():
        if isinstance(t,k.PCB_VIA):continue
        a,c=t.GetStart(),t.GetEnd();dx,dy=c.x-a.x,c.y-a.y
        if dx==0:orient='v';intercept=a.x;lo,hi=sorted([a.y,c.y])
        elif dy==0:orient='h';intercept=a.y;lo,hi=sorted([a.x,c.x])
        elif abs(dx-dy)<5:orient='p';intercept=round((a.y-a.x)/5)*5;lo,hi=sorted([a.x,c.x])
        elif abs(dx+dy)<5:orient='n';intercept=round((a.y+a.x)/5)*5;lo,hi=sorted([a.x,c.x])
        else:continue
        key=(t.GetNetCode(),t.GetLayer(),t.GetWidth(),orient,intercept)
        groups.setdefault(key,[]).append((lo,hi,t))
    for key,parts in groups.items():
        parts.sort(key=lambda x:x[0]);merged=[]
        for lo,hi,t in parts:
            if merged and lo<=merged[-1][1]:merged[-1][1]=max(hi,merged[-1][1]);merged[-1][2].append(t)
            else:merged.append([lo,hi,[t]])
        for lo,hi,ts in merged:
            if len(ts)<2:continue
            _,_,_,o,i=key
            xy=lambda s:k.VECTOR2I(i,s) if o=='v' else k.VECTOR2I(s,i) if o=='h' else k.VECTOR2I(s,s+i) if o=='p' else k.VECTOR2I(s,i-s)
            ts[0].SetStart(xy(lo));ts[0].SetEnd(xy(hi))
            for t in ts[1:]:b.Delete(t)

def main(kind):
    name,d,p=paths(kind);b=k.LoadBoard(str(p));configure(kind,b,d,name);log=[]
    if kind=='motion':
        for t in list(b.GetTracks()):
            if t.GetNetname()=='/IMU_MISO' or isinstance(t,k.PCB_VIA) and t.GetPosition()==pt(19.15,23.25):b.Delete(t)
        log.append(connect(b,'/IMU_MISO',(53.95,15.375),(25.15,32.74),[k.F_Cu],[k.F_Cu,k.B_Cu],(70,35)))
    elif kind=='imu':
        for t in list(b.GetTracks()):
            if t.GetNetname()=='/GND' or isinstance(t,k.PCB_VIA) and t.GetPosition() in [pt(7.2,7),pt(14,9)]:b.Delete(t)
            elif not isinstance(t,k.PCB_VIA) and t.GetStart() in [pt(9.5,11.1125),pt(8.6125,12)] and t.GetNetname()=='/+3V3':b.Delete(t)
        log.append(connect(b,'/+3V3',(9.5,11.1),(8.225,12),[k.F_Cu],[k.F_Cu],(20,16)))
        pairs=[((8.8375,8.75),(8.8375,9.25)),((10,9.9125),(10.5,9.9125)),((11.1625,8.25),(11.1625,8.75)),((11.1625,8.75),(11.1625,9.25)),
               ((8.8375,8.75),(6.875,5.45)),((10.5,9.9125),(9.775,12)),((11.1625,9.25),(13,8.225)),
               ((9.775,12),(11.725,12)),((9.775,12),(6.875,5.45)),((13,8.225),(14.375,5.45)),((6.875,5.45),(14.375,5.45))]
        for a,c in pairs:log.append(connect(b,'/GND',a,c,[k.F_Cu],[k.F_Cu],(20,16)))
        # Consolidate common ground junctions and the two nearby stitching
        # choices produced by the independent routes above.
        for t in list(b.GetTracks()):
            if isinstance(t,k.PCB_VIA):
                if t.GetPosition()==pt(8.45,7.35):b.Delete(t)
                continue
            if t.GetNetname()=='/+3V3' and t.GetStart()==pt(9.5,9.9125):t.SetEnd(pt(9.5,11.1))
            if t.GetNetname()=='/GND':
                if t.GetStart()==pt(6.9,6.35) and t.GetEnd()==pt(6.75,6.5):t.SetEnd(pt(6.75,6.35))
                if t.GetStart()==pt(7.8,7.4) and t.GetEnd()==pt(7.7,7.5):t.SetEnd(pt(7.8,7.5))
                if t.GetStart()==pt(8.45,7.35):t.SetStart(pt(8.3,7.4))
                if t.GetEnd()==pt(8.45,7.35):t.SetEnd(pt(8.3,7.4))
    elif kind=='power':
        for t in list(b.GetTracks()):
            if isinstance(t,k.PCB_VIA) and t.GetPosition()==pt(38.405,12.925):b.Delete(t)
            elif not isinstance(t,k.PCB_VIA):
                if t.GetNetname()=='/W_VM' and t.GetLayer()==k.B_Cu and t.GetStart()==pt(61.175,16):t.SetWidth(mm(.2))
                if t.GetNetname()=='/W_VM' and t.GetLayer()==k.F_Cu and t.GetStart()==pt(64.8888,19.266) and t.GetEnd()==pt(67.4765,16.6783):t.SetEnd(pt(64.8888,16.6783))
                if t.GetNetname()=='/GND' and t.GetStart()==pt(60.58,22.42) and t.GetEnd()==pt(60.58,22.2012):b.Delete(t)
        # Divider, decoupling and comparator branches carry milliamps. They
        # may use 0.2 mm traces; the fixed load-carrying battery trunk stays 2 mm.
        jobs=[('/BAT_MON',(30,25.825),(28.7,25.825),[k.B_Cu],[k.F_Cu],1,.45),
              ('/BAT_MON',(31.5,12.775),(28.7,13.6),[k.B_Cu],[k.F_Cu,k.B_Cu],1,.45),
              ('/BAT_ADC',(30,24.175),(30.5,29.825),[k.B_Cu],[k.B_Cu],.8,.3),
              ('/FAULT_N',(70.475,14.635),(70.475,32.635),[k.B_Cu],[k.B_Cu],.8,.3),
              ('/H_OVSENSE',(70.475,31.365),(65.325,43),[k.B_Cu],[k.B_Cu],.8,.3)]
        for n,a,c,al,cl,vd,dr in jobs:log.append(connect(b,n,a,c,al,cl,(80,45),width=.2,vd=vd,dr=dr))
    merge_lines(b);snap_via_ends(b);k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
    (d/'local_routes.json').write_text(json.dumps(log,indent=2)+'\n')
    print(name,'closed local routes',len(log),flush=True)

if __name__=='__main__':main(sys.argv[1])

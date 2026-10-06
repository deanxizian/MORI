"""Reserve load-bearing copper before signal routing on the fresh P5 board."""
import json
from collections import defaultdict
import pcbnew as k
from layout_P5 import paths,xy,pt,mm,F,B,track
from body_P5 import create,normal
from geometry_guard_P5 import Guard
from close_P5 import run

MAJOR={
 '/PACK_FUSED':[('J1','2'),('Q90','1')],
 '/BAT_IN':[('Q90','5'),('Q1','5')],
 '/BAT_REV':[('Q1','1'),('R2','1')],
 '/BAT_MON':[('R2','2'),('J2','2'),('J4','2'),('J6','2')],
 '/W9_IN':[('J3','2'),('D10','2')], '/W_PRE':[('D10','1'),('Q10','1')],
 '/W_VM':[('Q10','5'),('C10','1'),('J7','2'),('J8','2'),('J11','2')],
 '/H6_IN':[('J5','2'),('D30','2')], '/H_PRE':[('D30','1'),('Q30','1')],
 '/H_VM':[('Q30','5'),('C30','1'),('J9','2'),('J12','2')],
 '/M5_SW':[('U60','2'),('L60','1')], '/C5_SW':[('U70','2'),('L70','1')],
 '/M5_VIN':[('F60','2'),('C60','1'),('C61','1'),('C66','1'),('U60','3')],
 '/C5_VIN':[('F70','2'),('C70','1'),('C71','1'),('C76','1'),('U70','3')],
 '/+5V_MOTION':[('L60','2'),('C63','1'),('C64','1'),('J17','1')],
 '/+5V_CAM':[('L70','2'),('C73','1'),('C74','1'),('J18','1')]}

def banks():
    name,d,p,r=paths('power');b=k.LoadBoard(str(p));create(b,'power');log=[]
    for f in b.GetFootprints():
        if f.GetReference() not in ['Q1','Q90','Q10','Q30']:continue
        groups=defaultdict(list)
        for q in f.Pads():groups[q.GetNetname()].append(q)
        for net,pads in groups.items():
            if len(pads)<2:continue
            nx,ny=normal('power',f,pads[0]);points=[];g=Guard(b,net)
            for q in pads:
                a=xy(q.GetPosition());z=(a[0]+nx*.9,a[1]+ny*.9)
                if not g.line_clear(a,z,F,.6):raise RuntimeError(('blocked MOSFET bank',f.GetReference(),q.GetNumber(),a,z))
                track(b,net,[a,z],.6,F);points.append(z)
            ends=sorted(points,key=lambda q:q[1] if nx else q[0]);width=1.2
            if not g.line_clear(ends[0],ends[-1],F,width):raise RuntimeError(('blocked bank spine',f.GetReference(),net,ends))
            track(b,net,[ends[0],ends[-1]],width,F)
            log.append(dict(ref=f.GetReference(),net=net,parallel_lead_width=.6,spine_width=width,points=points))
    k.SaveBoard(str(p),b);(r/'load_banks.json').write_text(json.dumps(log,indent=2)+'\n')

if __name__=='__main__':
    import sys
    if len(sys.argv)>1 and sys.argv[1]=='banks':banks()
    else:run('power',list(MAJOR),targets=MAJOR)

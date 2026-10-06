"""S2 manually composed circuits. No maze router is used by these drawings.

Supply/ground marks have real local labels, retaining original /NET names.
All internal paths are explicit, and endpoints are checked against connectivity.
"""
from collections import defaultdict
import math
from functional_schematic import Block,icpins,q,mm,effects

class Circuit(Block):
    def __init__(self,*a,**kw):
        super().__init__(*a,**kw);self.paths=defaultdict(list);self.marked=set();self.tagged=set();self.tags=[];self.label_points=defaultdict(list)
    def pin(self,ref,pn):
        xy,net,side=self.pins[(ref,str(pn))]
        return (xy[0]/2-self.x,xy[1]/2-self.y)
    def net(self,ref,pn):return self.pins[(ref,str(pn))][1]
    def path(self,net,*points):
        points=[self.pin(*p) if isinstance(p[0],str) else p for p in points]
        for a,b in zip(points,points[1:]):
            assert a[0]==b[0] or a[1]==b[1],('Nonorthogonal schematic path',self.title,net,a,b)
            if a!=b:self.paths[net].append((a,b))
    def join(self,a,b,via=(),axis='x'):
        net=self.net(*a);assert net and net==self.net(*b),(a,b,net,self.net(*b))
        p=self.pin(*a);z=self.pin(*b)
        if via:points=[p,*via,z]
        elif p[0]==z[0] or p[1]==z[1]:points=[p,z]
        else:points=[p,(z[0],p[1]) if axis=='x' else (p[0],z[1]),z]
        self.path(net,*points)
    def label(self,net,p,side='R'):
        self.tags.append((net,p,side));self.tagged.add(net);self.label_points[net].append(p)
    def mark(self,ref,pn,length=3):
        key=(ref,str(pn));xy,net,side=self.pins[key]
        if not net:return
        p=self.pin(ref,pn);v={'L':(-1,0),'R':(1,0),'T':(0,-1),'B':(0,1)}[side]
        z=(p[0]+v[0]*length,p[1]+v[1]*length);self.path(net,p,z);self.label(net,z,side);self.marked.add(key)
    def supply(self,ref,pn,up=True,length=3):
        key=(ref,str(pn));p=self.pin(ref,pn);net=self.net(ref,pn)
        z=(p[0],p[1]+(-length if up else length));self.path(net,p,z)
        x,y=z[0]+self.x,z[1]+self.y
        if up:
            self.d.line([(x-.7,y+.8),(x,y),(x+.7,y+.8)],True)
            self.d.add(f'(label {q(net)} (at {mm(x)} {mm(y)} 0) {effects(.95,"left bottom")} (uuid @UUID@))')
        else:
            self.d.line([(x-1,y),(x+1,y)],True);self.d.line([(x-.65,y+.5),(x+.65,y+.5)],True);self.d.line([(x-.3,y+1),(x+.3,y+1)],True)
            self.d.add(f'(label {q(net)} (at {mm(x+2)} {mm(y)} 0) {effects(.8,"left bottom")} (uuid @UUID@))')
            # Anchor the label electrically; place its wire at the top of ground.
            self.path(net,z,(z[0]+2,z[1]))
        self.marked.add(key);self.tagged.add(net)
        self.label_points[net].append(z)
    def route(self,net_blocks):
        # A block ends at signal ports; power and ground do not snake across it.
        def on(p,a,b):
            return min(a[0],b[0])-1e-8<=p[0]<=max(a[0],b[0])+1e-8 and min(a[1],b[1])-1e-8<=p[1]<=max(a[1],b[1])+1e-8 and abs((p[0]-a[0])*(b[1]-a[1])-(p[1]-a[1])*(b[0]-a[0]))<1e-8
        def intersection(a,b,c,z):
            if (a[0]==b[0])==(c[0]==z[0]):return None
            p=(a[0],c[1]) if a[0]==b[0] else (c[0],a[1])
            return p if on(p,a,b) and on(p,c,z) else None
        done=set()
        for key,(xy,net,side) in self.pins.items():
            p=self.pin(*key)
            if not net:
                self.d.add(f'(no_connect (at {mm(p[0]+self.x)} {mm(p[1]+self.y)}) (uuid @UUID@))');continue
            if (p,net) in done:continue
            done.add((p,net))
            if key in self.marked or any(on(p,a,b) for a,b in self.paths[net]):continue
            if net=='GND':
                if side=='B':self.supply(*key,up=False)
                else:self.mark(*key)
            elif net in ['+3V3','+5V_MOTION','CAM_3V3'] and side=='T':self.supply(*key)
            else:self.mark(*key)
        # One name per local connected net preserves PCB net identities. It is
        # placed on a short, chosen lead, not used instead of a local connection.
        for net,segments in self.paths.items():
            # Repeated supply/port names connect disconnected local islands.
            # Every island needs its own anchor; a label elsewhere in the same
            # functional block cannot name an otherwise isolated wire.
            remaining=set(range(len(segments)))
            while remaining:
                group={remaining.pop()};todo=list(group)
                while todo:
                    i=todo.pop();a,b=segments[i]
                    linked={j for j in remaining if intersection(a,b,*segments[j]) is not None or any(on(p,*segments[j]) for p in (a,b)) or any(on(p,a,b) for p in segments[j])}
                    remaining-=linked;group|=linked;todo+=list(linked)
                ss=[segments[i] for i in group]
                if not any(on(p,a,b) for p in self.label_points[net] for a,b in ss):
                    horizontal=[(a,b) for a,b in ss if a[1]==b[1]]
                    a,b=max(horizontal or ss,key=lambda v:math.dist(*v))
                    self.label(net,min(a,b))
        # A line ending on a different net would make an unintended T join.
        # Refuse to write that drawing; ordinary through-crossings stay separate.
        for net,segments in self.paths.items():
            for other,other_segments in self.paths.items():
                if net>=other:continue
                for a,b in segments:
                    for c,z in other_segments:
                        assert not any(on(p,a,b) and on(p,c,z) for p in [a,b,c,z]),('Different nets touch',self.title,net,other,a,b,c,z)
        for net,p,side in self.tags:
            x,y=p[0]+self.x,p[1]+self.y
            justify='right bottom' if side=='L' else 'left bottom'
            self.d.add(f'(label {q(net)} (at {mm(x)} {mm(y)} 0) {effects(.95,justify)} (uuid @UUID@))')
        count=0;junctions=0
        for net,segments in self.paths.items():
            vertices={p for s in segments for p in s}
            vertices.update(p for i,(a,b) in enumerate(segments) for c,z in segments[i+1:] if (p:=intersection(a,b,c,z)) is not None)
            # Include symbol pins located partway along a trunk.
            vertices.update(self.pin(*key) for key,(_,n,_) in self.pins.items() if n==net)
            edges=set()
            for a,b in segments:
                pts=sorted([p for p in vertices if on(p,a,b)],key=lambda p:math.dist(a,p))
                for p,z in zip(pts,pts[1:]):
                    if p!=z:edges.add(tuple(sorted((p,z))))
            degree=defaultdict(int)
            for a,b in sorted(edges):
                self.d.line([(a[0]+self.x,a[1]+self.y),(b[0]+self.x,b[1]+self.y)]);count+=1
                degree[a]+=1;degree[b]+=1
            for p,deg in degree.items():
                if deg>=3:
                    self.d.add(f'(junction (at {mm(p[0]+self.x)} {mm(p[1]+self.y)}) (diameter 0.762) (color 0 0 0 0) (uuid @UUID@))');junctions+=1
        self.d.stats.append(dict(title=self.title,references=self.refs,wires=count,junctions=junctions,manual=True))

def block(d,title,x,y,w,h,note=''):
    b=Circuit(d,title,x,y,w,h,note);d.blocks.append(b);return b

def decouple(b,ref,x,y):
    b.place(ref,x,y,orient='v');b.supply(ref,1);b.supply(ref,2,up=False)

def motion(d):
    d.paper=(841,640);d.text('MORI / MOTION CARRIER / S2',6,7,2.6)
    d.text('Manually composed circuits. Same electrical interfaces. PROTOTYPE / UNVALIDATED.',6,11,1.2)
    b=block(d,'01  STM32 module / GPIO map',5,15,78,113,'NC pins are intentionally unused. SWD probe connects on the module top.')
    c=d.parts['U100'];power=[n for n,p in c['pins'].items() if p['net'] in ['+3V3','+5V_MOTION']]
    gnd=[n for n,p in c['pins'].items() if p['net']=='GND'];nc=[n for n,p in c['pins'].items() if not p['net']]
    active=[n for n,p in c['pins'].items() if p['net'] and n not in power+gnd]
    active.sort(key=lambda n:({'S288':0,'HEAD':1,'LINK':2,'IMU':3,'ARM':4,'CLR':5,'NRST':5,'FAULT':5,'CHG':5,'BAT':6,'WHEEL':6,'CURRENT':6,'USER':7}.get(c['pins'][n]['net'].split('_')[0],8),c['pins'][n]['net']))
    b.place('U100',34,58,pins=icpins(left=nc,right=active,top=power,bottom=gnd,w=32,h=72),w=32,h=72,short='WeAct F412RET6 / V1.1',caption_at=(34,8))
    # Local power header pins share a compact rail above/below the module.
    for nets,ys in [(['+3V3'],15),(['+5V_MOTION'],12),(['GND'],102)]:
        group=[n for n,p in c['pins'].items() if p['net'] in nets];points=[b.pin('U100',n) for n in group]
        if not points:continue
        for p in points:b.path(nets[0],p,(p[0],ys))
        b.path(nets[0],(min(p[0] for p in points),ys),(max(p[0] for p in points),ys));b.label(nets[0],(min(p[0] for p in points),ys))
    # Data paths: TX -> resistor -> connector, RX taps the bus locally.
    for base,ref,rs,j,x,y,title in [(1,'U1','R1','J2',85,15,'02  Wheel TTL / 6 Mbps target'),(2,'U2','R2','J3',205,15,'03  Head TTL / separate bus')]:
        b=block(d,title,x,y,118,48,'3.3 V logic; actuator thresholds and timing remain bench items.')
        pins={'1':(-12,-6,'L'),'2':(-12,-2,'L'),'3':(-12,5,'L'),'6':(12,-2,'R'),'5':(12,5,'R'),'8':(0,-11,'T'),'7':(3,11,'B'),'4':(-3,11,'B')}
        b.place(ref,42,24,pins=pins,w=20,h=18)
        b.place(rs,66,22);b.place(j,94,23 if j=='J2' else 24)
        b.join((ref,6),(rs,1));p=b.pin(j,1);b.join((rs,2),(j,1),via=[(80,22),(80,p[1])]);b.join((ref,5),(j,1),via=[(80,29),(80,p[1])])
        decouple(b,'C'+str(base),108,23)
    b=block(d,'04  Explicit ARM latch / physical disable loop',85,65,118,85,'CLR_N dominates. Re-arm requires a new ARM_CLK edge; this is not a watchdog.')
    b.place('U5',61,37,pins={'1':(-12,-3,'L'),'2':(-4,-15,'T'),'6':(-12,3,'L'),'7':(4,-15,'T'),'5':(12,-3,'R'),'3':(12,3,'R'),'8':(0,-15,'T'),'4':(0,15,'B')},w=20,h=26,caption_at=(44,17))
    b.place('J8',20,24,pins={'1':(-4,0,'L'),'2':(4,0,'R')},w=4,h=4);b.place('R6',10,18,orient='v');b.supply('R6',1)
    b.join(('R6',2),('J8',1),via=[(10,24)])
    b.join(('J8',2),('U5',6),via=[(31,24),(31,40)])
    b.place('R7',31,58,orient='v');b.join(('J8',2),('R7',1),via=[(31,24)]);b.supply('R7',2,up=False)
    b.place('C12',41,70,orient='v');b.join(('R7',1),('C12',1));b.supply('C12',2,up=False)
    b.place('R5',46,58,orient='v');b.join(('U5',1),('R5',1),via=[(46,34)]);b.supply('R5',2,up=False)
    b.place('R19',90,34);b.join(('U5',5),('R19',1))
    b.path('+3V3',('U5',2),(57,19),(65,19),('U5',7));b.supply('U5',8,length=6)
    b.place('U6',18,62,pins=icpins(right=[2],top=[3],bottom=[1],w=10,h=8),w=10,h=8)
    b.mark('U6',2);decouple(b,'C6',7,62);decouple(b,'C5',105,60)
    for ref,yy in [('D1',50),('D2',62),('D3',74)]:
        b.place(ref,81,yy,kind='schottky');b.mark(ref,1);b.mark(ref,2)
    b=block(d,'05  Transmit-enable gating',205,65,118,54,'OE_N = request_N OR ARM_Q_N. Pull-ups disable TX by default.')
    b.place('U3',64,29,pins=icpins(left=[1,2,5,6],right=[7,3],top=[8],bottom=[4],w=20,h=20),w=20,h=20)
    b.place('R3',29,17,orient='vu');b.place('R4',41,17,orient='vu')
    b.supply('R3',2);b.supply('R4',2)
    # R3/R4 pin1 is the request, pin2 the supply: orient upward explicitly.
    for rr,pinno,yy in [('R3',1,26),('R4',5,30)]:
        p=b.pin(rr,1);z=b.pin('U3',pinno);b.path(b.net(rr,1),p,(p[0]-5,p[1]),(p[0]-5,z[1]),z)
    decouple(b,'C3',104,28)
    b=block(d,'06  Body IMU connector / source damping',205,121,118,51,'SPI and DRDY belong to the rigid body IMU, not the head.')
    b.place('J4',89,29,pitch=4)
    for rr,pinno,net in [('R10',3,'IMU_SCK'),('R11',4,'IMU_MOSI'),('R12',6,'IMU_CS')]:
        yy=b.pin('J4',pinno)[1];b.place(rr,52,yy);b.join((rr,2),('J4',pinno));b.mark(rr,1)
    b.place('R13',72,15,orient='vu');b.supply('R13',2);b.join(('R13',1),('J4',6),axis='y')
    b=block(d,'07  Interaction UART / power-domain isolation',85,152,118,62,'CAM_3V3 powers translator B only. It does not power the motion MCU.')
    b.place('U4',43,31,pins={'5':(-12,-4,'L'),'4':(-12,4,'L'),'6':(-12,10,'L'),'8':(12,-4,'R'),'1':(12,4,'R'),'3':(-4,-14,'T'),'7':(4,-14,'T'),'2':(0,14,'B')},w=20,h=24)
    b.place('R9',70,27);b.place('J5',96,30)
    b.join(('U4',8),('R9',1));b.join(('R9',2),('J5',1));b.join(('U4',1),('J5',2),via=[(81,35),(81,29)])
    decouple(b,'C4',15,42);decouple(b,'C7',108,42)
    b=block(d,'08  Power monitor / RC filters',205,174,118,53,'1k / 10nF filters at the ADC inputs. Scaling is on the power board.')
    b.place('J7',17,28,orient='r')
    for rr,cc,pn,xx in [('R14','C9',5,49),('R15','C10',6,72),('R16','C11',7,95)]:
        yy=18 if pn==5 else 27 if pn==6 else 36
        b.place(rr,xx,yy);b.place(cc,xx+8,yy+8,orient='v')
        p=b.pin('J7',pn);z=b.pin(rr,1);b.join(('J7',pn),(rr,1),via=[(xx-12,p[1]),(xx-12,yy)])
        b.join((rr,2),(cc,1),axis='x');b.supply(cc,2,up=False)
    # Fault / charge pull-ups use short local ports instead of crossing ADCs.
    for ref,x in [('R17',31),('R18',42)]:b.place(ref,x,11,orient='vu');b.supply(ref,2);b.mark(ref,1)
    b=block(d,'09  Input / user button / supply boundaries',5,130,78,73,'J6 is a user button. Physical disable is J8; reset can cause a fall.')
    b.place('J1',14,22,orient='r');b.place('C8',35,24,orient='v');b.join(('J1',1),('C8',1));b.supply('C8',2,up=False)
    b.place('J6',14,43,orient='r');b.place('R8',44,35,orient='vu');b.supply('R8',2);b.join(('J6',1),('R8',1),axis='x')
    for ref,x,y in [('#FLG1',54,19),('#FLG2',54,34),('#FLG3',54,49)]:b.place(ref,x,y);b.mark(ref,1)
    for i in range(1,5):b.place('H'+str(i),5+i*15,65)

def power(d):
    d.paper=(841,730);d.text('MORI / POWER CONDITIONER / S2',6,7,2.6)
    d.text('Power flows left to right. Supplies above, returns below. PROTOTYPE / UNVALIDATED.',6,11,1.2)
    b=block(d,'01  Pack input / reverse protection / shunt',5,15,104,65,'External pack, fuse and master switch precede J1. No charger on this PCB.')
    b.place('J1',12,25,orient='r');b.place('Q1',39,26,kind='pmos',orient='hr');b.place('R2',70,26,short='10mR / 1% / 1W');b.place('C2',91,37,orient='v')
    b.join(('J1',2),('Q1',5));b.join(('Q1',1),('R2',1))
    b.join(('R2',2),('C2',1),via=[(91,26)]);b.supply('C2',2,up=False)
    b.place('D1',56,39,kind='zener',orient='v');b.place('R1',39,51,orient='v')
    b.join(('D1',1),('Q1',1),via=[(56,26)]);b.join(('Q1',4),('D1',2),via=[(39,42)])
    b.join(('Q1',4),('R1',1));b.supply('R1',2,up=False)
    b=block(d,'02  Kelvin current sense',5,82,104,51,'Sense from the shunt pads. Discharge-only nominal transfer: 0.2 V/A.')
    b.place('U1',62,27,pins={'3':(-11,-5,'L'),'4':(-11,5,'L'),'1':(11,0,'R'),'5':(0,-10,'T'),'2':(0,10,'B')},w=18,h=16)
    b.place('R3',30,22);b.place('R4',30,32);b.join(('R3',2),('U1',3));b.join(('R4',2),('U1',4));b.mark('R3',1);b.mark('R4',1);decouple(b,'C1',88,26)
    for base,prefix,x,title in [(10,'W',111,'03  Wheel 9 V conditioning'),(30,'H',218,'04  Head 6 V conditioning')]:
        b=block(d,title,x,15,105,86,'External buck return. Inrush, brake energy and thermal performance: NOT_TESTED.')
        jin='J3' if base==10 else 'J5';qf='Q'+str(base);dn='D'+str(base);rs='R'+str(base);rg='R'+str(base+1);qd='Q'+str(base+1);cap='C'+str(base)
        b.place(jin,10,23,orient='r');b.place(dn,29,24,kind='schottky',orient='hr');b.place(qf,54,24,kind='pmos');b.place(cap,76,41,kind='cp',orient='v',short='1000u / 16V')
        b.join((jin,2),(dn,2));b.join((dn,1),(qf,1));b.join((qf,5),(cap,1),via=[(76,24)]);b.supply(cap,2,up=False)
        b.place(rs,42,36,orient='vu');b.join((qf,1),(rs,2),via=[(42,24)])
        b.place(rg,54,43,orient='v');b.join((qf,4),(rg,1));b.join((rs,1),(rg,1))
        b.place(qd,52,61,kind='nmos');b.join((rg,2),(qd,3));b.supply(qd,2,up=False)
        if base==10:
            b.place('J7',94,25);b.place('J8',94,60);b.join((cap,1),('J7',2),via=[(76,25)])
            b.join(('J7',2),('J8',2),via=[(86,25),(86,60)])
            b.place('J13',14,61,orient='r');b.mark('J13',1)
        else:
            b.place('J9',94,25);b.join((cap,1),('J9',2),via=[(76,25)])
            b.place('J14',14,61,orient='r');b.mark('J14',1)
    b=block(d,'05  External converter input distribution',5,135,104,44,'J2 -> wheel buck; J4 -> head buck; J6 -> two independent 5 V converters.')
    for ref,x in [('J2',19),('J4',48),('J6',78)]:b.place(ref,x,24,orient='r');b.mark(ref,1);b.mark(ref,2)
    for base,prefix,x,title in [(20,'W',111,'06  Wheel rail / brake and overvoltage'),(40,'H',218,'07  Head rail / brake and overvoltage')]:
        b=block(d,title,x,103,105,116,'Two comparators share one LM393B. External dump resistor needs pulse qualification.')
        # One native symbol contains both comparator functions; physical pins
        # and reference stay unchanged, inputs align with their own dividers.
        pins={'3':(-13,-16,'L'),'2':(-13,-10,'L'),'5':(-13,15,'L'),'6':(-13,21,'L'),'1':(13,-13,'R'),'7':(13,18,'R'),'8':(0,-25,'T'),'4':(0,28,'B')}
        b.place('U'+str(base),56,58,kind='dualcmp',pins=pins,w=22,h=48,short='LM393B / brake + fault',caption_at=(58,26))
        ur='U'+str(base+1);b.place(ur,19,60,pins={'1':(0,-6,'T'),'2':(-6,0,'L'),'3':(0,6,'B')},w=8,h=8)
        b.place('R'+str(base),19,38,orient='v');b.join(('R'+str(base),2),(ur,1));b.supply('R'+str(base),1)
        b.join((ur,1),(ur,2),via=[(9,54),(9,60)]);b.supply(ur,3,up=False)
        b.join((ur,1),('U'+str(base),2),via=[(28,54),(28,48)])
        b.mark('U'+str(base),5,length=1.5)
        rt='R'+str(base+1);rb='R'+str(base+2);rh='R'+str(base+3);rp='R'+str(base+4)
        b.place(rt,35,29,orient='v');b.place(rb,35,55,orient='v');b.supply(rt,1);b.join((rt,2),(rb,1));b.join((rt,2),('U'+str(base),3),via=[(35,42)]);b.supply(rb,2,up=False)
        b.place(rh,57,16,orient='hr');b.join((rh,1),('U'+str(base),1),via=[(74,16),(74,45)]);b.join((rh,2),('U'+str(base),3),via=[(28,16),(28,42)])
        b.place(rp,78,30,orient='v');b.supply(rp,1);b.join((rp,2),('U'+str(base),1),via=[(78,45)])
        qf='Q'+str(base);b.place(qf,87,51,kind='nmos');b.join(('U'+str(base),1),(qf,1),via=[(78,45),(78,51)]);b.supply(qf,2,up=False)
        jd='J11' if base==20 else 'J12';b.place(jd,89,32,pins={'2':(0,-4,'T'),'1':(0,4,'B')},w=4,h=4,short='5R6 / 5W external' if base==20 else '10R / 5W external')
        b.join((jd,1),(qf,3));b.supply(jd,2)
        b.place('D'+str(base),88,75,kind='zener',orient='v');b.mark('D'+str(base),1);b.supply('D'+str(base),2,up=False)
        top='R'+str(base+5);bot='R'+str(base+6);cc='C'+str(base+1)
        b.place(top,35,72,orient='v');b.place(bot,35,96,orient='v');b.supply(top,1);b.join((top,2),(bot,1));b.join((top,2),('U'+str(base),6),via=[(35,79)]);b.supply(bot,2,up=False)
        b.place(cc,45,96,orient='v');b.join((bot,1),(cc,1));b.supply(cc,2,up=False);decouple(b,'C'+str(base),68,99)
    b=block(d,'08  Voltage monitor / motion connector',5,181,104,56,'Divider ratio 27 / 127. Current_ADC comes from block 02.')
    b.place('J10',85,29)
    for rt,rb,x,pn in [('R50','R51',20,5),('R52','R53',41,6)]:
        b.place(rt,x,17,orient='v');b.place(rb,x,41,orient='v');b.supply(rt,1);b.join((rt,2),(rb,1));yy=b.pin('J10',pn)[1]
        b.join((rt,2),('J10',pn),via=[(x,yy)]);b.supply(rb,2,up=False)
    b.place('R54',63,43,orient='v');b.mark('R54',1);b.supply('R54',2,up=False)
    b=block(d,'09  Charge insertion / VBUS sense',111,221,105,46,'Sense and interlock only; no CC / PD / CC-CV charger implementation.')
    b.place('J16',11,23,orient='r');b.place('R55',35,22);b.place('Q50',61,22,kind='npn');b.place('R56',47,34,orient='v');b.place('J15',91,20)
    b.join(('J16',1),('R55',1));b.join(('R55',2),('Q50',1));b.join(('R55',2),('R56',1),via=[(47,22)]);b.supply('R56',2,up=False);b.supply('Q50',2,up=False)
    b.join(('Q50',3),('J15',1),via=[(78,17),(78,19)])
    b=block(d,'10  Supply boundaries / board mounting',218,221,105,46,'80 x 45 mm PCB; populated assembly and thermal performance are not qualified.')
    for i in range(1,6):b.place('#FLG'+str(i),6+i*17,17);b.mark('#FLG'+str(i),1)
    for i in range(1,5):b.place('H'+str(i),10+i*20,34)

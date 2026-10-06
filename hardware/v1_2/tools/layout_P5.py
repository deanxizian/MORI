#!/usr/bin/env python3
"""New P5 placement, independent of all previous copper.

Use KiCad's bundled Python. Never writes P4 or mechanical-owned files.
"""
from pathlib import Path
from collections import defaultdict
import pcbnew as k
import json,math,sys,hashlib
from layout_P3R1 import setplace,xy,pt,mm,F,B,track,via,area
from audit_body_routes_P4 import rect

H=Path(__file__).resolve().parents[1]; O=H/'layout_P5'
def paths(kind):
    n=f'MORI_{kind}_P5';d=H/'kicad'/n;r=O/'reports'/n;r.mkdir(parents=True,exist_ok=True)
    return n,d,d/(n+'.kicad_pcb'),r

def box(f):
    shapes=[s.GetBoundingBox() for s in f.GraphicalItems() if isinstance(s,k.PCB_SHAPE) and s.GetLayer() in [k.F_Fab,k.B_Fab]]
    shapes += [p.GetBoundingBox() for p in f.Pads()]
    return [min(k.ToMM(s.GetX()) for s in shapes),min(k.ToMM(s.GetY()) for s in shapes),max(k.ToMM(s.GetRight()) for s in shapes),max(k.ToMM(s.GetBottom()) for s in shapes)]

def hit(a,b,gap=.5):return a[0]<b[2]+gap and a[2]>b[0]-gap and a[1]<b[3]+gap and a[3]>b[1]-gap

def courtyard(f):
    ss=[s.GetBoundingBox() for s in f.GraphicalItems() if isinstance(s,k.PCB_SHAPE) and s.GetLayer() in [k.F_CrtYd,k.B_CrtYd]]
    if not ss:return box(f)
    return [min(k.ToMM(s.GetX()) for s in ss),min(k.ToMM(s.GetY()) for s in ss),max(k.ToMM(s.GetRight()) for s in ss),max(k.ToMM(s.GetBottom()) for s in ss)]

MOTION={
 'J1':(58.5,3,0),'J2':(51,3,0),'J5':(66,13.5,90),
 'J4':(51,26.5,90),'J7':(60.4,9,-90),'J3':(66,24.5,90),
 'J6':(51,31.7,0),'J8':(58.5,31.7,0),
 'U5':(11,9.5,0),'U3':(19,11.5,0),'U1':(28,9,0),'U4':(39,10,0),
 'U6':(8,18,90),'U2':(21,23.5,90),
 'C5':(14.5,10.25,0),'C3':(22.5,12.25,0),'C1':(31.5,9.75,0),
 'C4':(42.5,9.25,0),'C7':(42.5,12,0),'C6':(8,15,90),
 'C2':(24.5,22.75,0),'C8':(46,6,90),
 'C9':(11.5,28,90),'C10':(15,28,90),'C11':(18,28,90),'C12':(8,21,180),
 'R1':(30.5,6.5,90),'R2':(24.5,19,90),'R3':(15,7.5,90),'R4':(18,7.5,90),
 'R5':(7,10.25,180),'R6':(42,26,90),'R7':(11.5,21,180),
 'R8':(47,29,90),'R9':(45,13.5,90),
 'R10':(26.5,27,0),'R11':(29.5,27,90),'R12':(23.5,27,90),'R13':(46,20,90),
 'R14':(11.5,25,90),'R15':(15,25,90),'R16':(18,25,90),
 'R17':(16,17,90),'R18':(29,21,90),'R19':(33,16,0),
 'D1':(34,21,0),'D2':(13,15.5,90),'D3':(27,17.5,90)}

def power_homes():
    d={
     'J1':(9,6,0),'J2':(22,6,0),'J3':(35,6,0),'J11':(61,6,0),
     'J4':(25,50,0),'J5':(40,50,0),'J6':(48,6,0),
     'J7':(75,19,90),'J8':(63,25,0),'J9':(64,42.5,0),'J12':(65,50,0),
     'J10':(44,27,-90),'J13':(75,34,90),'J14':(75,43,90),
     'J15':(4.5,31,90),'J16':(4.5,46,90),'J17':(4.5,24,90),
     'J18':(13,50,0),'J19':(4.5,17,90),
     'Q90':(13,12,0),'Q1':(23,12,180),'R2':(34,12,0),
     'R90':(7,12,90),'D90':(8,8.5,0),'R91':(8.5,17.5,90),
     'R1':(22,17.5,0),'D1':(26,17.5,0),
     'U1':(34,18.5,0),'R3':(30,16.5,90),'R4':(38,16.5,90),'C1':(37,21.5,90),'C2':(40,11,90),
     'D10':(44,12,90),'Q10':(50,12,0),'Q11':(42,18.5,0),'R10':(48,17,0),'R11':(44.5,17,0),
     'C10':(52,22,0),'Q30':(51,34,0),'D30':(36,35,90),'Q31':(55.5,35.5,0),
     'R30':(49,29.5,0),'R31':(46.5,35,90),'C30':(53,44,0),
     'R50':(37,25,0),'R51':(40,25,0),'R52':(48,26.5,0),'R53':(51.5,27.5,0),
     'R54':(46,45.5,0),'Q50':(11,41,0),'R55':(10,44.5,90),'R56':(14,42,90),
     'U20':(66,14,0),'U21':(59.5,13.5,0),'Q20':(72,8,0),'D20':(73,12,90),
     'R20':(60.5,10,90),'R21':(62,18.8,0),'R22':(62,20.8,0),'R23':(65.5,18.8,0),
     'R24':(69,18.8,0),'R25':(65.5,20.8,0),'R26':(69,20.8,0),'C20':(71,14,90),'C21':(69,22.6,0),
     'U40':(65,34.5,0),'U41':(58.5,32,0),'Q40':(57,52,0),'D40':(60,49,90),
     'R40':(58.5,27.5,90),'R41':(63,38.0,0),'R42':(66.5,38.0,0),'R43':(64,30.7,0),
     'R44':(70,30,90),'R45':(70,38.0,0),'R46':(54.5,28.8,0),'C40':(70,33,90),'C41':(72,40,90)}
    for n,cy in [(60,26),(70,40)]:
        d.update({f'U{n}':(25,cy,0),f'L{n}':(16.5,cy-2,180),
          f'F{n}':(34,cy-3,180),f'C{n}':(20,cy+4.5,180),f'C{n+6}':(26,cy+5,180),
          f'C{n+1}':(22,cy+1.5,270),f'C{n+2}':(26,cy-3,180),
          f'C{n+3}':(10.5,cy-3,90),f'C{n+4}':(10.5,cy+2,90),
          f'C{n+5}':(29,cy+3,90),f'R{n}':(32,cy+3,90),f'R{n+1}':(30.5,cy+5,180),
          f'JP{n}':(32,cy,0),f'TP{n}':(8,cy+4.5,0),f'TP{n+1}':(12,cy+5.5,0)})
    d['JP60']=(36.5,27,90)
    d['JP70']=(36.5,44.5,90)
    d['TP70']=(35,51,0)
    d['TP71']=(33.5,47.5,0)
    return d

def placement(kind,b):
    fps={f.GetReference():f for f in b.GetFootprints()}
    if kind=='motion':homes={r:(*v,'F' if r.startswith('J') else 'B') for r,v in MOTION.items()}
    elif kind=='power':homes={r:(*v,'F') for r,v in power_homes().items()}
    elif kind=='imu':homes={r:(*v,'F') for r,v in {
        'J1':(3,3.5,0),'U1':(10,9.6,0),'R1':(6.5,8.85,180),'R2':(14.4,7.8,0),
        'C1':(13.2,9.9,90),'C2':(12.5,12.9,180),'C3':(9.5,12.5,270)}.items()}
    else:homes={r:(*v[:3],v[3]) for r,v in {
        'USB1':(12,3,0,'B'),'SW1':(12,12.9,0,'F'),
        'J2':(19,15.7,270,'B'),'J3':(8.7,19.5,0,'F'),
        'F1':(4.6,4.4,270,'B'),'D1':(19.5,6,90,'B'),
        'D2':(10.75,10,270,'B'),'D3':(13.75,10,270,'B'),'C1':(4.6,15.5,90,'B')}.items()}
    expected={r for r in fps if not r.startswith('H') and r!='U100'}
    assert set(homes)==expected,(kind,'unplaced',expected-set(homes),'unknown',set(homes)-expected)
    for r,v in homes.items():setplace(fps[r],*v[:3],side=v[3])
    return homes

def pack(kind,b,homes):
    """Compare body/pad-valid translations and all four rotations, then score
    peer distance AND outward pin direction. This is placement screening,
    never a routing or thermal PASS.
    """
    fps={f.GetReference():f for f in b.GetFootprints()};W,Hh={'motion':(70,35),'power':(80,55),'imu':(20,16),'rear':(24,25)}[kind]
    placed=[r for r in fps if r not in homes];logs=[]
    boxes={r:box(fps[r]) for r in placed};courts={r:courtyard(fps[r]) for r in placed};padboxes={}
    def save_padboxes(ref):
        padboxes[ref]=[]
        for p in fps[ref].Pads():
            if p.GetAttribute() not in [k.PAD_ATTRIB_PTH,k.PAD_ATTRIB_NPTH]:continue
            bb=p.GetBoundingBox();padboxes[ref].append([k.ToMM(v) for v in [bb.GetX(),bb.GetY(),bb.GetRight(),bb.GetBottom()]])
    for r in placed:save_padboxes(r)
    fixed={'USB1','SW1','J2','J3','D2','D3','F1'} if kind=='rear' else {'U1','J1'} if kind=='imu' else {r for r in homes if r.startswith('J')} if kind=='motion' else set()
    netpads=defaultdict(list)
    for f in fps.values():
        for p in f.Pads():
            if p.GetNetname() and not p.GetNetname().startswith('unconnected-'):netpads[p.GetNetname()].append((f,p))
    def score(f,origin):
        s=0.;cx,cy=xy(f.GetPosition())
        for pad in f.Pads():
            nn=pad.GetNetname();ps=peers.get(nn,[])
            if not ps or nn in ['/GND','/+3V3','/BAT_MON','/W_VM','/H_VM'] or len(ps)>10:continue
            px,py=xy(pad.GetPosition());qx,qy=min(ps,key=lambda p:math.dist((px,py),p))
            s+=.28*math.dist((px,py),(qx,qy))
            nx,ny=px-cx,py-cy;dot=nx*(qx-px)+ny*(qy-py)
            if dot<0:s+=.35*min(6.,-dot/max(math.hypot(nx,ny),.1))
        s+=1.8*math.dist((cx,cy),origin)
        return s
    def legal(ref):
        f=fps[ref];a=box(f);ac=courtyard(f)
        # Rear socket bodies deliberately overhang the port/end edge.
        if not (kind=='rear' and ref in ['USB1','J2']):
            if a[0]<.4 or a[1]<.4 or a[2]>W-.4 or a[3]>Hh-.4:return False
        if kind=='rear' and not f.IsFlipped() and ref not in ['SW1']:
            if any(hit(a,s,0) for s in [[0,0,6.5,14],[17.5,0,24,14]]):return False
        for other in placed:
            g=fps[other]
            if f.IsFlipped()==g.IsFlipped() and hit(ac,courts[other],.02):return False
            if other=='U100' and f.IsFlipped():
                # Raised module projection is an explicit architecture issue,
                # not a universal component-body exception.
                if any(hit(a,r,.45) for r in padboxes[other]):return False
                continue
            # Actual opposite-side components must not create body-routing
            # tunnels. Housing overlap with the rear fixed switch is retained
            # only for the mechanical interface, not to permit under-routing.
            if kind=='rear' and f.IsFlipped()!=g.IsFlipped():
                if any(hit(a,r,.35) for r in padboxes[other]):return False
                continue
            if other.startswith('H'):
                x,y=xy(g.GetPosition());r=[x-2.7,y-2.7,x+2.7,y+2.7]
                if hit(a,r,0):return False
            elif hit(a,boxes[other],.2 if kind=='rear' else .35 if ref.startswith('C') else .55):return False
        return True
    def priority(r):
        return (0 if r in fixed else 1 if r.startswith('J') and not r.startswith('JP') else 2 if r in ['C10','C30','L60','L70'] else 3 if r.startswith('U') else 3.2 if kind=='power' and r in ['C61','C71','C62','C72'] else 3.5 if kind=='power' and r in ['C60','C63','C64','C66','C70','C73','C74','C76'] else 4 if r.startswith(('Q','D','F','JP')) else 5,r)
    for ref in sorted(homes,key=priority):
        x,y,a,side=homes[ref];f=fps[ref]
        peers={nn:[xy(p.GetPosition()) for other,p in ps if other!=f] for nn,ps in netpads.items()}
        radius=0 if ref in fixed or (kind=='power' and ref in ['C61','C71']) else 2 if ref.startswith('J') else 2.5 if ref.startswith('U') else 4
        angles=[a] if ref in fixed or ref.startswith(('J','U60','U70','L60','L70')) or (kind=='power' and ref in ['C61','C71']) else [a]+[z for z in [0,90,180,270] if (z-a)%360]
        offsets=sorted([(i*.5,j*.5) for i in range(-int(2*radius),int(2*radius)+1) for j in range(-int(2*radius),int(2*radius)+1)],key=lambda v:(v[0]**2+v[1]**2,v))
        best=None;valid=[];trials=0
        for dx,dy in offsets:
            if best is not None and 1.8*math.hypot(dx,dy)>best[0]:continue
            for ang in angles:
                setplace(f,x+dx,y+dy,ang,side);trials+=1
                if not legal(ref):continue
                s=score(f,(x,y));valid.append((s,x+dx,y+dy,ang))
                if best is None or (s,x+dx,y+dy,ang)<best:best=(s,x+dx,y+dy,ang)
        if best is None:
            setplace(f,x,y,a,side)
            paths(kind)[3].joinpath('pack_incomplete.json').write_text(json.dumps(dict(failed_ref=ref,placed=logs,boxes={rr:box(fps[rr]) for rr in placed}),indent=2)+'\n')
            raise RuntimeError(('no legal P5 placement',kind,ref,(x,y,a,side),'placed',placed))
        _,xx,yy,ang=best;setplace(f,xx,yy,ang,side);placed.append(ref);boxes[ref]=box(f);courts[ref]=courtyard(f);save_padboxes(ref)
        by_angle={str(z):min((v[0] for v in valid if v[3]==z),default=None) for z in angles}
        logs.append(dict(ref=ref,new_home=[x,y,a,side],selected=[xx,yy,ang,side],trials=trials,legal_trials=len(valid),best_score_by_rotation=by_angle,route_validation='NOT_TESTED'))
    return logs

def make_body_areas(b,kind):
    from body_keepouts_P3R1 import create
    log=create(b)
    # The same body is protected on BOTH outer copper layers. Pad escape
    # windows stay local; a layer change is not an exemption.
    for z in list(b.Zones()):
        if not z.GetIsRuleArea() or not z.GetZoneName().startswith(('BODY_','NETBODY_')):continue
        c=k.ZONE(b);c.SetIsRuleArea(True);c.SetLayer(B if z.GetLayer()==F else F)
        c.SetZoneName(z.GetZoneName()+'_OPPOSITE');c.SetDoNotAllowTracks(z.GetDoNotAllowTracks());c.SetDoNotAllowVias(z.GetDoNotAllowVias())
        c.SetDoNotAllowPads(False);c.SetDoNotAllowFootprints(False);c.SetDoNotAllowZoneFills(False);c.Outline().BooleanAdd(z.Outline());b.Add(c)
    return log

def init(kind):
    name,d,p,r=paths(kind);b=k.LoadBoard(str(p));before={t.m_Uuid.AsString() for t in b.GetTracks()};fps={f.GetReference():f for f in b.GetFootprints()}
    for t in list(b.GetTracks()):b.Delete(t)
    # Retain only the real mount/seat/vendor restrictions; old placement
    # body areas and copper planes are regenerated.
    keep=[]
    for z in list(b.Zones()):
        zn=z.GetZoneName()
        if z.GetIsRuleArea() and not zn.startswith(('BODY_','NETBODY_','OUTWARD_','TDK_')):keep.append(zn)
        else:b.Delete(z)
    for item in list(b.GetDrawings()):
        if isinstance(item,k.PCB_TEXT):b.Delete(item)
    for f in fps.values():
        f.Reference().SetVisible(False);f.Value().SetVisible(False)
    k.SaveBoard(str(p),b)
    homes=placement(kind,b);log=pack(kind,b,homes)
    body=make_body_areas(b,kind)
    # Preserve explicit no-inner-signal constraints in the native project.
    b.GetTitleBlock().SetTitle('MORI '+kind+' P5 - NEW LAYOUT / PROTOTYPE')
    b.GetTitleBlock().SetRevision('V1.2-H0.5-P5')
    b.GetTitleBlock().SetComment(0,'NEW PLACEMENT; ROUTING/THERMAL/ASSEMBLY NOT VALIDATED')
    k.SaveBoard(str(p),b)
    assert not list(b.GetTracks())
    (r/'zero_old_copper.json').write_text(json.dumps(dict(removed_tracks_and_vias=len(before),remaining_tracks_and_vias=0,retained_mechanical_rule_areas=keep,source_revision='P4',claim='New routing will start from this zero-copper checkpoint'),indent=2)+'\n')
    (r/'placement_trials.json').write_text(json.dumps(log,indent=2)+'\n')
    (r/'body_areas.json').write_text(json.dumps(body,indent=2)+'\n')
    update(kind,b)
    k.SaveBoard(str(r/'placement_only.kicad_pcb'),b)
    print(kind,'new placement',len(log),'components; zero inherited tracks/vias',flush=True)

def update(kind,b):
    name,d,p,r=paths(kind);data=json.loads((d/'connectivity.json').read_text());fps={f.GetReference():f for f in b.GetFootprints()}
    for c in data['components']:
        if c['ref'] in fps:
            f=fps[c['ref']];c.update(placed_at=[*xy(f.GetPosition()),f.GetOrientationDegrees()],side='B' if f.IsFlipped() else 'F')
    data.update(revision='V1.2-H0.5-P5',layout_revision='P5',pcb_status='PROTOTYPE / IN_PROGRESS / NOT_VALIDATED')
    (d/'connectivity.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    rows=[dict(ref=f.GetReference(),xy=xy(f.GetPosition()),angle=f.GetOrientationDegrees(),side='B' if f.IsFlipped() else 'F',box_mm=box(f),pads=[dict(pin=q.GetNumber(),net=q.GetNetname(),xy=xy(q.GetPosition())) for q in f.Pads()]) for f in b.GetFootprints()]
    (r/'placement.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':
    for kind in sys.argv[1:] or ['motion','imu','power','rear']:init(kind)

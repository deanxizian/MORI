#!/usr/bin/env python3
"""P3R1 placement and routing primitives. KiCad Python; writes P3R1 only.

Native schematic export is the net authority; no approximate label parser.
"""
from pathlib import Path
from collections import defaultdict
import csv, hashlib, json, math, re, subprocess, sys
import pcbnew as k

H=Path(__file__).resolve().parents[1]
O=H/'layout_P3R1'; CLI='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
mm=k.FromMM; pt=lambda x,y:k.VECTOR2I(mm(x),mm(y))
xy=lambda p:(k.ToMM(p.x),k.ToMM(p.y))
F=k.F_Cu; B=k.B_Cu

def paths(kind):
    name='MORI_'+kind+'_P3R1';d=H/'kicad'/name;r=O/'reports'/name;r.mkdir(parents=True,exist_ok=True)
    return name,d,d/(name+'.kicad_pcb'),r

def track(b,net,points,width=.2,layer=F):
    if isinstance(net,str):net=b.GetNetsByName()[net if net.startswith('/') else '/'+net]
    out=[]
    for a,c in zip(points,points[1:]):
        if math.dist(a,c)<.00001:continue
        t=k.PCB_TRACK(b);t.SetStart(pt(*a));t.SetEnd(pt(*c));t.SetWidth(mm(width));t.SetLayer(layer);t.SetNet(net);b.Add(t);out.append(t)
    return out

def via(b,net,x,y,vd=.8,dr=.3,grid=True):
    if isinstance(net,str):net=b.GetNetsByName()[net if net.startswith('/') else '/'+net]
    if grid:x,y=[round(v/.0254)*.0254 for v in (x,y)]
    v=k.PCB_VIA(b);v.SetPosition(pt(x,y));v.SetWidth(mm(vd));v.SetDrill(mm(dr));v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(F,B);v.SetNet(net);v.SetFrontTentingMode(k.TENTING_MODE_NOT_TENTED);b.Add(v)
    return xy(v.GetPosition())

def configure(kind,b,d,name):
    # Keep the user's complete 47-rule mapping, including original priorities.
    import layout_P2, rules_P2, rules_P3R1
    old=rules_P2.write_rules
    rules_P2.write_rules=rules_P3R1.write_rules
    try:layout_P2.configure(kind,b,d,name)
    finally:rules_P2.write_rules=old
    p=json.loads((d/(name+'.kicad_pro')).read_text())
    p['meta']['filename']=name+'.kicad_pro'
    p['board']['design_settings']['drc_exclusions']=[]
    # Small-current feedback/sense branches do not inherit the ampere bus width.
    if kind=='power':
        ns=b.GetDesignSettings().m_NetSettings
        entries=[('Logic5V',.8,.2,1.,.45),('BuckInput',.8,.2,1.,.45),('Switch',.6,.2,1.,.45)]
        for label,width,cl,vd,dr in entries:
            nc=k.NETCLASS(label);nc.SetTrackWidth(mm(width));nc.SetClearance(mm(cl));nc.SetViaDiameter(mm(vd));nc.SetViaDrill(mm(dr));ns.SetNetclass(label,nc)
            p['net_settings']['classes'].append(dict(name=label,track_width=width,clearance=cl,via_diameter=vd,via_drill=dr))
        for name_,cl in [('M5_VIN','BuckInput'),('C5_VIN','BuckInput'),('M5_SW','Switch'),('C5_SW','Switch'),('+5V_MOTION','Logic5V'),('+5V_CAM','Logic5V')]:
            nn='/'+name_;ns.SetNetclassPatternAssignment(nn,cl);p['net_settings']['netclass_patterns']=[x for x in p['net_settings']['netclass_patterns'] if x['pattern']!=nn];p['net_settings']['netclass_patterns'].append(dict(pattern=nn,netclass=cl))
        ns.RecomputeEffectiveNetclasses()
    (d/(name+'.kicad_pro')).write_text(json.dumps(p,indent=2)+'\n')

def setplace(fp,x,y,angle=0,side='F'):
    if fp.IsFlipped() != (side=='B'):fp.Flip(fp.GetPosition(),False)
    fp.SetOrientationDegrees(angle);fp.SetPosition(pt(x,y))

def build(kind):
    name,d,pcb,r=paths(kind);data=json.loads((d/'connectivity.json').read_text())
    cmd=[CLI,'sch','export','netlist','--format','kicadxml','-o',str(r/'netlist.xml'),str(d/(name+'.kicad_sch'))]
    run=subprocess.run(cmd,capture_output=True,text=True,check=True);(r/'netlist.log').write_text(run.stdout+run.stderr)
    import xml.etree.ElementTree as ET
    actual={}
    for n in ET.parse(r/'netlist.xml').getroot().findall('.//nets/net'):
        for node in n.findall('node'):actual[node.attrib['ref'],node.attrib['pin']]=n.attrib['name']
    source=H/'kicad'/('MORI_'+kind+'_P2')/('MORI_'+kind+'_P2.kicad_pcb')
    b=k.LoadBoard(str(source));b.SetFileName(str(pcb))
    for group in list(b.Groups()):b.Delete(group)
    for item in list(b.GetTracks())+list(b.Zones())+list(b.GetDrawings())+list(b.GetFootprints()):b.Delete(item)
    nets={str(n):v for n,v in b.GetNetsByName().items()}
    for n in set(actual.values()):
        if n not in nets:net=k.NETINFO_ITEM(b,n);b.Add(net);nets[n]=net
    root=re.search(r'\(uuid ([0-9a-f-]+)\)',(d/(name+'.kicad_sch')).read_text()).group(1)
    for c in data['components']:
        if not c['footprint']:continue
        lib,fn=c['footprint'].split(':');fp=k.FootprintLoad(str(d/'footprints'/(lib+'.pretty')),fn)
        assert fp,(c['ref'],c['footprint'])
        fp.SetReference(c['ref']);fp.SetValue(c['value']);fp.SetFPID(k.LIB_ID(lib,fn));fp.SetPath(k.KIID_PATH('/'+root+'/'+c['uuid']))
        fp.SetField('Datasheet',c.get('source',''));fp.SetDNP(c.get('dnp',False));fp.SetExcludedFromBOM(False);b.Add(fp)
        fp.Reference().SetVisible(False);fp.Value().SetVisible(False)
        for p in fp.Pads():
            key=(c['ref'],p.GetNumber())
            if key in actual:p.SetNet(nets[actual[key]])
            elif p.GetNumber() not in ['', 'MP'] and p.GetNumber() not in c['pins']:raise ValueError(('unmapped',key))
        pos=c.get('placed_at',c.get('at',[0,0,0]));setplace(fp,*pos,side=c.get('side','F'))
    w,h=data['size']
    for a,c in zip([(0,0),(w,0),(w,h),(0,h)],[(w,0),(w,h),(0,h),(0,0)]):
        sh=k.PCB_SHAPE();sh.SetShape(k.SHAPE_T_SEGMENT);sh.SetStart(pt(*a));sh.SetEnd(pt(*c));sh.SetLayer(k.Edge_Cuts);sh.SetWidth(mm(.05));b.Add(sh)
    configure(kind,b,d,name)
    place(kind,b,data)
    add_keepouts(kind,b)
    update_records(kind,b,data)
    k.SaveBoard(str(pcb),b)
    print(name,'new placement',len(b.GetFootprints()),'footprints; native netlist assigned',len(actual),'pins',flush=True)

def place(kind,b,data):
    fps={f.GetReference():f for f in b.GetFootprints()}
    if kind=='imu':
        targets={'U1':(9.875,9,0),'R1':(6.2,8.25,180),'R2':(6.5,13,90),
            'C1':(13,8.975,90),'C2':(12.5,12.5,180),'C3':(9,12.5,180)}
        for ref,v in targets.items():setplace(fps[ref],*v)
    elif kind=='motion':
        targets={'U1':(28,10,0),'U2':(21,23.5,0),'U3':(17,11,0),'U4':(36,12,0),'U5':(10,11,0),'U6':(7,17,0),
            'C1':(28,7.5,0),'C2':(21,21,0),'C3':(17,8.5,0),'C4':(36,9,0),'C5':(10,8,0),'C6':(7,14,0),'C7':(39,12,90),
            'C8':(46,5,0),'C9':(11.5,27,90),'C10':(15,27,90),'C11':(18,27,90),'C12':(7,20,0),
            'R1':(32,10,90),'R2':(24,23.5,90),'R3':(14,8,90),'R4':(20,8,90),'R5':(6.5,10,90),
            'R6':(42,25,0),'R7':(10,20,90),'R8':(57,25,0),'R9':(42,12,90),'R10':(27,26,90),'R11':(31,26,90),'R12':(24,26,90),
            'R13':(48,19,90),'R14':(11.5,24,90),'R15':(15,24,90),'R16':(18,24,90),'R17':(16,16,90),'R18':(29,23,90),'R19':(38,18,0),
            'D1':(34,17,0),'D2':(13,16,90),'D3':(28,19,90)}
        for ref,v in targets.items():setplace(fps[ref],*v,side='B')
    else:
        targets={
            'H1':(3,3,0,'F'),'H2':(3,52,0,'F'),'H3':(77,3,0,'F'),'H4':(77,52,0,'F'),
            'J1':(9,7,0,'F'),'J2':(23,7,0,'F'),'J3':(40,7,0,'F'),'J4':(4,33,90,'F'),'J5':(4,46,90,'F'),
            'J6':(40,51,0,'F'),'J7':(62,18,0,'F'),'J8':(63,28,0,'F'),'J9':(50,49,0,'F'),
            'J10':(45,29,0,'F'),'J11':(65,7,0,'F'),'J12':(65,48,0,'F'),'J13':(76,18,90,'F'),
            'J14':(76,31,90,'F'),'J15':(56,30,0,'F'),'J16':(74,38,90,'F'),
            'Q1':(13,15,180,'B'),'R2':(25,15,0,'B'),'R1':(14,20,0,'B'),'D1':(19,15,90,'B'),
            'U1':(25,21,0,'B'),'R3':(21,19,270,'B'),'R4':(29,19,270,'B'),'C1':(27,23.5,0,'B'),'C2':(30,12,90,'B'),
            'D10':(48,14,0,'B'),'Q10':(43,22,90,'B'),'Q11':(39,27,0,'B'),'R10':(39,19,90,'B'),'R11':(39,23,90,'B'),
            'C10':(48,20,0,'F'),'D30':(25,38,0,'B'),'Q30':(37,38,0,'B'),'Q31':(39,32,0,'B'),'R30':(35,34,0,'B'),'R31':(38,35,0,'B'),
            'C30':(47,38,0,'F'),'U20':(63,16,0,'B'),'U21':(55,15,0,'B'),'Q20':(74,10,0,'B'),
            'U40':(63,39,0,'B'),'U41':(55,38,0,'B'),'Q40':(73,45,0,'B'),
            'R50':(32,20,90,'B'),'R51':(32,23,90,'B'),'R52':(35,20,90,'B'),'R53':(35,23,90,'B'),
            'R54':(42,31.5,0,'B'),'R55':(72,35,0,'B'),'R56':(69,35,90,'B'),'Q50':(66,33,0,'B')}
        # Two comparator blocks; tentative passives subsequently optimized as groups.
        for n,dy in [(20,0),(40,23)]:
            for off,x,y,angle in [(0,55,11,90),(1,59,22,90),(2,59,25,90),(3,61.5,20,0),(4,67,11,90),(5,67,22,90),(6,67,25,90)]:targets['R'+str(n+off)]=(x,y+dy,angle,'B')
            targets['D'+str(n)]=(72,15+dy,90,'B');targets['C'+str(n)]=(65,12+dy,0,'B');targets['C'+str(n+1)]=(70,22+dy,90,'B')
        for n,uy in [(60,23),(70,43)]:
            targets['U'+str(n)]=(30,uy,0,'F');targets['L'+str(n)]=(20.5,uy-3,180,'F')
            for off,x,y,a in [(0,23,uy+3,180),(6,18.5,uy+5,90),(1,27,uy+2.8,0),
                (2,31,uy-3.5,180),(3,18,uy-10,90),(4,22,uy-10,90),(5,33.5,uy+2.5,90)]:targets['C'+str(n+off)]=(x,y,a,'F')
            targets['R'+str(n)]=(35.5,uy+2.5,90,'F');targets['R'+str(n+1)]=(34.5,uy+5,180,'F')
            targets['F'+str(n)]=(38,uy-10,0,'F');targets['JP'+str(n)]=(35,uy-6,0,'F')
            targets['TP'+str(n)]=(39.624,uy-4.05,0,'F');targets['TP'+str(n+1)]=(42.418,uy-4.05,0,'F')
        targets['J17']=(6,20,90,'F');targets['J18']=(12,50,0,'F')
        for ref,v in targets.items():setplace(fps[ref],*v[:3],side=v[3])
        missing=set(fps)-set(targets)
        if missing:raise RuntimeError(('no explicit power placement',missing))
    if kind=='motion':optimize(b,kind,list(targets),passes=2)
    if kind=='power':
        pack_power(b,targets)

def pack_power(b,targets):
    """Preserve functional neighborhoods; choose a clear location/rotation before routing."""
    fps={f.GetReference():f for f in b.GetFootprints()};placed=[];log=[]
    # Mechanical interfaces then high-energy parts then local controls/passives.
    refs=sorted(fps,key=lambda r:(0 if r.startswith('H') else 1 if r.startswith('J') and not r.startswith('JP') else 2 if r in ['C10','C30','L60','L70'] else 3 if r in ['U60','U70'] else 4 if r.startswith('C6') or r.startswith('C7') else 5 if r.startswith(('Q','D','F','U','JP','TP')) else 6,r))
    for ref in refs:
        f=fps[ref];ox,oy,oa,side=targets[ref];best=None;trials=0
        radius=0 if ref.startswith('H') else 3 if ref.startswith('J') and not ref.startswith('JP') else 4 if ref in ['U60','U70','L60','L70'] or ref.startswith(('C6','C7','R6','R7')) else 8
        step=.5;offsets=sorted([(i*step,j*step) for i in range(-int(radius/step),int(radius/step)+1) for j in range(-int(radius/step),int(radius/step)+1)],key=lambda v:(v[0]**2+v[1]**2,abs(v[1]),abs(v[0])))
        angles=[oa] if ref.startswith(('H','J','U60','U70','L60','L70')) else [oa]+[a for a in [0,90,180,270] if a!=oa]
        for dx,dy in offsets:
            displacement=dx*dx+dy*dy
            if best and displacement>best[0]:break
            for angle in angles:
                trials+=1;setplace(f,ox+dx,oy+dy,angle,side);a=bounds(f)
                if a[0]<.35 or a[1]<.35 or a[2]>79.65 or a[3]>54.65:continue
                ok=True
                for other in placed:
                    q=fps[other]
                    if f.IsFlipped()==q.IsFlipped() and intersects(a,bounds(q),.20):ok=False;break
                    if f.IsFlipped()!=q.IsFlipped() or other.startswith('H'):
                        for pad in q.Pads():
                            if pad.GetAttribute() not in [k.PAD_ATTRIB_PTH,k.PAD_ATTRIB_NPTH]:continue
                            x,y=xy(pad.GetPosition());ex=2.7 if other.startswith('H') else max(k.ToMM(pad.GetSize().x),k.ToMM(pad.GetSize().y))/2+.5
                            if intersects(a,[x-ex,y-ex,x+ex,y+ex]):ok=False;break
                    if not ok:break
                if not ok:continue
                score=displacement+(.10 if angle!=oa else 0)
                if best is None or score<best[0]:best=(score,ox+dx,oy+dy,angle)
        if best is None:raise RuntimeError(('cannot pack',ref,targets[ref]))
        _,x,y,angle=best;setplace(f,x,y,angle,side);placed.append(ref);log.append(dict(ref=ref,before=targets[ref],after=[x,y,angle,side],trials=trials,displacement_mm=math.dist([x,y],[ox,oy])))
    paths('power')[3].joinpath('orientation_trials.json').write_text(json.dumps(log,indent=2)+'\n')

def bounds(fp):
    bb=fp.GetBoundingBox(False,False);return [k.ToMM(x) for x in [bb.GetX(),bb.GetY(),bb.GetRight(),bb.GetBottom()]]

def intersects(a,b,extra=0):return not(a[2]+extra<=b[0] or a[0]>=b[2]+extra or a[3]+extra<=b[1] or a[1]>=b[3]+extra)

def optimize(b,kind,refs,passes=2):
    fps={f.GetReference():f for f in b.GetFootprints()};size={'motion':(70,35),'power':(80,55)}[kind];history=[]
    homes={r:xy(fps[r].GetPosition()) for r in refs};netpads=defaultdict(list)
    for f in fps.values():
        for p in f.Pads():
            if p.GetNetname():netpads[str(p.GetNetname())].append((f.GetReference(),p))
    def score(ref):
        f=fps[ref];s=0
        for p in f.Pads():
            nn=str(p.GetNetname());others=[q for rr,q in netpads[nn] if rr!=ref]
            if not others or len(others)>10 or 'unconnected-' in nn:continue
            s+=min(math.dist(xy(p.GetPosition()),xy(q.GetPosition())) for q in others)
        if ref.startswith('C') and ref[1:].isdigit() and int(ref[1:])<8 and kind=='motion':
            u=fps['U'+ref[1:]] if ref!='C7' else fps['U4']
            for p in f.Pads():
                peers=[q for q in u.Pads() if q.GetNetname()==p.GetNetname()]
                if peers:s+=4*min(math.dist(xy(p.GetPosition()),xy(q.GetPosition())) for q in peers)
        s+=.8*math.dist(xy(f.GetPosition()),homes[ref]);return s
    def legal(ref):
        f=fps[ref];a=bounds(f)
        if a[0]<.55 or a[1]<.55 or a[2]>size[0]-.55 or a[3]>size[1]-.55:return False
        for rr,q in fps.items():
            if rr==ref:continue
            if f.IsFlipped()==q.IsFlipped() and intersects(a,bounds(q),.15):return False
            if f.IsFlipped()!=q.IsFlipped() or rr.startswith('H'):
                for p in q.Pads():
                    if p.GetAttribute() not in [k.PAD_ATTRIB_PTH,k.PAD_ATTRIB_NPTH]:continue
                    x,y=xy(p.GetPosition());ex=2.7 if rr.startswith('H') else max(k.ToMM(p.GetSize().x),k.ToMM(p.GetSize().y))/2+.45
                    if intersects(a,[x-ex,y-ex,x+ex,y+ex]):return False
        return True
    for iteration in range(passes):
        for ref in sorted(refs,key=lambda x:(0 if x.startswith('U') else 1 if x.startswith('C') else 2,x)):
            f=fps[ref];before=(*xy(f.GetPosition()),f.GetOrientationDegrees());best=None;trials=0
            radius=1.0 if ref.startswith('U') else 2.0;offsets=[0,-.5,.5,-1,1]+([] if radius==1 else [-1.5,1.5,-2,2])
            for a in [0,90,180,270]:
                for dx in offsets:
                    for dy in offsets:
                        x,y=homes[ref][0]+dx,homes[ref][1]+dy;f.SetPosition(pt(x,y));f.SetOrientationDegrees(a);trials+=1
                        if not legal(ref):continue
                        cand=(score(ref),x,y,a)
                        if best is None or cand<best:best=cand
            if best is None:f.SetPosition(pt(*before[:2]));f.SetOrientationDegrees(before[2]);history.append(dict(ref=ref,iteration=iteration,trials=trials,status='NO_LEGAL_LOCAL_CANDIDATE',before=before));continue
            _,x,y,a=best;f.SetPosition(pt(x,y));f.SetOrientationDegrees(a);history.append(dict(ref=ref,iteration=iteration,trials=trials,before=before,after=[x,y,a],score=best[0]))
    _,_,_,r=paths(kind);(r/'orientation_trials.json').write_text(json.dumps(history,indent=2)+'\n')

def area(b,name,layer,rect,tracks=True,vias=True,fills=False):
    z=k.ZONE(b);z.SetIsRuleArea(True);z.SetLayer(layer);z.SetZoneName(name);z.SetDoNotAllowTracks(tracks);z.SetDoNotAllowVias(vias);z.SetDoNotAllowZoneFills(fills);z.SetDoNotAllowPads(False);z.SetDoNotAllowFootprints(False)
    x1,y1,x2,y2=rect;poly=z.Outline();poly.NewOutline()
    for x,y in [(x1,y1),(x2,y1),(x2,y2),(x1,y2)]:poly.Append(mm(x),mm(y))
    b.Add(z)

def add_keepouts(kind,b):
    from layout_P2 import add_keepouts as mounts
    mounts(b,kind)
    # The silicon body is a track keepout on its own assembly side, preserving
    # ground fill below logic ICs. Local outward pin escapes remain possible.
    for f in b.GetFootprints():
        ref=f.GetReference()
        if not ref.startswith('U') or ref=='U100' or kind=='imu':continue
        pads=list(f.Pads());xs=[xy(p.GetPosition())[0] for p in pads];ys=[xy(p.GetPosition())[1] for p in pads]
        x,y=xy(f.GetPosition());a=f.GetOrientationDegrees()%180
        if len(pads) in [6,8]:
            dx,dy=(.55,.9) if len(pads)==8 and 'DCU' in str(f.GetFPID()) else (.45,1.15) if len(pads)==6 else (1.35,1.55)
            if abs(a-90)<1:dx,dy=dy,dx
            area(b,'OUTWARD_'+ref,B if f.IsFlipped() else F,[x-dx,y-dy,x+dx,y+dy])

def update_records(kind,b,data):
    name,d,pcb,r=paths(kind);fps={f.GetReference():f for f in b.GetFootprints()}
    for c in data['components']:
        if c['ref'] not in fps:continue
        f=fps[c['ref']];c.update(placed_at=[*xy(f.GetPosition()),f.GetOrientationDegrees()],side='B' if f.IsFlipped() else 'F')
    (d/'connectivity.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    info=[]
    for ref,f in fps.items():
        info.append(dict(ref=ref,value=f.GetValue(),position=[*xy(f.GetPosition()),f.GetOrientationDegrees()],side='B' if f.IsFlipped() else 'F',bbox=bounds(f),pins={p.GetNumber():dict(xy=xy(p.GetPosition()),net=str(p.GetNetname())) for p in f.Pads()}))
    (r/'placement.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n')

def fill(kind):
    name,d,pcb,r=paths(kind);b=k.LoadBoard(str(pcb));w,h=json.loads((d/'connectivity.json').read_text())['size']
    for z in list(b.Zones()):
        if not z.GetIsRuleArea():b.Delete(z)
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.GetAttribute()==k.PAD_ATTRIB_PTH:
                p.SetThermalSpokeAngleDegrees(45);p.SetThermalGap(mm(.254));p.SetLocalThermalSpokeWidthOverride(mm(.3))
    for layer in [F,B]:
        z=k.ZONE(b);z.SetLayer(layer);z.SetNet(b.GetNetsByName()['/GND']);z.SetZoneName('P3R1_GND_'+b.GetLayerName(layer));z.SetLocalClearance(mm(.5));z.SetMinThickness(mm(.15));z.SetPadConnection(k.ZONE_CONNECTION_THT_THERMAL);z.SetThermalReliefGap(mm(.254));z.SetThermalReliefSpokeWidth(mm(.3));z.SetIslandRemovalMode(k.ISLAND_REMOVAL_MODE_ALWAYS)
        poly=z.Outline();poly.NewOutline()
        for x,y in [(0,0),(w,0),(w,h),(0,h)]:poly.Append(mm(x),mm(y))
        b.Add(z)
    k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(pcb),b)

def export_dsn(kind):
    name,d,pcb,r=paths(kind);b=k.LoadBoard(str(pcb))
    # Router-only keepout for signals; manual local supply/ground bridges are preserved.
    if kind=='motion':
        for z in b.Zones():
            if z.GetIsRuleArea() and z.GetZoneName().startswith('OUTWARD_U'):z.SetDoNotAllowTracks(True)
    assert k.ExportSpecctraDSN(b,str(d/(name+'.dsn')))
    p=d/(name+'.dsn');p.write_text(p.read_text().replace('(clearance 50 (type smd_smd))','(clearance 200 (type smd_smd))'))

def import_ses(kind):
    name,d,pcb,r=paths(kind);b=k.LoadBoard(str(pcb));assert k.ImportSpecctraSES(b,str(d/(name+'.ses')));k.SaveBoard(str(pcb),b)

if __name__=='__main__':
    kind,action=sys.argv[1:3]
    {'build':build,'fill':fill,'dsn':export_dsn,'import':import_ses}[action](kind)

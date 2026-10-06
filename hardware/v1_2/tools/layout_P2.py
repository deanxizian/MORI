#!/usr/bin/env python3
"""P2 layout branch. Never edits P1, a schematic circuit, or a mechanical source.

Run with KiCad Python. prepare -> route (Java) -> import -> finish -> validate.
The electrical prototype is inherited; this script does not release fabrication.
"""
from pathlib import Path
import json, shutil, sys, math, hashlib, re
import pcbnew as k

R = Path(__file__).resolve().parents[1]
mm = k.FromMM
pt = lambda x,y: k.VECTOR2I(mm(x),mm(y))
KINDS = ['motion','imu','power']

def paths(kind):
    name = 'MORI_'+kind+'_P2'
    d = R/'kicad'/name
    return name,d,d/(name+'.kicad_pcb')

def configure(kind, b, d, name):
    p = json.loads((d/(name+'.kicad_pro')).read_text())
    power = kind == 'power'
    clearance = .20
    via = (1.0,.45) if power else (.8,.3)
    classes = [('Default',.2,clearance,*via),('LogicPower',.2,clearance,*via),
               ('Ground',.2,clearance,*via)]
    if power:
        classes += [('Battery',2.0,.2,1.0,.45),('Wheel',1.5,.2,1.0,.45),('Head',1.0,.2,1.0,.45),('Kelvin',.381,.2,1.0,.45)]
    assigns = {'/GND':'Ground','/+3V3':'LogicPower','/+5V_MOTION':'LogicPower','/CAM_3V3':'LogicPower'}
    if power:
        for n in ['BAT_IN','BAT_REV','BAT_MON']: assigns['/'+n]='Battery'
        for n in ['W9_IN','W_PRE','W_VM','W_DUMP_D']: assigns['/'+n]='Wheel'
        for n in ['H6_IN','H_PRE','H_VM','H_DUMP_D']: assigns['/'+n]='Head'
    if power:
        assigns['/KELVIN_P']='Kelvin';assigns['/KELVIN_N']='Kelvin'
    ns=b.GetDesignSettings().m_NetSettings
    ns.ClearNetclassPatternAssignments()
    values=[]; live={}
    for cname,width,cl,vd,dr in classes:
        c=k.NETCLASS(cname);c.SetClearance(mm(cl));c.SetTrackWidth(mm(width));c.SetViaDiameter(mm(vd));c.SetViaDrill(mm(dr))
        ns.SetDefaultNetclass(c) if cname=='Default' else ns.SetNetclass(cname,c)
        live[cname]=c
        values.append(dict(name=cname,clearance=cl,track_width=width,via_diameter=vd,via_drill=dr))
    pats=[]
    for n,net in b.GetNetsByName().items():
        n=str(n)
        cname=assigns.get(n,'Default');net.SetNetClass(live[cname])
        if cname!='Default':
            ns.SetNetclassPatternAssignment(n,cname);pats.append(dict(netclass=cname,pattern=n))
    ns.RecomputeEffectiveNetclasses()
    p['net_settings']['classes']=values;p['net_settings']['netclass_patterns']=pats
    rules=p['board']['design_settings']['rules']
    rules.update(min_clearance=0.0,min_track_width=.2,min_via_diameter=.75 if kind=='motion' else .8,min_via_annular_width=.25,
        min_through_hole_diameter=.25 if kind=='motion' else .3,min_hole_clearance=.3,min_hole_to_hole=.15,
        min_copper_edge_clearance=.5,min_silk_clearance=.01,min_text_height=.8,min_text_thickness=.10)
    p['board']['design_settings']['track_widths']=[.2,.25,.4,.6,1.0,1.5,2.,3.]
    p['board']['design_settings']['via_dimensions']=[dict(diameter=via[0],drill=via[1]),dict(diameter=1.0,drill=.45)]
    assert not p['board']['design_settings'].get('drc_exclusions',[])
    (d/(name+'.kicad_pro')).write_text(json.dumps(p,indent=2)+'\n')
    ds=b.GetDesignSettings();ds.m_CopperEdgeClearance=mm(.5)
    ds.m_SolderMaskExpansion=mm(.05);ds.m_SolderMaskMinWidth=mm(.07500112);ds.m_SolderPasteMargin=mm(.05);ds.m_SolderPasteMarginRatio=0.0
    ds.m_TentViasFront=False
    from rules_P2 import write_rules
    write_rules(kind,d,name,{str(x) for x in b.GetNetsByName().keys()})

def bbox(fp, extra=.2):
    bb=fp.GetBoundingBox(False,False)
    return [k.ToMM(bb.GetX())-extra,k.ToMM(bb.GetY())-extra,k.ToMM(bb.GetRight())+extra,k.ToMM(bb.GetBottom())+extra]
def overlap(a,b):return not(a[2]<b[0] or a[0]>b[2] or a[3]<b[1] or a[1]>b[3])

def place(kind,b,data):
    fps={f.GetReference():f for f in b.GetFootprints()};w,h=data['size']
    # Connector and mounting interfaces stay at P1 coordinates except the two
    # wheel outputs: placing them beside the wheel conditioner shortens its bus.
    targets={}; fixed=set(fps)
    if kind=='motion':
        targets={'U1':(29,10,0),'U2':(22,23,0),'U3':(16,12,0),'U4':(38,13,0),'U5':(16,22,0),'U6':(9,23,0),
          'R1':(32,10,90),'R2':(25,23,90),'R3':(18,8,0),'R4':(20,10,0),'R5':(13,19,0),
          'R6':(43,25,0),'R7':(16,26,0),'R8':(58,25,0),'R9':(42,13,90),
          'R10':(25,27,0),'R11':(28,27,0),'R12':(22,27,0),'R13':(49,20,0),
          'R14':(12,27,0),'R15':(15,27,0),'R16':(18,27,0),'R17':(35,24,0),'R18':(38,24,0),'R19':(19,20,0),
          'C1':(30,7,0),'C2':(23,20,0),'C3':(17,9,0),'C4':(39,10,0),'C5':(17,19,0),'C6':(9,20,0),
          'C7':(41,11,0),'C8':(52,4,0),'C9':(12,24,90),'C10':(15,24,90),'C11':(18,24,90),'C12':(13,23,90),
          'D1':(28,20,0),'D2':(28,24,0),'D3':(31,24,0)}
    elif kind=='imu':
        targets={'C1':(12.8,8.8,90),'C2':(12.8,11.7,90),'C3':(9,11.8,0),'R1':(6.2,8.5,90),'R2':(7,12.8,0)}
    else:
        # All values are design coordinates, not measured product envelopes.
        for ref,x,y in [('J3',40,7),('J7',48,21),('J8',62,21)]:
            fps[ref].SetPosition(pt(x,y))
        targets={'J10':(35,22,90),'J13':(58,27,0),'Q1':(15,12,180),'R2':(24,12,0),'U1':(24,17,0),'R3':(20,16,270),'R4':(28,16,270),'C1':(26,19,0),
          'R1':(16,17,0),'D1':(19,12,90),'C2':(31.5,12,90),
          'D10':(45,12,0),'Q10':(39,17,270),'Q11':(38,23,0),'R10':(34,15,90),'R11':(35,22,0),
          'C10':(52,12,0),
          'D30':(24,33,90),'Q30':(18,29,180),'Q31':(19,23,0),'R30':(22,27,90),'R31':(22,23,0),
          'C30':(8,26,90),
          'U20':(68,14,0),'U21':(61,13,0),'Q20':(75,12,0),
          'U40':(68,32,0),'U41':(61,32,0),'Q40':(75,32,0),
          'R50':(30,25,90),'R51':(30,29,90),'R52':(33,25,90),'R53':(33,29,90),
          'R54':(55,24,90)}
        # Repack all B-side passives around their functional targets, avoiding
        # through holes and reserving space around high-current packages.
        for ref,f in fps.items():
            if ref.startswith(('R','C','D','U','Q')) and ref not in targets:
                targets[ref]=(k.ToMM(f.GetPosition().x),k.ToMM(f.GetPosition().y),f.GetOrientationDegrees())
    fixed-=set(targets)
    occupied=[]
    def occupy(ref,f,box=None):
        side='B' if f.IsFlipped() else 'F'
        if ref.startswith('H'):
            occupied.append((bbox(f,.7),'both'));return
        occupied.append((box or bbox(f,.2),side))
        # A connector housing or radial capacitor is only above its assembly
        # side. On the reverse, reserve the real through pads and lead trim.
        for pad in f.Pads():
            if pad.GetAttribute() in [k.PAD_ATTRIB_PTH,k.PAD_ATTRIB_NPTH]:
                bb=pad.GetBoundingBox();occupied.append(([k.ToMM(bb.GetX())-.45,k.ToMM(bb.GetY())-.45,k.ToMM(bb.GetRight())+.45,k.ToMM(bb.GetBottom())+.45],'B' if side=='F' else 'F'))
    for ref in fixed:
        f=fps[ref];through=any(p.GetAttribute() in [k.PAD_ATTRIB_PTH,k.PAD_ATTRIB_NPTH] for p in f.Pads())
        if ref=='U100':
            occupied.append((bbox(f),'F'))
            for p in f.Pads():
                x,y=k.ToMM(p.GetPosition().x),k.ToMM(p.GetPosition().y)
                occupied.append(([x-1.15,y-1.15,x+1.15,y+1.15],'B'))
        else: occupy(ref,f)
    # Packages before their local passives; bulk capacitors before small parts.
    order=sorted(targets,key=lambda ref:(-1 if ref.startswith('J') else 0 if ref in ['C10','C30'] and kind=='power' else 1 if ref.startswith(('Q','U','D')) or ref=='R2' and kind=='power' else 2))
    if kind=='power':
        first=['J10','J13','C10','C30','Q1','R2','U1','R3','R4','C1']
        order=first+[r for r in order if r not in first]
    if kind=='imu':order=['R1','C1','C2','C3','R2']
    for ref in order:
        f=fps[ref];side='B' if f.IsFlipped() else 'F';tx,ty,angle=targets[ref]
        through=any(p.GetAttribute()==k.PAD_ATTRIB_PTH for p in f.Pads());candidates=[]
        for rot in [angle,angle+90]:
            f.SetOrientationDegrees(rot);f.SetPosition(pt(0,0));bb=bbox(f,.05 if kind=='imu' else .25)
            for iy in range(3,int(h*2)-2):
                for ix in range(3,int(w*2)-2):
                    x,y=ix/2,iy/2;ab=[bb[0]+x,bb[1]+y,bb[2]+x,bb[3]+y]
                    if ab[0]<.6 or ab[1]<.6 or ab[2]>w-.6 or ab[3]>h-.6:continue
                    if any(overlap(ab,ob) for ob,os in occupied if os in [side,'both']):continue
                    if through:
                        # Through pads must also clear components on the back.
                        blocked=False
                        for pad in f.Pads():
                            if pad.GetAttribute()!=k.PAD_ATTRIB_PTH:continue
                            pb=pad.GetBoundingBox();pbox=[k.ToMM(pb.GetX())+x-.45,k.ToMM(pb.GetY())+y-.45,k.ToMM(pb.GetRight())+x+.45,k.ToMM(pb.GetBottom())+y+.45]
                            if any(overlap(pbox,ob) for ob,os in occupied if os in ['F' if side=='B' else 'B','both']):blocked=True;break
                        if blocked:continue
                    candidates.append(((x-tx)**2+(y-ty)**2+(.1 if rot!=angle else 0),rot,x,y,ab))
        if not candidates: raise RuntimeError(('No legal placement',kind,ref))
        _,rot,x,y,ab=min(candidates);f.SetOrientationDegrees(rot);f.SetPosition(pt(x,y));occupy(ref,f,ab)
    # Assembly reference text must follow the new placement, not its P1 position.
    for drawing in list(b.GetDrawings()):
        if isinstance(drawing,k.PCB_TEXT) and drawing.GetText() in fps:
            f=fps[drawing.GetText()];drawing.SetPosition(f.GetPosition())
        elif isinstance(drawing,k.PCB_TEXT) and 'P1' in drawing.GetText():drawing.SetText(drawing.GetText().replace('P1','P2'))
    for c in data['components']:
        if c['ref'] in fps:
            f=fps[c['ref']];c['placed_at']=[k.ToMM(f.GetPosition().x),k.ToMM(f.GetPosition().y),f.GetOrientationDegrees()]
            c['side']='B' if f.IsFlipped() else 'F'
    return data

def add_keepouts(b,kind):
    for f in b.GetFootprints():
        if not f.GetReference().startswith('H'):continue
        x,y=k.ToMM(f.GetPosition().x),k.ToMM(f.GetPosition().y)
        z=k.ZONE(b);z.SetIsRuleArea(True);z.SetZoneName('R03_'+f.GetReference()+'_M2_assumed_r2p2_plus0p5')
        ls=k.LSET();ls.AddLayer(k.F_Cu);ls.AddLayer(k.B_Cu);z.SetLayerSet(ls)
        z.SetDoNotAllowPads(False);z.SetDoNotAllowFootprints(False);z.SetDoNotAllowTracks(True);z.SetDoNotAllowVias(True);z.SetDoNotAllowZoneFills(True)
        poly=z.Outline();poly.NewOutline()
        for i in range(48):
            a=2*math.pi*i/48;poly.Append(mm(x+2.7*math.cos(a)),mm(y+2.7*math.sin(a)))
        b.Add(z)
    if kind=='imu':
        f=next(f for f in b.GetFootprints() if f.GetReference()=='U1')
        x,y=k.ToMM(f.GetPosition().x),k.ToMM(f.GetPosition().y)
        # Top: central die area only; the device's own pads and radial escapes
        # necessarily lie under its perimeter. Bottom: entire package body.
        for layer,dx,dy in [(k.F_Cu,.90,.65),(k.B_Cu,1.5,1.25)]:
            z=k.ZONE(b);z.SetIsRuleArea(True);z.SetLayer(layer);z.SetZoneName('TDK_AN000393_under_IMU_'+b.GetLayerName(layer))
            z.SetDoNotAllowPads(False);z.SetDoNotAllowFootprints(False);z.SetDoNotAllowTracks(True);z.SetDoNotAllowVias(True);z.SetDoNotAllowZoneFills(True)
            poly=z.Outline();poly.NewOutline()
            for px,py in [(x-dx,y-dy),(x+dx,y-dy),(x+dx,y+dy),(x-dx,y+dy)]:poly.Append(mm(px),mm(py))
            b.Add(z)

def prepare(kind):
    name,d,pcb=paths(kind);old=name.replace('_P2','_P1');src=R/'kicad'/old
    d.mkdir(parents=True,exist_ok=True)
    if not (d/'P1_source_hashes.json').exists():
        hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in src.iterdir() if p.is_file() and p.suffix in ['.kicad_sch','.kicad_pcb','.kicad_pro','.json']}
        (d/'P1_source_hashes.json').write_text(json.dumps(hashes,indent=2)+'\n')
    for fn in ['MORI.kicad_sym','sym-lib-table','fp-lib-table','assembly_bom.csv']:
        shutil.copy2(src/fn,d/fn)
    shutil.copytree(src/'footprints',d/'footprints',dirs_exist_ok=True)
    for ext in ['.kicad_sch','.kicad_pro']:
        (d/(name+ext)).write_text((src/(old+ext)).read_text().replace(old,name))
    data=json.loads((src/'connectivity.json').read_text());data['layout_revision']='P2'
    shutil.copy2(src/(old+'.kicad_pcb'),pcb)
    b=k.LoadBoard(str(pcb))
    for item in list(b.GetTracks())+list(b.Zones()):b.Delete(item)
    for group in list(b.Groups()):b.Delete(group)
    from footprints_P2 import apply
    apply(kind,b,d,data)
    data=place(kind,b,data)
    configure(kind,b,d,name)
    (d/'connectivity.json').write_text(json.dumps(data,indent=2)+'\n')
    add_keepouts(b,kind)
    from detail_P2 import seed
    seed(kind,b)
    k.SaveBoard(str(pcb),b)
    assert k.ExportSpecctraDSN(b,str(d/(name+'.dsn')))
    print(name,'prepared: new placement,',len(b.GetFootprints()),'footprints')

def import_route(kind):
    name,d,pcb=paths(kind);b=k.LoadBoard(str(pcb));configure(kind,b,d,name)
    assert k.ImportSpecctraSES(b,str(d/(name+'.ses')))
    k.SaveBoard(str(pcb),b);print(name,len(b.GetTracks()),'tracks/vias imported')

def finish(kind):
    name,d,pcb=paths(kind);b=k.LoadBoard(str(pcb));data=json.loads((d/'connectivity.json').read_text());w,h=data['size']
    for z in list(b.Zones()):
        if not z.GetIsRuleArea():b.Delete(z)
    layers=[k.F_Cu,k.B_Cu]
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.GetAttribute()==k.PAD_ATTRIB_PTH:
                p.SetThermalSpokeAngleDegrees(45);p.SetThermalGap(mm(.254));p.SetLocalThermalSpokeWidthOverride(mm(.3))
            if p.GetNetname()=='/GND':p.SetLocalZoneConnection(k.ZONE_CONNECTION_THERMAL if p.GetAttribute()==k.PAD_ATTRIB_PTH else k.ZONE_CONNECTION_FULL)
    for layer in layers:
        z=k.ZONE(b);z.SetLayer(layer);z.SetNet(b.GetNetsByName()['/GND']);z.SetZoneName('P2_GND_'+b.GetLayerName(layer))
        z.SetLocalClearance(mm(.5));z.SetMinThickness(mm(.2 if kind=='power' else .15))
        z.SetPadConnection(k.ZONE_CONNECTION_THT_THERMAL);z.SetThermalReliefGap(mm(.254));z.SetThermalReliefSpokeWidth(mm(.3));z.SetIslandRemovalMode(k.ISLAND_REMOVAL_MODE_ALWAYS)
        poly=z.Outline();poly.NewOutline()
        for x,y in [(0,0),(w,0),(w,h),(0,h)]:poly.Append(mm(x),mm(y))
        b.Add(z)
    k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(pcb),b)
    print(name,'ground planes filled; native validation required')

if __name__=='__main__':
    kind,action=sys.argv[1:3]
    assert kind in KINDS
    {'prepare':prepare,'import':import_route,'finish':finish}[action](kind)

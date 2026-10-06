#!/usr/bin/env python3
"""Native KiCad generator for explicitly unvalidated V1.2 prototypes.
Run only with KiCad's bundled Python (pcbnew). Sources are design_P1.py.
Each generated project has real symbols, pins, wires, footprints and netlist parity.
"""
from pathlib import Path
import json,uuid,subprocess,shutil,csv,xml.etree.ElementTree as ET,sys,math
import pcbnew as k
from design_P1 import designs
ROOT=Path(__file__).resolve().parents[1]
CLI='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
FP=Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints')
q=lambda s:json.dumps(str(s),ensure_ascii=False)
mm=k.FromMM
pt=lambda x,y:k.VECTOR2I(mm(x),mm(y))

def build(name,d):
    dest=ROOT/'kicad'/name;dest.mkdir(parents=True,exist_ok=True)
    rep=ROOT/'reports'/'cad'/name;rep.mkdir(parents=True,exist_ok=True)
    uid=lambda s:str(uuid.uuid5(uuid.NAMESPACE_URL,'mori-v12-P1/'+name+'/'+s))
    root=uid('root');cs=d['components']
    def prop(n,v,x,y,hide=False):return f'(property {q(n)} {q(v)} (at {x} {y} 0) (effects (font (size 1 1))'+(' (hide yes)' if hide else '')+'))'
    def libsym(c,full):
        h=max(5.08,len(c['pins'])*2.54);n=c['ref'].replace('#','');ref=c['ref']
        s=f'(symbol {q(full)} (pin_names (offset 0.762)) (exclude_from_sim no) (in_bom yes) (on_board yes)'
        s+=prop('Reference',ref,0,5.08)+prop('Value',c['value'],0,2.54)+prop('Footprint',c['footprint'],0,0,True)
        s+=f'(symbol {q(n+"_0_1")} (rectangle (start 0 1.27) (end 35.56 {-h}) (stroke (width 0.254) (type default)) (fill (type background))))'
        s+=f'(symbol {q(n+"_1_1")}'
        for i,(pn,p) in enumerate(c['pins'].items()):
            s+=f'(pin {p["type"]} line (at -5.08 {-2.54*i} 0) (length 5.08) (name {q(p["name"])} (effects (font (size 0.95 0.95)))) (number {q(pn)} (effects (font (size 0.95 0.95)))))'
        return s+'))'
    libs=[]; inst=[]; col=0;sy=40.64; rowheight=0
    for c in cs:
        ref=c['ref'];n=ref.replace('#','');sid=uid(ref);c['uuid']=sid
        sx=50.8+col*96.52; h=max(5.08,2.54*len(c['pins']))+15.24
        libs.append(libsym(c,'MORI:'+n));on='yes' if c['footprint'] else 'no'
        sym=f'(symbol (lib_id {q("MORI:"+n)}) (at {sx} {sy} 0) (unit 1) (exclude_from_sim no) (in_bom {on}) (on_board {on}) (dnp no) (uuid {sid})'
        sym+=prop('Reference',ref,sx+17.78,sy-5.08)+prop('Value',c['value'],sx+17.78,sy-2.54)+prop('Footprint',c['footprint'],sx,sy,True)
        if c.get('source'):sym+=prop('Datasheet',c['source'],sx,sy,True)
        for pn in c['pins']:sym+=f'(pin {q(pn)} (uuid {uid(ref+"p"+pn)}))'
        sym+=f'(instances (project {q(name)} (path {q("/"+root)} (reference {q(ref)}) (unit 1)))))';inst.append(sym)
        for i,(pn,p) in enumerate(c['pins'].items()):
            x=sx-5.08;y=round(sy+i*2.54,4);net=p['net']
            if net is None:inst.append(f'(no_connect (at {x} {y}) (uuid {uid(ref+pn+"nc")}))');continue
            x2=sx-33.02
            inst.append(f'(wire (pts (xy {x} {y}) (xy {x2} {y})) (stroke (width 0) (type default)) (uuid {uid(ref+pn+"w")}))')
            inst.append(f'(label {q(net)} (at {x2} {y} 0) (effects (font (size 0.95 0.95)) (justify left bottom)) (uuid {uid(ref+pn+"l")}))')
        col+=1;rowheight=max(rowheight,h)
        if col==8:col=0;sy=round(sy+rowheight,4);rowheight=0
    sch=f'(kicad_sch (version 20250114) (generator "mori_v12") (uuid {root}) (paper "A1") (title_block (title {q(name+" - PROTOTYPE / NOT FOR FABRICATION")}) (date "2026-09-22") (rev "V1.2-P1")) (lib_symbols '+''.join(libs)+')'
    for i,t in enumerate([d['description'],'Native netlist/PCB; NOT_TESTED on bench. See engineering_review.md and pinmap.']):
        sch+=f'(text {q(t)} (at 17.78 {15.24+i*5.08} 0) (effects (font (size 1.5 1.5)) (justify left)) (uuid {uid("title"+str(i))}))'
    sch+=''.join(inst)+f'(sheet_instances (path "/" (page "1"))))';(dest/(name+'.kicad_sch')).write_text(sch)
    (dest/'MORI.kicad_sym').write_text('(kicad_symbol_lib (version 20231120) (generator "mori_v12")'+''.join(libsym(c,c['ref'].replace('#','')) for c in cs)+')')
    (dest/'sym-lib-table').write_text('(sym_lib_table (lib (name "MORI") (type "KiCad") (uri "${KIPRJMOD}/MORI.kicad_sym") (options "") (descr "V1.2-P1 documented pin mappings")))')
    used=set()
    for c in cs:
        if not c['footprint']:continue
        lib,fn=c['footprint'].split(':');used.add(lib);dd=dest/'footprints'/(lib+'.pretty');dd.mkdir(parents=True,exist_ok=True)
        source=ROOT/'kicad'/'custom.pretty'/(fn+'.kicad_mod') if lib=='MORI_Custom' else FP/(lib+'.pretty')/(fn+'.kicad_mod')
        shutil.copy2(source,dd/(fn+'.kicad_mod'))
    (dest/'fp-lib-table').write_text('(fp_lib_table '+''.join(f'(lib (name {q(l)}) (type "KiCad") (uri "${{KIPRJMOD}}/footprints/{l}.pretty") (options "") (descr "Localized footprint"))' for l in sorted(used))+')')
    subprocess.run([CLI,'sch','export','netlist',str(dest/(name+'.kicad_sch')),'--format','kicadxml','-o',str(rep/'netlist.xml')],check=True,stdout=subprocess.DEVNULL)
    actual={}
    for net in ET.parse(rep/'netlist.xml').findall('.//nets/net'):
        for node in net.findall('node'):actual[(node.get('ref'),node.get('pin'))]=net.get('name')
    for c in cs:
        for pn,p in c['pins'].items():
            if p['net'] and c['footprint']:assert actual[c['ref'],pn].lstrip('/')==p['net'],(c['ref'],pn)
    board=k.BOARD();board.SetCopperLayerCount(d.get('layers',2));nets={}
    for n in sorted(set(actual.values())):a=k.NETINFO_ITEM(board,n);board.Add(a);nets[n]=a
    w,h=d['size']
    for a,b in zip([(0,0),(w,0),(w,h),(0,h)],[(w,0),(w,h),(0,h),(0,0)]):
        sh=k.PCB_SHAPE();sh.SetShape(k.SHAPE_T_SEGMENT);sh.SetStart(pt(*a));sh.SetEnd(pt(*b));sh.SetLayer(k.Edge_Cuts);sh.SetWidth(mm(.05));board.Add(sh)
    fps={}
    for c in cs:
        if not c['footprint']:continue
        lib,fn=c['footprint'].split(':');fp=k.FootprintLoad(str(dest/'footprints'/(lib+'.pretty')),fn);assert fp,c['ref']
        fp.SetReference(c['ref']);fp.SetValue(c['value']);fp.SetExcludedFromBOM(False);fp.SetField('Datasheet',c.get('source',''));fp.SetFPID(k.LIB_ID(lib,fn));fp.SetPath(k.KIID_PATH('/'+root+'/'+c['uuid']))
        for p in fp.Pads():
            pn=p.GetNumber()
            if (c['ref'],pn) in actual:p.SetNet(nets[actual[c['ref'],pn]])
            elif pn and pn not in ['MP'] and pn not in c['pins']:raise ValueError((c['ref'],'unmapped footprint pad',pn))
        board.Add(fp);x,y,rot=c['at'];fp.SetOrientationDegrees(rot);fp.SetPosition(pt(x,y))
        if c.get('side')=='B':fp.Flip(pt(x,y),False)
        fp.Reference().SetTextSize(pt(.65,.65));fp.Reference().SetTextThickness(mm(.1));fp.Reference().SetVisible(False);fp.Value().SetVisible(False)
        fps[c['ref']]=fp
    def box(fp):
        b=fp.GetBoundingBox(False,False)
        return (k.ToMM(b.GetX())-.2,k.ToMM(b.GetY())-.2,k.ToMM(b.GetRight())+.2,k.ToMM(b.GetBottom())+.2)
    def collide(a,b):return not(a[2]<b[0] or a[0]>b[2] or a[3]<b[1] or a[1]>b[3])
    occupied=[]
    for c in cs:
        if not c['footprint'] or c.get('auto'):continue
        fp=fps[c['ref']];through=any(p.GetAttribute()==k.PAD_ATTRIB_PTH for p in fp.Pads())
        if c['ref']=='U100':
            occupied.append((box(fp),'F'))
            for pad in fp.Pads():
                x,y=k.ToMM(pad.GetPosition().x),k.ToMM(pad.GetPosition().y)
                occupied.append(((x-1.1,y-1.1,x+1.1,y+1.1),'B'))
        else:occupied.append((box(fp),'both' if through else c.get('side','F')))
    for c in sorted(cs,key=lambda c:(0 if c['ref'].startswith('J') else (1 if c['ref'].startswith('C') else 2),-len(c['pins']))):
        if not c['footprint'] or not c.get('auto'):continue
        fp=fps[c['ref']];side=c.get('side','F');target=c['at'];candidates=[]
        for rot in [0,90]:
            fp.SetOrientationDegrees(rot);fp.SetPosition(pt(0,0));b=box(fp)
            for iy in range(2,int(h*2)-2):
                for ix in range(2,int(w*2)-2):
                    x,y=ix/2,iy/2;bb=(x+b[0],y+b[1],x+b[2],y+b[3])
                    if bb[0]<.4 or bb[1]<.4 or bb[2]>w-.4 or bb[3]>h-.4:continue
                    if any(collide(bb,ob) for ob,os in occupied if os in ['both',side]):continue
                    if side=='F' and any(collide(bb,ob) for ob in d.get('module_outlines',[])):continue
                    candidates.append(((x-target[0])**2+(y-target[1])**2,rot,x,y,bb))
        if not candidates:raise ValueError(('No placement space',name,c['ref']))
        _,rot,x,y,bb=min(candidates);fp.SetOrientationDegrees(rot);fp.SetPosition(pt(x,y));occupied.append((bb,'both' if any(p.GetAttribute()==k.PAD_ATTRIB_PTH for p in fp.Pads()) else side))
        c['placed_at']=[x,y,rot]
    # Fabrication drawing retains reference labels; assembly map is exported separately.
    for c in cs:
        if not c['footprint']:continue
        t=k.PCB_TEXT(board);t.SetText(c['ref']);t.SetTextSize(pt(.7,.7));t.SetTextThickness(mm(.1));t.SetPosition(fps[c['ref']].GetPosition());t.SetLayer(k.F_Fab if c.get('side')!='B' else k.B_Fab);t.SetMirrored(c.get('side')=='B');board.Add(t)
    for rect in d.get('module_outlines',[]):
        x1,y1,x2,y2=rect
        for a,b in zip([(x1,y1),(x2,y1),(x2,y2),(x1,y2)],[(x2,y1),(x2,y2),(x1,y2),(x1,y1)]):
            s=k.PCB_SHAPE();s.SetShape(k.SHAPE_T_SEGMENT);s.SetStart(pt(*a));s.SetEnd(pt(*b));s.SetLayer(k.Dwgs_User);s.SetWidth(mm(.15));board.Add(s)
    t=k.PCB_TEXT(board);t.SetText(name+' P1 / UNVALIDATED');t.SetTextSize(pt(.7,.7));t.SetPosition(pt(w/2,h/2));t.SetLayer(k.Dwgs_User);board.Add(t)
    pro={'meta':{'filename':name+'.kicad_pro','version':1},'board':{'design_settings':{'rules':{'min_clearance':d.get('clearance',.2),'min_track_width':.2,'min_via_diameter':.6,'min_through_hole_diameter':.3,'min_copper_edge_clearance':.5}}},
         'net_settings':{'classes':[{'name':'Default','clearance':d.get('clearance',.2),'track_width':.2,'via_diameter':.6,'via_drill':.3}], 'meta':{'version':3}},'schematic':{'meta':{'version':1}}}
    pro['board']['design_settings']['rule_severities'] = {key: 'warning' for key in [
        'missing_courtyard', 'track_not_centered_on_via', 'footprint_filters_mismatch',
        'footprint_type_mismatch', 'tuning_profile_track_geometries']}
    (dest/(name+'.kicad_pro')).write_text(json.dumps(pro,indent=2)+'\n')
    # Set live netclasses too: writing the .pro alone does not update the fresh
    # in-memory board's default 0.2-mm net class during save/export.
    ns=board.GetDesignSettings().m_NetSettings
    nc=k.NETCLASS('Default');nc.SetClearance(mm(d.get('clearance',.15)));nc.SetTrackWidth(mm(.2));nc.SetViaDiameter(mm(.6));nc.SetViaDrill(mm(.3))
    ns.SetNetclass('Default',nc)
    for net in nets.values():net.SetNetClass(nc)
    ds=board.GetDesignSettings();ds.m_CopperEdgeClearance=mm(.5)
    k.SaveBoard(str(dest/(name+'.kicad_pcb')),board)
    (dest/'connectivity.json').write_text(json.dumps(d,indent=2)+'\n')
    with (dest/'assembly_bom.csv').open('w',newline='') as f:
        fields=['ref','value','footprint','source','note'];cw=csv.DictWriter(f,fieldnames=fields);cw.writeheader();cw.writerows({x:c.get(x,'') for x in fields} for c in cs if c['footprint'])
    # The label-array drawing above bootstraps the netlist for board creation.
    # The published schematic is always the functional circuit. Reformatting
    # alone uses functional_schematic.py and NEVER regenerates this PCB.
    from functional_schematic import render_project
    render_project(name)
    subprocess.run([CLI,'sch','export','netlist',str(dest/(name+'.kicad_sch')),'--format','kicadxml','-o',str(rep/'netlist.xml')],check=True,stdout=subprocess.DEVNULL)
    print(name,len(fps),'footprints',len(nets),'nets','UNROUTED')

if __name__=='__main__':
    for name,d in designs().items():
        if len(sys.argv)==1 or name in sys.argv[1:]:build(name,d)

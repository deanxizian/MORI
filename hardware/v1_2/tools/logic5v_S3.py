#!/usr/bin/env python3
"""Schematic-only dual 5 V revision. Never writes an existing PCB or mechanics.

The P2 electrical circuit is inherited, then two separately fused buck circuits
are added. Geometry/placement is intentionally UNFROZEN at the user's request.
"""
from pathlib import Path
import csv, json, shutil, uuid, re, subprocess, hashlib
from copy import deepcopy
from functional_schematic import Drawing, q, sexpr, encode
from readable_schematic import power, block
from design_P1 import comp, pin, GH

H=Path(__file__).resolve().parents[1]
NAME='MORI_power_S3'
REV='V1.2-H0.3-S3'
DEST=H/'kicad'/NAME
REPORT=H/'schematic_S3/reports'
FP=Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints')
TI='https://www.ti.com/lit/ds/symlink/tps54302.pdf'
BOURNS='https://www.bourns.com/docs/product-datasheets/srp7050ta.pdf'
FUSE='https://www.littelfuse.com/assetdocs/fuse-451-and-453-datasheet?assetguid=533cd5cc-956c-4243-867f-6ab5a62f6ba1'
SAMSUNG='https://product.samsungsem.com/mlcc/CL32B226KAJNNN.do'

def part(ref,value,fp,nets,mpn,manufacturer,source='',lcsc='',note='',dnp=False):
    c=comp(ref,value,fp,nets,[0,0,0],source=source,note=note)
    c.pop('at');c.pop('auto');c.pop('side')
    c.update(uuid=str(uuid.uuid5(uuid.NAMESPACE_URL,REV+'/'+ref)),mpn=mpn,
             manufacturer=manufacturer,lcsc=lcsc,dnp=dnp,layout_status='NOT_LAID_OUT',
             source_date='2026-09-22',physical_tests='NOT_TESTED')
    return c

def new_parts():
    result=[]
    for n,p,out,j,fusea,flag in [(60,'M5','+5V_MOTION','J17',1,6),(70,'C5','+5V_CAM','J18',2,7)]:
        r=lambda prefix,i=0:prefix+str(n+i)
        add=lambda *a,**kw:result.append(part(*a,**kw))
        add(r('F'),f'{fusea}A / 125V / very fast', 'Fuse:Fuse_Littelfuse-NANO2-451_453',
            {1:'BAT_MON',2:p+'_VIN'},f'045100{fusea}.MRL','Littelfuse',FUSE,
            'C3099' if fusea==1 else 'C99547',
            'Input branch fuse, not a fast electronic current limiter. Coordinate inrush, ambient derating and upstream 6.3A fuse on bench.')
        add(r('U'),'TPS54302DDCR','MORI_Custom:TI_DDC0006A_TPS54302',
            {1:pin('GND','GND','power_in'),2:pin('SW',p+'_SW','power_out'),
             3:pin('VIN',p+'_VIN','power_in'),4:pin('FB',p+'_FB','input'),
             5:pin('EN',p+'_EN','input'),6:pin('BOOT',p+'_BOOT')},
            'TPS54302DDCR','Texas Instruments',TI,'C311983',
            'SLVSDG6C Rev C. 1GND 2SW 3VIN 4FB 5EN 6BOOT. EN internally pulled up; never tie EN to 3S VIN. 3A silicon rating is not the qualified harness/assembly rating.')
        add(r('L'),'10uH / SRP7050TA-100M','MORI_Custom:Bourns_SRP7050TA_CANDIDATE',
            {1:p+'_SW',2:out},'SRP7050TA-100M','Bourns',BOURNS,'C2041441',
            '10uH +/-20%; DCR max69mohm, Irms4A (40C rise), Isat7.5A (20% L fall). Footprint dimension interpretation pending visual confirmation before PCB.')
        for offset,net1,net2 in [(0,p+'_VIN','GND'),(6,p+'_VIN','GND'),(3,out,'GND'),(4,out,'GND')]:
            add(r('C',offset),'22u / 25V / X7R','Capacitor_SMD:C_1210_3225Metric',
                {1:net1,2:net2},'CL32B226KAJNNNE','Samsung Electro-Mechanics',SAMSUNG,'C309062',
                '22uF +/-10%. Effective capacitance at bias and temperature must be qualified; nominal capacitance is not guaranteed in-circuit capacitance.')
        for offset,net1,net2 in [(1,p+'_VIN','GND'),(2,p+'_BOOT',p+'_SW')]:
            add(r('C',offset),'100n / 50V / X7R','Capacitor_SMD:C_0603_1608Metric',
                {1:net1,2:net2},'GRM188R71H104KA93D','Murata',
                'https://www.murata.com/en-us/products/productdetail?partno=GRM188R71H104KA93D','',
                'Exact suffix and domestic small-quantity quotation remain to be checked. Cboot must connect BOOT to SW, not GND.')
        add(r('C',5),'75p / 50V / C0G','Capacitor_SMD:C_0603_1608Metric',
            {1:out,2:p+'_FB'},'GRM1885C1H750JA01D','Murata',
            'https://www.murata.com/en-us/products/productdetail?partno=GRM1885C1H750JA01D','',
            'Feedforward across upper feedback resistor, following TI 5V ceramic-output reference. Re-tune only from stability/step-load evidence.')
        for offset,value,mpn,a,b in [(0,'100k / 0.1%','RT0603BRD07100KL',out,p+'_FB'),(1,'13.3k / 0.1%','RT0603BRD0713K3L',p+'_FB','GND')]:
            add(r('R',offset),value,'Resistor_SMD:R_0603_1608Metric',{1:a,2:b},mpn,'Yageo',
                'https://www.yageogroup.com/component-documentation/download/specsheet/'+mpn,'',
                'Nominal 0.596V reference gives 5.0772V setpoint; full voltage tolerance is calculated, not assumed exactly5.000V.')
        if j=='J17':
            fp=GH(2);mpn='BM02B-GHS-TBT(LF)(SN)';val='MOTION 5V OUT / 1+ 2GND'
            note='To unchanged motion_P2 J1: 1->1,2->2. Target0.5A sustained/0.75A transient; 1A GH contact rating at AWG26, exact crimp/harness qualification required.'
        else:
            fp='Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical';mpn='B2B-XH-A(LF)(SN)';val='CAM 5V OUT / 1+ 2GND'
            note='To qualified CAM USB power pigtail, NOT BAT connector. Target1.5A sustained/2A peak. USB-C source/CC/polarity and cable resistance still require qualification. Disconnect robot5V for host USB.'
        add(j,val,fp,{1:pin('5V_OUT',out),2:pin('GND','GND')},mpn,'JST',
            'https://www.jst-mfg.com/product/pdf/eng/eGH.pdf' if j=='J17' else 'https://www.jst-mfg.com/product/pdf/eng/eXH.pdf','',note)
        add(r('JP'),'SERVICE OFF / OPEN=ON','Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical',
            {1:pin('EN',p+'_EN'),2:pin('GND','GND')},'61300211121','Wurth Elektronik',
            'https://www.we-online.com/components/products/datasheet/61300211121.pdf','',
            'Normally open header. Bridge 1-2 only in maintenance cradle to disable this one rail. Motion supply loss removes ARM and robot balance. No automatic MCU-controlled power cycling.')
        for off,net in [(0,out),(1,'GND')]:
            add(r('TP',off),net,'TestPoint:TestPoint_Pad_D1.5mm',{1:pin(net,net)},'PCB copper test pad','PCB','', '',
                'Electrical test access defined; position and fixture coverage intentionally not frozen.')
        add('#FLG'+str(flag),'FUSED INPUT POWER DECLARATION','',
            {1:pin('Post-fuse source',p+'_VIN','power_out')},'NOT_A_COMPONENT','N/A',TI,'',
            'ERC declaration of power passed through Q1/R2/F60 or F70. No new physical power source and no rule exclusion.')
        result[-1].update(internal_power_declaration=True,flag_caption='Post-fuse power')
    return result

def prepare():
    src=H/'kicad/MORI_power_P2'
    DEST.mkdir(parents=True,exist_ok=True);REPORT.mkdir(parents=True,exist_ok=True)
    for name in ['footprints']:
        shutil.copytree(src/name,DEST/name,dirs_exist_ok=True)
    for name in ['fp-lib-table','sym-lib-table']:
        shutil.copy2(src/name,DEST/name)
    p=json.loads((src/'MORI_power_P2.kicad_pro').read_text())
    p['meta']['filename']=NAME+'.kicad_pro'
    (DEST/(NAME+'.kicad_pro')).write_text(json.dumps(p,indent=2)+'\n')
    # This is deliberately not a PCB copy. S3 has no board/frame/placement file.
    (DEST/(NAME+'.kicad_sch')).write_text((src/'MORI_power_P2.kicad_sch').read_text().replace('MORI_power_P2',NAME))
    d=json.loads((src/'connectivity.json').read_text())
    d.update(size=None,layout_revision=None,schematic_revision=REV,
             pcb_status='NOT_UPDATED_USER_REQUEST',mechanical_outline_status='UNFROZEN',
             description='Two PCB-local5V converters; MCU local3V3 retained. Schematic-only revision, no new PCB.',
             power_nets=d['power_nets']+['M5_VIN','C5_VIN','+5V_MOTION','+5V_CAM'])
    for c in d['components']:
        for field in ['at','placed_at','auto','side']:c.pop(field,None)
        if c['ref']=='J6':c.update(value='RAW BAT SERVICE / DNP',dnp=True,note='Legacy external5V feed no longer used. Not5V. Leave unpopulated in S3.')
        if c['ref'].startswith('H'):c['value']='M2 mounting / POSITION TBD'
    d['components']+=new_parts()
    (DEST/'connectivity.json').write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
    for c in new_parts():
        if not c['footprint'] or c['footprint'].startswith('MORI_Custom:'):continue
        lib,fn=c['footprint'].split(':');dst=DEST/'footprints'/(lib+'.pretty');dst.mkdir(exist_ok=True)
        shutil.copy2(FP/(lib+'.pretty')/(fn+'.kicad_mod'),dst/(fn+'.kicad_mod'))
    # Assign native project-local land patterns, independent of board placement.
    custom=DEST/'footprints/MORI_Custom.pretty';custom.mkdir(exist_ok=True)
    def footprint(name,body,pads,description):
        sx,sy=body
        s=f'(footprint {q(name)} (version 20241229) (generator "mori_S3") (layer "F.Cu") (descr {q(description)}) (attr smd)'
        s+=f'(fp_rect (start {-sx/2} {-sy/2}) (end {sx/2} {sy/2}) (stroke (width 0.1) (type default)) (fill none) (layer "F.Fab"))'
        extx=max(sx/2,max(abs(x)+w/2 for _,x,y,w,h in pads))+.25
        exty=max(sy/2,max(abs(y)+h/2 for _,x,y,w,h in pads))+.25
        s+=f'(fp_rect (start {-extx} {-exty}) (end {extx} {exty}) (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))'
        for pn,x,y,w,h in pads:s+=f'(pad "{pn}" smd roundrect (at {x} {y}) (size {w} {h}) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.08))'
        (custom/(name+'.kicad_mod')).write_text(s+')\n')
    footprint('TI_DDC0006A_TPS54302',(1.6,2.9),[(n,x,y,1.1,.6) for n,x,y in [(1,-1.35,-.95),(2,-1.35,0),(3,-1.35,.95),(4,1.35,.95),(5,1.35,0),(6,1.35,-.95)]],
              'TI SLVSDG6C p30 DDC0006A: pads1.1x0.6; column2.7; pitch0.95. Stencil and full PCB review pending.')
    footprint('Bourns_SRP7050TA_CANDIDATE',(7.6,6.9),[(1,-2.95,0,2.5,3.5),(2,2.95,0,2.5,3.5)],
              'PROTOTYPE CANDIDATE ONLY: vendor text dimensions8.4 overall,2.5x3.5 lands. Visual orientation confirmation required BEFORE layout/fabrication.')
    libs=sorted({c['footprint'].split(':')[0] for c in d['components'] if c['footprint']})
    (DEST/'fp-lib-table').write_text('(fp_lib_table '+''.join(f'(lib (name {q(l)}) (type "KiCad") (uri "${{KIPRJMOD}}/footprints/{l}.pretty") (options "") (descr "S3 local library"))' for l in libs)+')')
    return d

def draw_branch(d,n,p,out,j,flag,x,title):
    r=lambda prefix,i=0:prefix+str(n+i)
    b=block(d,title,x,272,157,116,'Prototype: verify stability, temperature, cable drop and concurrent load. No PCB placement frozen.')
    b.place(r('U'),62,45,kind='ic',pins={'3':(-14,-10,'L'),'5':(-14,9,'L'),'1':(0,15,'B'),'2':(14,0,'R'),'6':(14,-10,'R'),'4':(14,10,'R')},w=24,h=25,caption_at=(62,22))
    b.place(r('F'),17,26,kind='fuse',short='1A input fuse' if n==60 else '2A input fuse')
    b.mark(r('F'),1)
    b.join((r('F'),2),(r('U'),3),via=[(48,26)])
    for off,xp in [(0,24),(6,34),(1,44)]:
        b.place(r('C',off),xp,39,orient='v',short='22u/25V' if off!=1 else '100n')
        b.join((r('F'),2),(r('C',off),1),via=[(xp,26)])
        b.supply(r('C',off),2,up=False)
    b.place(r('C',2),88,35,short='100n BOOT')
    b.join((r('U'),6),(r('C',2),1))
    b.place(r('L'),98,45,kind='l',short='10uH / 4A rms',caption_at=(98,39))
    b.join((r('U'),2),(r('L'),1))
    b.join((r('C',2),2),(r('L'),1),via=[(91,45)])
    b.place(j,148,24,short='MOTION 5V' if n==60 else 'CAM 5V',caption_at=(143,18))
    b.join((r('L'),2),(j,1),via=[(139,45),(139,23)])
    b.mark(j,2)
    for off,xp in [(3,119),(4,132)]:
        b.place(r('C',off),xp,61,orient='v',short='22u/25V')
        b.join((r('L'),2),(r('C',off),1),via=[(xp,45)]);b.supply(r('C',off),2,up=False)
    b.place(r('R'),105,68,orient='v',short='100k 0.1%')
    b.place(r('R',1),105,89,orient='v',short='13.3k 0.1%')
    b.join((r('L'),2),(r('R'),1),via=[(105,45)])
    b.join((r('R'),2),(r('R',1),1))
    b.join((r('U'),4),(r('R'),2),via=[(85,55),(85,79),(105,79)])
    b.supply(r('R',1),2,up=False)
    b.place(r('C',5),93,68,orient='v',short='75p C0G')
    b.join((r('R'),1),(r('C',5),1),via=[(105,52),(93,52)])
    b.join((r('C',5),2),(r('R'),2),via=[(93,79),(105,79)])
    b.place(r('JP'),42,82,orient='r',short='OPEN=ON / SHORT=OFF')
    b.join((r('U'),5),(r('JP'),1),via=[(20,54),(20,81)])
    b.mark(r('JP'),2)
    b.place(r('TP'),149,45,kind='conn',short='5V probe')
    b.join((r('L'),2),(r('TP'),1))
    b.place(r('TP',1),149,76,kind='conn',short='GND probe');b.mark(r('TP',1),1)
    b.place('#FLG'+str(flag),11,94);b.mark('#FLG'+str(flag),1)
    b.d.text('Post-fuse power declaration only',b.x+7,b.y+100,.8)
    b.d.text('EN is internally pulled up; never connect to raw battery.',b.x+7,b.y+107,.85)
    b.d.text('Setpoint 5.077V. MCU 3V3 remains local.',b.x+84,b.y+101,.9)
    return b

def generate():
    data=prepare();d=Drawing(NAME);power(d)
    d.paper=(841,1050)
    # Replace stale historical block captions; inherited circuit topology stays.
    replacements={
        'MORI / POWER CONDITIONER / S2':'MORI / POWER + DUAL 5V / S3 - SCHEMATIC ONLY',
        'J2 -> wheel buck; J4 -> head buck; J6 -> two independent 5 V converters.':'J2 -> external9V; J4 -> external6V. J6 is RAW BAT service, DNP. See blocks11/12 for logic5V.',
        '80 x 45 mm PCB; populated assembly and thermal performance are not qualified.':'Board outline / mounting coordinates UNFROZEN. P2 PCB does not implement blocks11/12.'}
    for a,b in replacements.items():d.objects=[v.replace(a,b) for v in d.objects]
    draw_branch(d,60,'M5','+5V_MOTION','J17',6,5,'11  Motion 5 V / independent fused buck')
    draw_branch(d,70,'C5','+5V_CAM','J18',7,166,'12  Interaction 5 V / independent fused buck')
    layout=d.finish()
    s=DEST/(NAME+'.kicad_sch')
    raw=s.read_text().replace('(rev "S2 drawing layout")',f'(rev "{REV}")').replace('PROTOTYPE / UNVALIDATED - electrical design unchanged','PROTOTYPE / NOT_TESTED - SCHEMATIC ONLY; PCB NOT UPDATED')
    # Larger legends on the two spacious new blocks. Coordinates/connectivity
    # are untouched; the full exported PDF is inspected again after this step.
    refs={c['ref'] for c in new_parts()}
    def larger(node):
        if node and node[0]=='font':
            for f in node:
                if isinstance(f,list) and f[0]=='size':f[1:]=[str(round(float(v)*1.8,5)) for v in f[1:]]
        for child in node:
            if isinstance(child,list):larger(child)
    tree=sexpr(raw)
    for node in tree:
        if not isinstance(node,list):continue
        if node[0]=='lib_symbols':
            for lib in node[1:]:
                if isinstance(lib,list) and json.loads(lib[1]).split(':')[-1] in {r.replace('#','') for r in refs}:larger(lib)
        elif node[0]=='symbol':
            props={json.loads(v[1]):json.loads(v[2]) for v in node if isinstance(v,list) and v[0]=='property'}
            if props.get('Reference') in refs:larger(node)
        elif node[0] in ['text','label']:
            at=next((v for v in node if isinstance(v,list) and v[0]=='at'),None)
            if at and float(at[2])>=272*2.54:larger(node)
    s.write_text(encode(tree)+'\n')
    local=sexpr((DEST/'MORI.kicad_sym').read_text())
    for lib in local:
        if isinstance(lib,list) and lib[0]=='symbol' and json.loads(lib[1]) in {r.replace('#','') for r in refs}:larger(lib)
    (DEST/'MORI.kicad_sym').write_text(encode(local)+'\n')
    layout['schematic_sha256']=hashlib.sha256(s.read_bytes()).hexdigest()
    (REPORT/'layout.json').write_text(json.dumps(layout,indent=2)+'\n')
    fields=['ref','value','mpn','manufacturer','footprint','lcsc','source','source_date','dnp','note']
    with (DEST/'assembly_bom.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:c.get(k,'') for k in fields} for c in data['components'] if c['footprint'])
    (DEST/'README.md').write_text('# MORI 电源原理图 S3\n\n本工程只含原理图。两路板载5V新增电路尚未同步到PCB；没有冻结板框、孔位或放置。P2 PCB 保留在原目录，仅代表旧电路。\n\n完整变更和测试边界见 [S3说明](../../schematic_S3/README.md)。\n')
    print(NAME, len(data['components']),'symbols; schematic only, PCB untouched')

if __name__=='__main__':generate()

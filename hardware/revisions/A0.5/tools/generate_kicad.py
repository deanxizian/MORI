#!/usr/bin/env python3
"""Generate native KiCad sources, localized libraries, and an explicitly UNROUTED PCB."""
from pathlib import Path
import json,uuid,math,shutil,csv
import pcbnew as k
import subprocess,xml.etree.ElementTree as ET
R=Path(__file__).resolve().parents[1];D=R/'kicad';D.mkdir(exist_ok=True)
cs=json.loads((D/'connectivity.json').read_text());mech=json.loads((R/'mechanical_interfaces.json').read_text())
uid=lambda key:str(uuid.uuid5(uuid.NAMESPACE_URL,'mori-reva/'+key))
q=lambda value:json.dumps(str(value),ensure_ascii=False)
root=uid('root');project='MORI_carrier'
eff=lambda size=1.0:f'(effects (font (size {size} {size})))'
def prop(name,value,x,y,hide=False):return f'(property {q(name)} {q(value)} (at {x} {y} 0) (effects (font (size 1 1))'+(' (hide yes)' if hide else '')+'))'
for i,(x,y) in enumerate(mech['parts']['carrier']['mount_holes_local'],1):cs.append(dict(ref=f'H{i}',value='M3_deck_hole_3.4mm',footprint='MORI_Mech:MountingHole_3.4mm_M3',pins={},section='MECHANICAL',kind='hole',note='copied deck XY, standoff Z pending'))
for i,net in enumerate(['DEVKIT_5V','HEAD_5V'],1):cs.append(dict(ref=f'#FLG{i}',value='External_power_path',footprint='',pins={'1':dict(name='pwr',net=net,type='power_out')},section='POWER_FLAG',note='power source through documented diode/NC path',kind='flag'))
def libsymbol(c,fullname):
 pins=c['pins'];h=max(5.08,len(pins)*2.54);name=c['ref'].replace('#','')
 s=f'(symbol {q(fullname)} (pin_names (offset 1.016)) (exclude_from_sim no) (in_bom yes) (on_board yes)'
 s+=prop('Reference',c['ref'],12.7,5.08)+prop('Value',c['value'],12.7,2.54)+prop('Footprint',c['footprint'],0,0,True)
 s+=f'(symbol {q(name+"_0_1")} (rectangle (start 0 1.27) (end 33.02 {-h}) (stroke (width 0.254) (type default)) (fill (type background))))'
 s+=f'(symbol {q(name+"_1_1")}'
 for i,(pn,pin) in enumerate(pins.items()):s+=f'(pin {pin["type"]} line (at -5.08 {-2.54*i} 0) (length 5.08) (name {q(pin["name"])} {eff(.95)}) (number {q(pn)} {eff(.95)}))'
 return s+'))'
lib=[];inst=[];coords={}
for j,c in enumerate(cs):
 ref=c['ref'];name=ref.replace('#','');sx=71.12+(j%9)*127;sy=40.64+(j//9)*88.9
 lib.append(libsymbol(c,'MORI:'+name));sid=uid(ref);c['uuid']=sid
 board='no' if ref.startswith('#') else 'yes'
 sym=f'(symbol (lib_id {q("MORI:"+name)}) (at {sx} {sy} 0) (unit 1) (exclude_from_sim no) (in_bom {board}) (on_board {board}) (dnp no) (uuid {sid})'
 sym+=prop('Reference',ref,sx+16.51,sy-5.08)+prop('Value',c['value'],sx+16.51,sy-2.54)+prop('Footprint',c['footprint'],sx,sy,True)
 for pn in c['pins']:sym+=f'(pin {q(pn)} (uuid {uid(ref+"-pin"+pn)}))'
 sym+=f'(instances (project {q(project)} (path {q("/"+root)} (reference {q(ref)}) (unit 1)))))';inst.append(sym)
 for i,(pn,pin) in enumerate(c['pins'].items()):
  x=sx-5.08;y=round(sy+2.54*i,4);n=pin['net']
  if n is None:inst.append(f'(no_connect (at {x} {y}) (uuid {uid(ref+pn+"nc")}))');continue
  x2=sx-38.1
  inst.append(f'(wire (pts (xy {x} {y}) (xy {x2} {y})) (stroke (width 0) (type default)) (uuid {uid(ref+pn+"w")}))')
  inst.append(f'(label {q(n)} (at {x2} {y} 0) (effects (font (size 1 1)) (justify left bottom)) (uuid {uid(ref+pn+"label")}))')
text='MORI RevA — PROTOTYPE / UNVALIDATED — module harness + safety circuitry; see wiring.csv for offboard paths'
sch=f'(kicad_sch (version 20250114) (generator "mori_generator") (uuid {root}) (paper "A0") (title_block (title "MORI carrier RevA — NOT FOR FABRICATION") (date "2026-09-21") (rev "A0.5")) (lib_symbols '+''.join(lib)+')'
sch+=f'(text {q(text)} (at 30.48 15.24 0) (effects (font (size 2 2)) (justify left)) (uuid {uid("title")}))'+''.join(inst)+f'(sheet_instances (path "/" (page "1"))))'
(D/(project+'.kicad_sch')).write_text(sch)
(D/'MORI.kicad_sym').write_text('(kicad_symbol_lib (version 20231120) (generator "mori_generator")'+''.join(libsymbol(c,c['ref'].replace('#','')) for c in cs)+')')
(D/'sym-lib-table').write_text('(sym_lib_table (lib (name "MORI") (type "KiCad") (uri "${KIPRJMOD}/MORI.kicad_sym") (options "") (descr "MORI interface symbols; pin types model offboard modules")))')
# Localize used footprints for portable project.
fpbase=Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints');libs=set()
for c in cs:
 if not c['footprint']:continue
 lib,name=c['footprint'].split(':');libs.add(lib);dest=D/'footprints'/(lib+'.pretty');dest.mkdir(parents=True,exist_ok=True)
 if lib=='MORI_Mech':
  (dest/(name+'.kicad_mod')).write_text('(footprint "MountingHole_3.4mm_M3" (version 20241229) (generator "mori") (layer "F.Cu") (attr through_hole) (fp_text reference "H" (at 0 -4) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15)))) (fp_text value "M3" (at 0 4) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15)))) (fp_circle (center 0 0) (end 3.5 0) (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd")) (pad "" np_thru_hole circle (at 0 0) (size 3.4 3.4) (drill 3.4) (layers "*.Cu" "*.Mask")))')
 else:shutil.copy2(fpbase/(lib+'.pretty')/(name+'.kicad_mod'),dest)
(D/'fp-lib-table').write_text('(fp_lib_table '+''.join(f'(lib (name {q(v)}) (type "KiCad") (uri "${{KIPRJMOD}}/footprints/{v}.pretty") (options "") (descr "Subset copied from KiCad10 library"))' for v in sorted(libs))+')')
subprocess.run(['/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli','sch','export','netlist',str(D/(project+'.kicad_sch')),'--format','kicadxml','-o',str(R/'reports/netlist.xml')],check=True)
xml=ET.parse(R/'reports/netlist.xml');actualpins={}
for net in xml.findall('.//nets/net'):
 for node in net.findall('node'):actualpins[(node.get('ref'),node.get('pin'))]=net.get('name')
for c in cs:
 for pn,pin in c['pins'].items():
  if pin['net'] and not c['ref'].startswith('#'):assert actualpins[(c['ref'],pn)].lstrip('/')==pin['net'],(c['ref'],pn)
board=k.BOARD();board.SetCopperLayerCount(2);nets={}
for n in sorted(set(actualpins.values())):nn=k.NETINFO_ITEM(board,n);board.Add(nn);nets[n]=nn
mm=lambda x:k.FromMM(x);pt=lambda x,y:k.VECTOR2I(mm(x),mm(y))
# PCB X = Blender X+100, PCB Y = Blender Y+100; note PCB front views differ from world axes.
cut=math.sqrt(61**2-46**2);cuty=math.sqrt(61**2-48**2)
outline=[(-cut,-46),(cut,-46),(48,-cuty),(48,cuty),(cut,46),(-cut,46),(-48,cuty),(-48,-cuty)]
def loop(poly):
 for a,b in zip(poly,poly[1:]+poly[:1]):
  sh=k.PCB_SHAPE();sh.SetShape(k.SHAPE_T_SEGMENT);sh.SetStart(pt(a[0]+100,a[1]+100));sh.SetEnd(pt(b[0]+100,b[1]+100));sh.SetLayer(k.Edge_Cuts);sh.SetWidth(mm(.05));board.Add(sh)
loop(outline);loop([(-38,-12),(-6,-12),(-6,12),(-38,12)])
for y in [-7,7]:sh=k.PCB_SHAPE();sh.SetShape(k.SHAPE_T_CIRCLE);sh.SetCenter(pt(114,100+y));sh.SetEnd(pt(119,100+y));sh.SetLayer(k.Edge_Cuts);sh.SetWidth(mm(.05));board.Add(sh)
footprints=[]
for c in cs:
 if not c['footprint']:continue
 lib,name=c['footprint'].split(':');fp=k.FootprintLoad(str(D/'footprints'/(lib+'.pretty')),name);assert fp,c['ref']
 fp.SetReference(c['ref']);fp.SetValue(c['value']);fp.SetAttributes(fp.GetAttributes() & ~k.FP_EXCLUDE_FROM_BOM);fp.SetFPID(k.LIB_ID(lib,name));fp.SetPath(k.KIID_PATH('/'+root+'/'+c['uuid']))
 for pad in fp.Pads():
  pn=pad.GetNumber();pin=c['pins'].get(pn)
  if (c['ref'],pn) in actualpins:pad.SetNet(nets[actualpins[(c['ref'],pn)]])
  elif pn and pn!='MP' and pn not in c['pins'] and c['pins']:raise ValueError((c['ref'],'unmapped pad',pn))
  if c['ref'] in ['Q1','J3'] and pin and pin['net']=='GND':pad.SetLocalZoneConnection(k.ZONE_CONNECTION_FULL)
 fp.Reference().SetTextSize(pt(.8,.8));fp.Value().SetVisible(False);board.Add(fp)
 footprints.append((c,fp))
# Coarse non-overlapping placement; no tracks, no copper zones, no manufacturing outputs.
occupied=[];staged=[]
def collide(a,b):return not(a[2]<b[0] or a[0]>b[2] or a[3]<b[1] or a[1]>b[3])
for i,(x,y) in enumerate(mech['parts']['carrier']['mount_holes_local'],1):
 fp=next(f for c,f in footprints if c['ref']==f'H{i}');fp.SetPosition(pt(x+100,y+100));fp.Reference().SetPosition(pt(x+96,y+100) if i==3 else pt(x+100,y+100+(-4 if y>0 else 4)));occupied.append((x-4,y-4,x+4,y+4))
blocked=[(-40,-14,-4,14),(7,-14,21,14)]
def inside(x,y):
 return abs(x)<46 and abs(y)<44 and x*x+y*y<59**2 and not(-40<x<-4 and -14<y<14) and not(7<x<21 and -14<y<14)
ordered=[]
for c,fp in footprints:
 if c['ref'].startswith('H'):continue
 box=fp.GetBoundingBox(False,False);ordered.append((box.GetWidth()*box.GetHeight(),c,fp))
anchors={'J3':(-24,-39),'J2':(32,-18),'C9':(-24,-26),'U3':(-5,-28),'Q1':(9,-25),'U4':(6,-14),'J17':(-40,-23),'J8':(-9,-40),'J1':(-37,23),'C12':(-33,15),'J4':(-29,28),'J5':(-29,39),'U5':(-8,27),'J9':(15,-40),'J6':(-8,39),'J7':(10,20),'J10':(12,37),'J11':(34,34),'J12':(-5,40),'J13':(15,40),'J14':(29,-39),'J15':(43,2),'J16':(43,13),'U1':(32,10),'U2':(1,25),'U6':(15,29),'C10':(13,24),'C11':(-7,30)}
for ref in ['R14','R15','R16','R17','R18','C7','C8']:anchors[ref]=(-5,-26)
for ref in ['R19','R20']:anchors[ref]=(9,-24)
for ref in ['R1','R2','R6','C1','C2']:anchors[ref]=(32,10)
for ref in ['R3','R4','R5','C3']:anchors[ref]=(3,25)
for ref in ['R7','R8','R9','R10','R11','R12','R13','C4','C5','C6']:anchors[ref]=(38,-15)
for ref in ['R21','R22','R23','R24','C13']:anchors[ref]=(-8,27)
for ref in ['C14','C15','R25']:anchors[ref]=(15,29)
priority=['J3','J2','C9','U3','Q1','J17','U1','U2','U5','J11','J4','J5','J1','J8']
def priority_key(entry):
 _,c,fp=entry
 return (priority.index(c['ref']) if c['ref'] in priority else 20,-entry[0])
for _,c,fp in sorted(ordered,key=priority_key):
 candidates=[];target=anchors.get(c['ref'],(0,30))
 for rot in [0,90]:
  fp.SetOrientationDegrees(rot);fp.SetPosition(pt(0,0));bb=fp.GetBoundingBox(False,False)
  x0=k.ToMM(bb.GetX());y0=k.ToMM(bb.GetY());w=k.ToMM(bb.GetWidth())+1;h=k.ToMM(bb.GetHeight())+1
  for y in range(-43,44,2):
   for x in range(-45,46,2):
    rect=(x,y,x+w,y+h)
    if all(inside(xx,yy) for xx,yy in [(x,y),(x+w,y),(x,y+h),(x+w,y+h)]) and not any(collide(rect,bb) for bb in occupied+blocked):
     score=(x+w/2-target[0])**2+(y+h/2-target[1])**2+rot*.001
     candidates.append((score,rot,x,y,x0,y0,rect))
 if candidates:
  _,rot,x,y,x0,y0,rect=min(candidates)
  fp.SetOrientationDegrees(rot);fp.SetPosition(pt(100+x-x0+.5,100+y-y0+.5));occupied.append(rect)
 else:
  fp.SetPosition(pt(165+(len(staged)%6)*20,60+(len(staged)//6)*25));staged.append(c['ref'])
label=k.PCB_TEXT(board);label.SetText('MORI RevA UNROUTED / UNVALIDATED');label.SetPosition(pt(100,148));label.SetTextSize(pt(1,1));label.SetLayer(k.Dwgs_User);board.Add(label)
k.SaveBoard(str(D/(project+'.kicad_pcb')),board)
pro={'meta':{'filename':project+'.kicad_pro','version':1},'board':{'design_settings':{'rules':{'min_clearance':.2,'min_track_width':.25}}},'net_settings':{'classes':[{'name':'Default','clearance':.2,'track_width':.25,'via_diameter':.6,'via_drill':.3,'diff_pair_width':.25,'diff_pair_gap':.25,'diff_pair_via_gap':.25}],'meta':{'version':3}},'schematic':{'meta':{'version':1}}}
(D/(project+'.kicad_pro')).write_text(json.dumps(pro,indent=2)+'\n')
with (D/'carrier_bom.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['ref','value','footprint','section','note']);w.writeheader();w.writerows({key:c.get(key,'') for key in w.fieldnames} for c in cs if c['footprint'])
(D/'generation.json').write_text(json.dumps({'kicad_version':k.GetBuildVersion(),'footprints':len(footprints),'nets':len(nets),'tracks':len(board.GetTracks()),'staged_outside_board':staged,'board_frame':'PCB(x,y)=(BlenderX+100,BlenderY+100) mm; Z117mm proposal','mechanical_source_sha256':mech['mechanical_source_sha256'],'schematic_symbols':len(cs),'fabrication_allowed':False},indent=2)+'\n')
print('Native KiCad generated;',len(footprints),'footprints;',len(nets),'nets;unrouted;',len(staged),'parts need placement')

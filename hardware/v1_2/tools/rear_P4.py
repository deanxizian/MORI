"""MORI rear Type-C + physical master/DISARM interface, P4 prototype.
Rebuild ONLY its own project. No charger, PD controller, purchasing or Gerber.
Dimensions derive from vendor drawings; native checking is separate.
"""
from pathlib import Path
import json,sys,shutil,re,hashlib
import pcbnew as k
from design_P1 import comp,pin,passive,holes,C0603
from native_cad import build,FP
import functional_schematic as fs
from readable_schematic import block
from layout_P3R1 import pt,mm
from body_keepouts_P3R1 import create,rectangle
H=Path(__file__).resolve().parents[1];NAME='MORI_rear_P4';D=H/'kicad'/NAME
CUSTOM=H/'kicad/custom.pretty';CUSTOM.mkdir(exist_ok=True)
PH_SOURCE='https://www.jst-mfg.com/product/pdf/eng/ePH.pdf'
USB_SOURCE='https://www.krhro.com/Product-Details/726.html'
SW_SOURCE='https://item.szlcsc.com/44278924.html'
FUSE_SOURCE='https://www.littelfuse.com/assetdocs/fuse-451-and-453-datasheet?assetguid=533cd5cc-956c-4243-867f-6ab5a62f6ba1'
TVS_SOURCE='https://www.littelfuse.cn/products/overvoltage-protection/tvs-diodes/surface-mount/smf/smf24a'
CC_SOURCE='https://assets.nexperia.com/documents/data-sheet/PESD5V0L1BA.pdf'

def primitive(name,body,pads,holes=()):
 s=f'(footprint "{name}" (version 20241229) (generator "mori_P4") (layer "F.Cu") (attr smd)\n'
 x,y=body
 s+=f'(fp_rect (start {-x/2} {-y/2}) (end {x/2} {y/2}) (stroke (width 0.1) (type default)) (fill none) (layer "F.Fab"))\n'
 xx=max(x/2,max(abs(p[1])+p[3]/2 for p in pads))+.25;yy=max(y/2,max(abs(p[2])+p[4]/2 for p in pads))+.25
 s+=f'(fp_rect (start {-xx} {-yy}) (end {xx} {yy}) (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))\n'
 # Corner lines keep assembly outline visible without silk over exposed pads.
 for a,c in [((-x/2,-y/2),(x/2,-y/2)),((-x/2,y/2),(x/2,y/2))]:
  s+=f'(fp_line (start {a[0]} {a[1]}) (end {c[0]} {c[1]}) (stroke (width .12) (type default)) (layer "F.SilkS"))\n'
 for n,px,py,sx,sy in pads:s+=f'(pad "{n}" smd rect (at {px} {py}) (size {sx} {sy}) (layers "F.Cu" "F.Paste" "F.Mask"))\n'
 for x,y,drill in holes:s+=f'(pad "" np_thru_hole circle (at {x} {y}) (size {drill} {drill}) (drill {drill}) (layers "*.Cu" "*.Mask"))\n'
 s+=')\n';(CUSTOM/(name+'.kicad_mod')).write_text(s)
 return 'MORI_Custom:'+name

def ph(n,horizontal=False):
 fn=f'JST_PH_{"S" if horizontal else "B"}{n}B-PH-K_1x{n:02d}_P2.00mm_{"Horizontal" if horizontal else "Vertical"}'
 f=k.FootprintLoad(str(FP/'Connector_JST.pretty'),fn);assert f,fn
 for p in f.Pads():p.SetSize(pt(1.35,1.35))
 new=fn+'__P4_ANNULUS';f.SetFPID(k.LIB_ID('MORI_Custom',new));k.PCB_IO_MGR.FindPlugin(k.PCB_IO_MGR.KICAD_SEXP).FootprintSave(str(CUSTOM),f)
 return 'MORI_Custom:'+new

def usb():
 fn='USB_C_Receptacle_HRO_TYPE-C-31-M-12';f=k.FootprintLoad(str(FP/'Connector_USB.pretty'),fn)
 for p in f.Pads():
  if p.GetNumber()=='SH':p.SetSize(pt(1.1,k.ToMM(p.GetSize().y)))
 new=fn+'__P4_ANNULUS';f.SetFPID(k.LIB_ID('MORI_Custom',new));k.PCB_IO_MGR.FindPlugin(k.PCB_IO_MGR.KICAD_SEXP).FootprintSave(str(CUSTOM),f)
 return 'MORI_Custom:'+new

def design():
 sw=primitive('SOFNG_MS202V_G3_P4',(9.1,3.5),[(str(i+1),x,y,1.2,2.0) for i,(x,y) in enumerate([(x,y) for y in [-2.8,2.8] for x in [-2.5,0,2.5]])],[(-3.4,0,.9),(3.4,0,.9)])
 fu=primitive('Littelfuse_451_6.1x2.69_P4',(6.1,2.69),[('1',-2.45,0,1.96,3.15),('2',2.45,0,1.96,3.15)])
 usbpins={n:pin(n,'GND') for n in ['A1','A12','B1','B12','SH']}
 usbpins.update({n:pin(n,'VBUS_RAW') for n in ['A4','A9','B4','B9']})
 usbpins.update({n:pin(n,None) for n in ['A6','A7','A8','B6','B7','B8']})
 usbpins.update({'A5':pin('CC1','CC1'),'B5':pin('CC2','CC2')})
 cs=[comp('USB1','HRO TYPE-C-31-M-12 / charge only',usb(),usbpins,[12,3,180],'B',source=USB_SOURCE,note='C165948. A/B VBUS tied, A/B GND and shell tied; D+/D-/SBU NC. CC1/CC2 go separately to external sink controller. No local Rd.'),
 comp('SW1','SOFNG MS-202V-G3',sw,{1:pin('A1','MASTER_RETURN'),2:pin('COM1','GND'),3:pin('B1',None),4:pin('A2','LOOP_3V3'),5:pin('COM2','CLR_N'),6:pin('B2',None)},[12,11.8,0],source=SW_SOURCE,note='C42378287. 0.5A/30VDC rating; signal contacts only. Locally defined pad numbering on top assembly view. State A:1-2,4-5; B:2-3,5-6. Verify with DMM before assembly.'),
 comp('J2','CHARGER / PH5 SIDE ENTRY',ph(5,True),{1:'VBUS_FUSED',2:'GND',3:'CC1',4:'CC2',5:'VBUS_RAW'},[16,23,0],'B',source=PH_SOURCE,note='JST S5B-PH-K-S(LF)(SN),C157923; PHR-5/SPH-002T-P0.5S. Pin5 only raw-VBUS presence sense to power J16. PCB top view pin1 at X16.'),
 comp('J3','MASTER + DISARM / PH4',ph(4),{1:'MASTER_RETURN',2:'GND',3:'LOOP_3V3',4:'CLR_N'},[9,18,0],source=PH_SOURCE,note='JST B4B-PH-K-S(LF)(SN),C131334; PHR-4/SPH-002T-P0.5S. Pins1/2 to power J19, pins3/4 to motion J8.'),
 comp('F1','045101.5MRL / 1.5A',fu,{1:'VBUS_RAW',2:'VBUS_FUSED'},[4,4.8,90],'B',source=FUSE_SOURCE,note='Littelfuse C185113; 125VDC very-fast fuse. 1A continuous interface design target after thermal derating; downstream electronic current limit required.'),
 comp('D1','SMF24A / Littelfuse','Diode_SMD:D_SOD-123F',{1:'VBUS_FUSED',2:'GND'},[20,5,90],'B',source=TVS_SOURCE,note='C315999; 24V stand-off, 38.9V pulse clamp. Not precise overvoltage protection. Downstream PD/charger OVP required.'),
 comp('D2','PESD5V0L1BA,115','Diode_SMD:D_SOD-323',{1:'CC1',2:'GND'},[10,9.5,0],'B',source=CC_SOURCE,note='Nexperia C85380; bidirectional CC ESD, no VBUS short protection.'),
 comp('D3','PESD5V0L1BA,115','Diode_SMD:D_SOD-323',{1:'CC2',2:'GND'},[14,9.5,180],'B',source=CC_SOURCE,note='Nexperia C85380; bidirectional CC ESD.'),
 comp('C1','100n / 50V / X7R',C0603,{1:'VBUS_FUSED',2:'GND'},[20,17,0],'B',source='https://www.murata.com/en-us/products/productdetail?partno=GRM188R71H104KA93%23',note='GRM188R71H104KA93D; exact procurement price pending. Local port capacitance only; downstream inrush must include total sink capacitance.')]
 holes(cs,[(3,11),(21,11)])
 return dict(size=[24,25],layers=2,clearance=.2,components=cs,module_outlines=[],description='Rear charging connector and low-current physical power/DISARM switch; external PD sink + 3S CC/CV charger REQUIRED. PROTOTYPE / NOT_TESTED.')

def switch_graphics(d):
 # Replace only the graphic of SW1; retain native pins and numbering.
 def graphic():
  a=[]
  for yc in [-5,5]:
   a += [f'(polyline (pts (xy {fs.mm(-6)} {fs.mm(-yc)}) (xy {fs.mm(-2)} {fs.mm(-yc)}) (xy {fs.mm(5.5)} {fs.mm(-(yc-3))})) (stroke (width .254) (type default)) (fill (type none)))']
   for xx,yy in [(-2,yc),(6,yc-3),(6,yc+3)]:a.append(f'(circle (center {fs.mm(xx)} {fs.mm(-yy)}) (radius .5) (stroke (width .254) (type default)) (fill (type none)))')
  return a
 for seq in [d.libs,d.local_libs]:
  for i,s in enumerate(seq):
   n=fs.sexpr(s)
   if n[0]!='symbol' or json.loads(n[1]) not in ['MORI:SW1','SW1']:continue
   for ch in n:
    if isinstance(ch,list) and ch[:2]==['symbol','"SW1_0_1"']:ch[2:]=[fs.sexpr(g) for g in graphic()]
   seq[i]=fs.encode(n)

def render(name):
 d=fs.Drawing(name);d.paper=(594,420)
 d.text('MORI / REAR TYPE-C + POWER SWITCH / P4',5,6,2.4)
 d.text('PROTOTYPE / NOT_TESTED. No PD negotiation or battery CC/CV charging on this interface board.',5,10,1.15)
 b=block(d,'01  USB-C charge inlet / fuse / CC pass-through',5,15,220,77,'5-20V only after external sink negotiation. 1A continuous target; current limit and 3S charger remain external.')
 pins={n:(12,-10,'R') for n in ['A4','A9','B4','B9']};pins.update({n:(0,22,'B') for n in ['A1','A12','B1','B12','SH']})
 pins.update({'A5':(12,2,'R'),'B5':(12,10,'R')});pins.update({n:(-12,-12+i*5,'L') for i,n in enumerate(['A6','A7','A8','B6','B7','B8'])})
 b.place('USB1',25,34,kind='ic',pins=pins,w=20,h=40,short='USB-C / HRO 31-M-12')
 b.place('F1',55,24,kind='fuse',short='1.5A / 125VDC');b.join(('USB1','A4'),('F1',1))
 b.place('J2',190,35,pitch=8);b.join(('F1',2),('J2',1),via=[(90,24),(90,19)])
 b.place('D1',106,38,kind='zener',orient='v');b.join(('F1',2),('D1',1),via=[(90,24),(90,35)]);b.supply('D1',2,up=False,length=5)
 b.place('C1',124,38,orient='v');b.join(('D1',1),('C1',1));b.supply('C1',2,up=False,length=5)
 b.join(('USB1','A5'),('J2',3),via=[(151,36),(151,35)])
 b.join(('USB1','B5'),('J2',4),via=[(160,44),(160,43)])
 b.place('D2',64,53,kind='zener',orient='v',short='CC1 ESD');b.join(('USB1','A5'),('D2',1),via=[(64,36)]);b.supply('D2',2,up=False)
 b.place('D3',80,61,kind='zener',orient='v',short='CC2 ESD');b.join(('USB1','B5'),('D3',1),via=[(80,44)]);b.supply('D3',2,up=False)
 b.mark('J2',5);b.mark('J2',2)
 b=block(d,'02  Physical master switch + latch-clear loop',5,94,132,62,'ON closes both poles. OFF / broken harness opens both. A fresh local ARM is required after switch-on.')
 swpins={'2':(-8,-5,'L'),'1':(8,-8,'R'),'3':(8,-2,'R'),'5':(-8,5,'L'),'4':(8,2,'R'),'6':(8,8,'R')}
 b.place('SW1',55,30,kind='ic',pins=swpins,w=12,h=22,short='DPDT / 0.5A signal only')
 b.place('J3',100,29,pitch=6)
 b.join(('SW1',1),('J3',1),via=[(80,22),(80,20)])
 b.join(('SW1',4),('J3',3),via=[(72,32)])
 b.join(('SW1',5),('J3',4),via=[(38,35),(38,47),(85,47),(85,38)])
 b.mark('SW1',2);b.mark('J3',2)
 b=block(d,'03  Mechanical and test interfaces',139,94,86,62,'PCB grows 11mm inward. Actual USB/switch opening positions require mechanical update.')
 b.place('H1',22,24);b.place('H2',61,24)
 d.text('H1=(3,11), H2=(21,11); NPTH 2.2mm',143,134,1.1)
 d.text('24 x 25 x 1.6mm; no exposed top metal on side seats.',143,140,1.05)
 switch_graphics(d);summary=d.finish()
 p=D/(name+'.kicad_sch');s=p.read_text().replace('(rev "S2 drawing layout")','(rev "P4 interface prototype")').replace('PROTOTYPE / UNVALIDATED - electrical design unchanged','PROTOTYPE / NOT_TESTED - PD sink and 3S charger external').replace('2026-09-22','2026-09-23');p.write_text(s)
 (D/'schematic_layout.json').write_text(json.dumps(summary,indent=2)+'\n')

def rules(b):
 import rules_P3 as old
 source=Path(old.__file__).read_text().replace("out=R/'layout_P3'","out=R/'layout_P4'")
  # A normal module globals dictionary is required by the executed functions.
 scope=dict(__file__=str(old.__file__));exec(compile(source,str(old.__file__),'exec'),scope)
 original=scope['roles']
 def roles(kind,nets):
  r=original(kind,nets);r['VCC']+=['/VBUS_RAW','/VBUS_FUSED'];return r
 scope['roles']=roles;scope['write_rules']('rear',D,NAME,list(b.GetNetsByName()))
 # Start from checked electrical clearance/DRC preferences; no exclusions.
 pro=json.loads((H/'kicad/MORI_imu_P4/MORI_imu_P4.kicad_pro').read_text());pro['meta']['filename']=NAME+'.kicad_pro';pro['board']['design_settings']['drc_exclusions']=[]
 pro['net_settings']['netclass_patterns']=[];pro['net_settings']['classes']=[dict(name='Default',clearance=.2,track_width=.2,via_diameter=.8,via_drill=.3)]
 (D/(NAME+'.kicad_pro')).write_text(json.dumps(pro,indent=2)+'\n')
 for x1,x2 in [(0,6.5),(17.5,24)]:
  z=k.ZONE(b);z.SetIsRuleArea(True);z.SetLayer(k.F_Cu);z.SetZoneName('TOP_MOUNT_SEAT_'+str(x1));z.SetDoNotAllowTracks(False);z.SetDoNotAllowVias(True);z.SetDoNotAllowPads(False);z.SetDoNotAllowFootprints(False);z.SetDoNotAllowZoneFills(False);z.Outline().BooleanAdd(rectangle((x1,0,x2,14)));b.Add(z)
 for f in b.GetFootprints():
  if not f.GetReference().startswith('H'):continue
  from body_keepouts_P3R1 import polygon
  import math
  x,y=k.ToMM(f.GetPosition().x),k.ToMM(f.GetPosition().y)
  for layer in [k.F_Cu,k.B_Cu]:
   z=k.ZONE(b);z.SetIsRuleArea(True);z.SetLayer(layer);z.SetZoneName('SCREW_'+f.GetReference()+'_'+str(layer));z.SetDoNotAllowTracks(True);z.SetDoNotAllowVias(True);z.SetDoNotAllowPads(False);z.SetDoNotAllowFootprints(False);z.SetDoNotAllowZoneFills(True);z.Outline().BooleanAdd(polygon([(x+2.75*math.cos(i*math.pi/48),y+2.75*math.sin(i*math.pi/48)) for i in range(96)]));b.Add(z)
 log=create(b);lines=[]
 for f in b.GetFootprints():
  ref=f.GetReference()
  if not any(z.GetZoneName()=='NETBODY_'+ref for z in b.Zones()):continue
  allowed=sorted({str(p.GetNetname()) for p in f.Pads() if p.GetNetname()})
  cond="A.intersectsArea('NETBODY_"+ref+"')"+''.join(" && A.NetName != '"+n+"'" for n in allowed)
  lines.append('(rule '+json.dumps('P4 '+ref+' unrelated nets outside body')+'\n (condition '+json.dumps(cond)+')\n (constraint disallow track via))')
 with (D/(NAME+'.kicad_dru')).open('a') as out:out.write('\n'.join(lines)+'\n')
 r=H/'layout_P4/reports'/NAME;r.mkdir(parents=True,exist_ok=True);(r/'body_keepouts.json').write_text(json.dumps(log,indent=2)+'\n')
 for layer in [k.F_Cu,k.B_Cu]:
  z=k.ZONE(b);z.SetLayer(layer);z.SetNet(b.GetNetsByName()['/GND']);z.SetLocalClearance(mm(.2));z.SetPadConnection(k.ZONE_CONNECTION_FULL);z.SetThermalReliefGap(mm(.254));z.SetThermalReliefSpokeWidth(mm(.3));z.Outline().BooleanAdd(rectangle((.5,.5,23.5,24.5)));b.Add(z)
 k.ZONE_FILLER(b).Fill(b.Zones())

if __name__=='__main__':
 if D.exists() and '--rebuild' not in sys.argv:raise SystemExit('Project exists; use --rebuild only to deliberately discard rear routing.')
 original=fs.render_project;fs.render_project=render
 try:build(NAME,design())
 finally:fs.render_project=original
 p=D/(NAME+'.kicad_pcb');b=k.LoadBoard(str(p));rules(b);k.SaveBoard(str(p),b)
 print(NAME,'native project created; unrouted prototype, mechanical update required')

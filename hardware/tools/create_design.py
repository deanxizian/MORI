"""Authoritative carrier connectivity + reproducible pin/wire/BOM exports."""
from pathlib import Path
import csv,json
R=Path(__file__).resolve().parents[1]
def csvout(name,rows):
 with (R/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
pin_defs=[
 ('BATTERY',1,'J3.4','BAT_ADC','in','ADC1_CH0; 30k/10k divider + 1k/100nF; 4x voltage'),
 ('NTC_L',2,'J3.5','NTC_L','in','ADC1_CH1; 10k pull-up and NCP18XH103F03RB B3380'),
 ('NTC_R',4,'J1.4','NTC_R','in','ADC1_CH3; same NTC as left'),
 ('AIN1',5,'J1.5','AIN1','out','LEDC channel0 timer0 20kHz 10bit'),
 ('AIN2',6,'J1.6','AIN2','out','LEDC channel1 timer0'),
 ('BIN1',7,'J1.7','BIN1','out','LEDC channel2 timer0'),
 ('BIN2',8,'J1.12','BIN2','out','LEDC channel3 timer0'),
 ('ENC_LA',9,'J1.15','ENC_LA','in','PCNT unit0 channel0; 1us glitch filter'),
 ('ENC_LB',10,'J1.16','ENC_LB','in','PCNT unit0 channel1; x4 total'),
 ('ENC_RA',11,'J1.17','ENC_RA','in','PCNT unit1 channel0'),
 ('ENC_RB',12,'J1.18','ENC_RB','in','PCNT unit1 channel1'),
 ('LCD_MOSI',13,'J1.19','LCD_MOSI','out','SPI2 dedicated to LCD, DMA stripe'),
 ('LCD_CLK',14,'J1.20','LCD_CLK','out','SPI2 20MHz initial'),
 ('LCD_CS',15,'J1.8','LCD_CS','out','active low'),
 ('IMU_INT',16,'J1.9','IMU_INT','in','LSM6DSOX INT1; gyro DRDY rising, 416Hz'),
 ('SDA',17,'J1.10','SDA','bidir','I2C0 400kHz; IMU0x6A + INA2190x40; sole owner control task'),
 ('SCL',18,'J1.11','SCL','out','I2C0; pull-ups only to3V3'),
 ('ARM',21,'J3.18','ARM','out','10k pulldown; hardware watchdog/ESTOP/FAULT AND gate'),
 ('LCD_DC',39,'J3.9','LCD_DC','out','JTAG unavailable on39-42'),
 ('LCD_RST',40,'J3.8','LCD_RST','out','active low'),
 ('HEAD',41,'J3.7','HEAD_PWM','out','LEDC channel4 timer1 50Hz; SER0037 270deg; gear8:14; +/-50deg head commissioning, disabled until calibrated'),
 ('HEARTBEAT',42,'J3.6','HEARTBEAT','out','software toggle only after successful control frame; no free-running PWM'),
 ('FAULT',47,'J3.17','NFAULT','in','DRV open drain; 10k pull-up3V3; falling ISR and hardware gate'),
 ('ESTOP',48,'J3.16','ESTOP_OK','in','RUN NC contact passes3V3; 10k pulldown. v1.1 REQUIRED')]
rows=[]
for i,(name,gpio,header,net,direction,note) in enumerate(pin_defs,1):
 rows.append(dict(signal=name,gpio=gpio,devkit_header=header,carrier_pin=f'J2.{i}',net=net,direction=direction,logic_V='0-3.3' if name not in ['BATTERY','NTC_L','NTC_R'] else 'analog <=3.1',supply='3V3',connector='IDC 2x13 2.54 mm keyed; mechanically keyed adapter to DevKit headers',view='carrier component side; pin1 square/cable red stripe; numbering per PCB footprint, NOT mating-face mirror',wire='AWG28 signal / <=100mm analog-I2C',notes=note))
csvout('pinmap.csv',rows)
comps=[]
def add(ref,value,fp,pins,kind='block',note='',section='IO'):
 # pin tuple name,net,type (numbers follow order unless dict provided)
 if isinstance(pins,list):pins={str(i+1):{'name':p[0],'net':p[1],'type':p[2] if len(p)>2 else 'passive'} for i,p in enumerate(pins)}
 comps.append(dict(ref=ref,value=value,footprint=fp,pins=pins,kind=kind,note=note,section=section))
def two(ref,value,net1,net2,fp='Resistor_SMD:R_0805_2012Metric',names=('1','2'),section='PASSIVES'):
 add(ref,value,fp,[(names[0],net1),(names[1],net2)],section=section)
def conn(ref,value,nets,types=None,fp=None,section='IO'):
 n=len(nets)
 fp=fp or f'Connector_JST:JST_XH_B{n}B-XH-A_1x{n:02d}_P2.50mm_Vertical'
 add(ref,value,fp,[(net,net,(types[i] if types else 'passive')) for i,net in enumerate(nets)],kind='connector',section=section)
# J1 receives factory pack through external fuse, master switch and reverse-FET assembly.
conn('J1','VMAIN_from_protected_pack',['VMAIN','GND'],['power_out','power_out'],'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2_1x02_P5.00mm_Horizontal',section='POWER')
mpins=[]
for _,_,_,net,d,_ in pin_defs:mpins.append((net,net,{'in':'bidirectional','out':'output','bidir':'bidirectional'}[d]))
mpins += [('3V3','3V3','power_out'),('GND','GND','power_in')]
add('J2','DevKit_v1.1_N8R8_HARNESS','Connector_IDC:IDC-Header_2x13_P2.54mm_Vertical',mpins,'connector','Remote board represented with functional pin directions')
conn('J3','DRV8833_Pololu2130_HARNESS',['VM_DRV_IN','VM_MOTOR','GND','AIN1','AIN2','BIN1','BIN2','NSLEEP','NFAULT','LM1','LM2','RM1','RM2','GND'],['power_in','power_out','power_in','input','input','input','input','input','open_collector','output','output','output','output','power_in'])
for ref,side in [('J4','L'),('J5','R')]:
 add(ref,'Motor4863_CUSTOM_XH6','Connector_JST:JST_XH_B6B-XH-A_1x06_P2.50mm_Vertical',[('GND','GND','power_in'),('B',f'ENC_{side}B_5V','output'),('A',f'ENC_{side}A_5V','output'),('VCC','DEVKIT_5V','power_in'),('M2',side+'M2','passive'),('M1',side+'M1','passive')],'connector','CUSTOM retermination:1 green GND;2 white B;3 yellow A;4 blue Vcc 5V;5 black M2;6 red M1. NOT factory header order. LVC14 level shifts required.')
conn('J6','Adafruit4438_IMU',['3V3','GND','SDA','SCL','IMU_INT'],['power_in','power_in','bidirectional','input','output'])
conn('J7','INA219_LOGIC',['GND','3V3','SDA','SCL'],['power_in','power_in','bidirectional','input'],fp='Connector_JST:JST_SH_BM04B-SRSS-TB_1x04-1MP_P1.00mm_Vertical')
conn('J8','INA219_SHUNT_IN_OUT',['VMAIN','VM_DRV_IN'],['power_in','power_out'],fp='TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2_1x02_P5.00mm_Horizontal',section='POWER')
conn('J9','Waveshare19192_LCD',['3V3','GND','LCD_MOSI','LCD_CLK','LCD_CS','LCD_DC','LCD_RST','3V3'],['power_in','power_in','input','input','input','input','input','input'],fp='Connector_JST:JST_PH_B8B-PH-K_1x08_P2.00mm_Vertical')
conn('J10','SER0037_JR_GND_5V_SIGNAL',['GND','HEAD_5V','HEAD_PWM'],['power_in','power_in','input'],fp='Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical')
conn('J11','ESTOP_2NC_EXTERNAL',['3V3','ESTOP_OK','SERVO_5V_RAW','HEAD_5V'],fp='Connector_JST:JST_VH_B4P-VH_1x04_P3.96mm_Vertical',section='SAFETY')
conn('J12','BUCK_LOGIC_UNPLUG_FOR_USB',['VMAIN','GND','LOGIC_5V_RAW'],['power_in','power_in','power_out'],section='POWER')
conn('J13','BUCK_SERVO_D24V22F5',['VMAIN','GND','SERVO_5V_RAW'],['power_in','power_in','power_out'],section='POWER')
conn('J14','DevKit_5V_KEEP_FOR_ENCODERS',['DEVKIT_5V','GND'],['power_in','power_in'],section='POWER')
for ref,net in [('J15','NTC_L_RAW'),('J16','NTC_R_RAW')]:conn(ref,'10k_B3380_ON_MOTOR',[net,'GND'])
conn('J17','DUMP_RESISTOR_HS25_5R6J',['VM_MOTOR','DUMP_DRAIN'],fp='TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2_1x02_P5.00mm_Horizontal',section='CLAMP')
# Watchdog pin numbering per CD74HC123E PDIP16, both halves included.
wp={1:('1A','GND','input'),2:('1B','HEARTBEAT','input'),3:('1CLR','ARM','input'),4:('1Qbar',None,'output'),5:('2Q',None,'output'),6:('2C',None,'passive'),7:('2RC',None,'passive'),8:('GND','GND','power_in'),9:('2A','GND','input'),10:('2B','GND','input'),11:('2CLR','GND','input'),12:('2Qbar',None,'output'),13:('1Q','WD_OK','output'),14:('1C','WD_C','passive'),15:('1RC','WD_RC','passive'),16:('VCC','3V3','power_in')}
add('U1','CD74HC123E','Package_DIP:DIP-16_W7.62mm',{str(k):dict(name=v[0],net=v[1],type=v[2]) for k,v in wp.items()},section='SAFETY')
gp={1:('1A','ARM','input'),2:('1B','WD_OK','input'),3:('1Y','ARM_WD','output'),4:('2A','ARM_WD','input'),5:('2B','ESTOP_OK','input'),6:('2Y','RUN_OK','output'),7:('GND','GND','power_in'),8:('3Y','NSLEEP','output'),9:('3A','RUN_OK','input'),10:('3B','NFAULT','input'),11:('4Y',None,'output'),12:('4A','GND','input'),13:('4B','GND','input'),14:('VCC','3V3','power_in')}
add('U2','SN74HC08N','Package_DIP:DIP-14_W7.62mm',{str(k):dict(name=v[0],net=v[1],type=v[2]) for k,v in gp.items()},section='SAFETY')
# SN74LVC14A: 5.5V tolerant inputs at 3.3V Vcc. Both A/B inverted together.
lp={1:('1A','ENC_LA_5V','input'),2:('1Y','ENC_LA','output'),3:('2A','ENC_LB_5V','input'),4:('2Y','ENC_LB','output'),5:('3A','ENC_RA_5V','input'),6:('3Y','ENC_RA','output'),7:('GND','GND','power_in'),8:('4Y','ENC_RB','output'),9:('4A','ENC_RB_5V','input'),10:('5Y',None,'output'),11:('5A','GND','input'),12:('6Y',None,'output'),13:('6A','GND','input'),14:('VCC','3V3','power_in')}
add('U5','SN74LVC14AD','Package_SO:SOIC-14_3.9x8.7mm_P1.27mm',{str(k):dict(name=v[0],net=v[1],type=v[2]) for k,v in lp.items()},section='ENCODER')
two('C13','100nF','3V3','GND','Capacitor_SMD:C_0805_2012Metric',section='ENCODER')
# Bus-powered clamp stays operational when the master battery connector opens.
cp={1:('OUT1','CLAMP_OUT','open_collector'),2:('IN1-','VREF_2V495','input'),3:('IN1+','BUS_DIV','input'),4:('V-','GND','power_in'),5:('IN2+','GND','input'),6:('IN2-','VREF_2V495','input'),7:('OUT2',None,'open_collector'),8:('V+','VM_MOTOR','power_in')}
add('U3','LM393P','Package_DIP:DIP-8_W7.62mm',{str(k):dict(name=v[0],net=v[1],type=v[2]) for k,v in cp.items()},section='CLAMP')
# TI TL431BCLP TO-92: pin1 REF, pin2 A, pin3 K.
add('U4','TL431BCLP','Package_TO_SOT_THT:TO-92_Inline',[('REF','VREF_2V495','input'),('A','GND','passive'),('K','VREF_2V495','open_collector')],section='CLAMP')
add('Q1','IRLZ44NPBF_DUMP','Package_TO_SOT_THT:TO-220-3_Vertical',[('G','DUMP_GATE','input'),('D','DUMP_DRAIN','passive'),('S','GND','passive')],section='CLAMP')
two('D1','SS34_USB_ISOLATION','DEVKIT_5V','LOGIC_5V_RAW','Diode_SMD:D_SMA',('K','A'),'POWER')
for ref,value,n1,n2,sec in [
 ('R1','10k','ARM','GND','SAFETY'),('R2','10k','HEARTBEAT','GND','SAFETY'),('R3','10k','ESTOP_OK','GND','SAFETY'),('R4','10k','3V3','NFAULT','SAFETY'),('R5','10k','NSLEEP','GND','SAFETY'),('R6','47k','3V3','WD_RC','SAFETY'),
 ('R7','30k_1pct','VMAIN','BAT_DIV','ADC'),('R8','10k_1pct','BAT_DIV','GND','ADC'),('R9','1k','BAT_DIV','BAT_ADC','ADC'),
 ('R10','10k_1pct','3V3','NTC_L_RAW','ADC'),('R11','10k_1pct','3V3','NTC_R_RAW','ADC'),('R12','1k','NTC_L_RAW','NTC_L','ADC'),('R13','1k','NTC_R_RAW','NTC_R','ADC'),
 ('R14','25k5_0.1pct','VM_MOTOR','BUS_DIV','CLAMP'),('R15','10k_0.1pct','BUS_DIV','GND','CLAMP'),('R16','2M2_1pct','CLAMP_OUT','BUS_DIV','CLAMP'),('R17','2k2','VM_MOTOR','VREF_2V495','CLAMP'),('R18','4k7','VM_MOTOR','CLAMP_OUT','CLAMP'),('R19','100R','CLAMP_OUT','DUMP_GATE','CLAMP'),('R20','100k','DUMP_GATE','GND','CLAMP'),
 ('R21','100k','ENC_LA_5V','GND','ENCODER'),('R22','100k','ENC_LB_5V','GND','ENCODER'),('R23','100k','ENC_RA_5V','GND','ENCODER'),('R24','100k','ENC_RB_5V','GND','ENCODER')]:two(ref,value,n1,n2,section=sec)
# Module I2C pull-ups (10k on IMU and 10k on INA219) parallel to ~5k; no extra pull-ups initially.
for ref,val,n1,n2 in [('C1','1uF_50V_X7R','WD_C','WD_RC'),('C2','100nF','3V3','GND'),('C3','100nF','3V3','GND'),('C4','100nF','BAT_ADC','GND'),('C5','100nF','NTC_L','GND'),('C6','100nF','NTC_R','GND'),('C7','100nF_25V','VM_MOTOR','GND'),('C8','1nF_C0G','BUS_DIV','GND')]:two(ref,val,n1,n2,'Capacitor_SMD:C_0805_2012Metric',section='DECOUPLING')
for ref,val,n1 in [('C9','1000uF_16V','VM_MOTOR'),('C10','470uF_10V','SERVO_5V_RAW'),('C11','100uF_10V','LOGIC_5V_RAW'),('C12','100uF_16V','VMAIN')]:two(ref,val,n1,'GND','Capacitor_THT:CP_Radial_D10.0mm_P5.00mm',('+','-'),'POWER')
for i,net in enumerate(['GND','VMAIN','VM_MOTOR','DEVKIT_5V','3V3','ARM','WD_OK','NSLEEP','NFAULT','BUS_DIV','CLAMP_OUT'],1):add(f'TP{i}',net,'TestPoint:TestPoint_Pad_D1.5mm',[(net,net,'passive')],section='TESTPOINT')
next(c for c in comps if c['ref']=='J12')['note']='UNPLUG whole J12 logic-buck harness before USB; manufacturer power modes mutually exclusive. Keep J14 connected so USB also supplies encoder 5V. Battery may power motors/head separately.'
next(c for c in comps if c['ref']=='J14')['note']='KEEP J14 connected in both supply modes: DevKit 5V and encoder bus. Disconnect J12 logic buck before USB; do not cut encoder power by unplugging J14.'
(R/'kicad/connectivity.json').write_text(json.dumps(comps,indent=2)+'\n')
# Every carrier port pin maps to a named, physically checkable external endpoint.
wire=[]
external={
 'J1':['protected main bus after fuse/switch/AO4407A','battery/PSU star ground'],
 'J2':[r['devkit_header'] for r in rows]+['DevKit J1.1 3V3','DevKit J1.22 GND'],
 'J3':['DRV VIN','DRV VMM','DRV GND','DRV AIN1','DRV AIN2','DRV BIN1','DRV BIN2','DRV SLP (remove stock pull-up)','DRV FLT','DRV AOUT1','DRV AOUT2','DRV BOUT1','DRV BOUT2','DRV GND'],
 'J4':['left motor custom XH1 green','left motor custom XH2 white','left motor custom XH3 yellow','left motor custom XH4 blue','left motor custom XH5 black','left motor custom XH6 red'],
 'J5':['right motor custom XH1 green','right motor custom XH2 white','right motor custom XH3 yellow','right motor custom XH4 blue','right motor custom XH5 black','right motor custom XH6 red'],
 'J6':['IMU VIN 3.3V','IMU GND','IMU SDA/SDI','IMU SCL/SCK','IMU INT1'],
 'J7':['INA219 GND','INA219 VCC 3.3V','INA219 SDA','INA219 SCL'],
 'J8':['INA219 VIN+ terminal','INA219 VIN- terminal'],
 'J9':['LCD VCC','LCD GND','LCD DIN','LCD CLK','LCD CS','LCD DC','LCD RST','LCD BL'],
 'J10':['SER0037 brown GND','SER0037 red +5V','SER0037 yellow signal'],
 'J11':['E-stop NC1 input (3V3)','E-stop NC1 return; open=stop','E-stop NC2 input (5V)','E-stop NC2 return to head supply'],
 'J12':['D24V10F5 VIN','D24V10F5 GND','D24V10F5 VOUT'],
 'J13':['D24V22F5 VIN','D24V22F5 GND','D24V22F5 VOUT'],
 'J14':['DevKit J1.21 5V','DevKit J1.22 GND'],
 'J15':['left motor insulated NTC lead1','left motor NTC lead2'],
 'J16':['right motor insulated NTC lead1','right motor NTC lead2'],
 'J17':['HS25 5R6J resistor lead1','HS25 5R6J resistor lead2']}
for c in comps:
 if c['ref'] not in external:continue
 for pn,pin in c['pins'].items():
  net=pin['net'];idx=int(pn)-1
  gpio=next((row['gpio'] for row in rows if row['net']==net),'')
  high=net in ['VMAIN','VM_DRV_IN','VM_MOTOR','DUMP_DRAIN'];motor=net in ['LM1','LM2','RM1','RM2']
  gauge='AWG20; <=0.5m round trip; 3A bus / 1.6A dump pulse' if high else ('stock motor wire: verify gauge; reterminate JST XH6 with correct terminals; <=0.622A/ch peak' if c['ref'] in ['J4','J5'] else 'AWG22 power/GND; AWG28 signal; <=0.15m')
  level='6.0-8.4V; bus transient acceptance <10.0V' if high or motor else ('5V' if '5V' in net else '0-3.3V')
  wire.append(dict(carrier=c['ref'],pin=pn,net=net,to=external[c['ref']][idx],gpio=gpio,direction=pin['type'],level=level,connector=c['footprint'],view='carrier component side, pin1 square; mating face mirrored; use pin number + continuity, never color alone',wire=gauge,notes=c['note']))
# External battery/charge path is explicit and not silently represented as integrated on the PCB.
for start,end,net,note in [('pack +','F1 3A input','PACK_PLUS','factory XT30U-F recessed live contacts; verify embossed +/-'),('F1 out','SW_MAIN in','FUSED_PLUS','Littelfuse0287003.PXCN in DC holder'),('SW_MAIN out','AO4407A pins5-8 D','SWITCHED_PLUS','main disconnect rated >=5A 12VDC; short unfused lead'),('AO4407A pins1-3 S','J1.1','VMAIN','100k gate pin4 toGND; reverse FET allows bidirectional channel when on'),('pack -','J1.2 star','GND','motor return and logic return meet here'),('charger CH-L7412SM centre +','disconnected pack XT30 +','CHARGE_PLUS','robot connector physically disconnected before charging'),('charger barrel sleeve -','disconnected pack XT30 -','CHARGE_GND','manufacturer-prepared adapter; no on-board charger')]:
 wire.append(dict(carrier=start,pin='',net=net,to=end,gpio='',direction='power',level='8.4V max normal',connector='AMASS XT30U matched / factory charger adapter',view='embossed polarity + continuity, not wire color',wire='AWG20 main / pack stock22AWG',notes=note))
csvout('wiring.csv',wire)
# Fixed main route; budget estimates are deliberately distinct from live list prices.
bom=[]
def item(group,purpose,qty,mpn,params,dim,mass,url,price,price_type,status,minimal=True,alternative='none'):
 bom.append(dict(group=group,purpose=purpose,quantity=qty,mpn=mpn,key_parameters=params,dimensions_mm=dim,mass_g=mass,procurement_channel=url,currency='USD',unit_price=price,price_type=price_type,price_date='2026-09-21',shipping_included='NO; import tax and shipping unknown',alternative=alternative,confirmation_status=status,minimal_balance_included='yes' if minimal else 'no'))
P='https://www.pololu.com/product/'
item('balance','wheel motor',2,'Pololu 4863 25D MP12V 20.408667:1 48CPR','12V;380rpm;1.8A stall;48CPR x4;2S and0.39ohm limit','diameter25 x65 +12.5 shaft',98,P+'4863',53.95,'observed_list','datasheet verified; buy bench pair, not production')
item('balance','MCU',1,'ESP32-S3-DevKitC-1-N8R8 v1.1','WROOM-1-N8R8;8MB Flash/8MB PSRAM','physical measurement pending;65x30x18 keepout','TBD','https://www.espressif.com/en/products/devkits',18,'allowance_not_quote','module/spec verified; seller must confirm v1.1 (RGB38)')
item('balance','6-axis IMU',1,'Adafruit 4438 / LSM6DSOX','I2C400k;INT1;416Hz initial','25.6x17.8x4.6',1.7,'https://www.adafruit.com/product/4438',11.95,'observed_list','buy bench module')
item('balance','dual H bridge',1,'Pololu 2130 DRV8833','2.7-10.8V;1.2A/ch module;modify sleep/current sense','20.3x17.8;headers additional','TBD',P+'2130',7.95,'allowance_verify_live','buy bench module; modifications required')
item('balance','motor-bus current sensor',1,'Adafruit 904 INA219 STEMMA QT','0.1ohm; signed shunt; not phase-current sensing','25.6x20.4x4.7','TBD','https://www.adafruit.com/product/904',9.95,'observed_list','buy module; mounting revision verify')
item('balance','encoder level shifting',1,'SN74LVC14AD + SOIC14 adapter','5V encoder to3.3V PCNT;5.5V tolerant Schmitt inputs','8.7x3.9 IC plus adapter','TBD','https://www.ti.com/product/SN74LVC14A',3,'allowance_not_quote','REQUIRED; no direct5V into ESP32')
item('balance','motor clamp brackets pair',1,'Pololu 2676 25D Bracket Pair','17mm M3 front mounting; bracket hole pattern per0J825','27x52x25 approx; drawing controls',17,P+'2676',10.95,'observed_list','bench only; hold custom mount')
item('balance','belt pulleys and belts set',1,'MORI-BELT-1to1 candidate 27T 2mm pitch 150mm belt','motor4mm bore / wheel6mm;6mm belt requires width revision','pitch diameter17.19; centre48.0; flange TBD','TBD','supplier drawing and quote required',18,'allowance_not_quote','HOLD exact manufacturer SKU/pitch/tension/width: current belt4mm reserve insufficient')
item('balance','two plain wheels',1,'MORI-W95-W18 custom pair Rev0','95mm tyre OD;18wide;independent6mm wheel axle; belt drive','95x18 each',130,'local print/machining + TPU tyre quote',15,'allowance_not_quote','HOLD model/tyre/hub interface; no finished SKU')
item('balance','wheel axle bearings',4,'NSK 686ZZ','shielded miniature deep-groove; nominal6x13x5','6 bore x13 OD x5 wide',2.69,'https://www.nsk.com/content/dam/nsk/am/pt_br/product/bearings-/ball-bearings/self--aligning-ball-bearings/guide.pdf',3,'allowance_not_quote','catalog envelope matches; buy via NSK authorized distributor; fit/preload NOT_TESTED, printed13.6 hole is not final fit')
item('interaction','round display',1,'Waveshare 19192 1.28inch LCD Module','GC9A01;240x240;active32.4mm;SPI','40.4x37.5;glass/thickness TBD',15,'https://www.waveshare.com/1.28inch-lcd-module.htm',14.99,'observed_list','bench only; FAIL active60mm target; requires revised opaque mask',False,'comparison only: DM-TFT24-432 2.4inch MIPI; incompatible direct S3 interface')
item('interaction','head yaw',1,'DFRobot SER0037 270deg PWM','4.8-6V;500-2500us;spec580/740mA stall;gear8:14','22.9x12.3x22.6 ears extra',11.2,'https://www.dfrobot.com/product-1106.html',7.90,'observed_list','buy one bench; HOLD ears/spline/calibration; lower spec torque used',False)
item('interaction','head bearing + cable relief',1,'NSK 6805ZZ candidate + custom retention','separate turntable;25x37x7 differs from24x36x6 reserve','25 bore x37 OD x7 wide','included in45g bearing/fastener allocation','https://www.oss.nsk.com/mea/calculation/calculate/index/sku/6805ZZ-APN/',10,'allowance_not_quote','HOLD: change shaft/housing diameters and axial stack +1mm; verify preload and head/body clearance before purchase',False)
item('power','logic buck',1,'Pololu 2831 D24V10F5','5V1A nominal;derate after thermal test','18x13x3.5','TBD',P+'2831',12.95,'observed_list','buy bench regulator')
item('power','servo buck',1,'Pololu 2858 D24V22F5','5V2.5A advertised depends Vin/thermal;allocate0.8A peak','TBD','TBD',P+'2858',18.95,'observed_list','buy bench regulator',False)
item('power','protected factory battery',1,'ANSMANN 2447-0105','2S1P Li-ion7.2V3.35Ah24.12Wh;5A max;BMS details pending','39x71x18 oriented to Blender',99,'https://www.reichelt.com/de/en/shop/product/lithium-ionen_akkupack_7_2_v_3350_mah_2s1p-414412',40,'USD_allowance_not_currency_conversion','HOLD:71mm>70 reservation; resize tray after review; manufacturer charge current/balance/regen/connector confirmation required')
item('power','external matched charger',1,'BatterySpace CH-L7412SM (product4208)','8.4VCCCV1.2A;5.5x2.1mm centre positive','88x52x30',139,'https://www.batteryspace.com/Smart-Charger-1.2A-for-7.4V-Li-ion/Polymer-Rechargeable-Battery-Pack.aspx',26.39,'observed_from_range_variant_verify','HOLD:8.4V/1.2A candidate ONLY, ANSMANN charge-current approval/matching/connector unconfirmed; no balance function assumed')
item('power','bus dump power resistor',1,'ARCOL HS25 5R6 J','5.6ohm5%;25W on specified heatsink;14.1W when ON at8.9V','manufacturer drawing pending',25,'https://www.te.com/en/products/passive-components/resistors/power-resistors.html',6,'allowance_not_quote','HOLD pulse/temperature/heat-spreader acceptance')
item('power','hardware watchdog + clamp parts',1,'CD74HC123E;SN74HC08N;LM393P;TL431BCLP;IRLZ44NPBF','see native schematic and carrier_bom.csv','DIP16/14/8;TO92;TO220','included in board allocation','TI / authorized local distributor',8,'allowance_not_quote','buy bench components; not validated circuit')
item('power','reverse protection/USB isolation/fuse',1,'AO4407A;SS34;0287003.PXCN;DC fuse holder','3A fuse;Q reverse;D logic diode OR','SO8/SMA/offboard holder','TBD','AOS/Littelfuse/authorized distributor',7,'allowance_not_quote','verify fuse holder/main switch exact DC ratings')
item('power','current-limit resistors',2,'Vishay WSL1206R3900FEA','0.39ohm1%;>=0.25W;Pololu sense cut links','3.2x1.6','TBD','authorized distributor',.6,'allowance_not_quote','buy; continuity and trip-current test required')
item('power','motor temperature probes',2,'Murata NCP18XH103F03RB on insulated wired tab','10k1%;B3380;no bare conductor touching motor case','0603 + insulated carrier','TBD','Murata/LCSC/Mouser',1.5,'allowance_not_quote','thermal contact and lag NOT_TESTED')
item('power','keyed connectors/wire/caps/passives',1,'JST SH/PH/XH/VH;AMASS XT30U;specified carrier passives','see wiring and carrier_bom;AWG20/22/28','per wiring','included in wire allocation','authorized distributor',18,'allowance_not_quote','verify supplied polarity; buy bench allowance')
item('one_time','hardware emergency stop fixture',1,'Schneider XB5AS8444 2NC','NC1 logic / NC2 servo5V; manually reachable','22mm panel hole;40mm mushroom;body drawing TBD','excluded from robot: external fixture','https://www.se.com/us/en/product/XB5AS8444/',25,'allowance_not_quote','buy fixture; on-robot disconnect integration HOLD')
item('one_time','solder board + carrier prototype + assembly',1,'MORI RevA 2-layer 1oz PROTOTYPE','unrouted; not orderable yet','96x92x1.6 clipped corners; four deck holes','board allocation','local PCB supplier quote required',25,'allowance_not_quote','HOLD PCB fabrication')
item('one_time','fall-protection fixture and weighed chassis',1,'MORI-BENCH-REV0','soft catches not touching during free balance; weighed ballast','TBD','fixture excluded','local fabrication',20,'allowance_not_quote','HOLD fixture geometry; assembly needed')
item('optional','speaker/amp/mic allowance',1,'MAX98357A breakout + I2S MEMS mic (SKU not selected)','I2S GPIOs presently unavailable; requires repin/resource review','TBD','TBD','not selected',15,'allowance_not_quote','HOLD; not in mandatory scope',False)
csvout('bom.csv',bom)
from collections import defaultdict
tot=defaultdict(float);minimum=0
for b in bom:
 cost=float(b['unit_price'])*int(b['quantity']);tot[b['group']]+=cost
 if b['minimal_balance_included']=='yes':minimum+=cost
full=sum(v for k,v in tot.items() if k!='optional')
(R/'reports/budget.json').write_text(json.dumps(dict(currency='USD',basis='mixture of observed US list prices and explicit planning allowances; NOT a user-approved budget',price_date='2026-09-21',shipping_tax_tools_excluded=True,group_totals=tot,minimal_balance_including_battery_charger_fixture=round(minimum,2),complete_robot_including_one_time=round(full,2),optional=tot['optional']),indent=2)+'\n')
print('Pinmap',len(rows),'wire rows',len(wire),'carrier parts',len(comps),'BOM items',len(bom),'budget',round(minimum,2),round(full,2))

"""Reviewed pin-number definitions for V1.2-P1. Values in mm; PCB +Y down.
TI pin maps verified in saved vendor PDFs. Never substitute similarly named ICs.
Module side headers follow WeAct 64Pin V1.1, not BlackPill V3.0.
"""
from pathlib import Path
import json

R0603='Resistor_SMD:R_0603_1608Metric'
C0603='Capacitor_SMD:C_0603_1608Metric'
VSSOP='Package_SO:VSSOP-8_2.3x2mm_P0.5mm'
SOT23='Package_TO_SOT_SMD:SOT-23'
GH=lambda n:f'Connector_JST:JST_GH_BM{n:02d}B-GHS-TBT_1x{n:02d}-1MP_P1.25mm_Vertical'
HEADER=lambda n:f'Connector_PinHeader_2.54mm:PinHeader_2x{n:02d}_P2.54mm_Vertical'

def pin(name,net,typ='passive'):return dict(name=name,net=net,type=typ)
def comp(ref,value,fp,nets,at,side='F',auto=False,note='',source=''):
    return dict(ref=ref,value=value,footprint=fp,pins={str(n):v if isinstance(v,dict) else pin(str(n),v) for n,v in nets.items()},at=at,side=side,auto=auto,note=note,source=source)
def passive(ref,val,net1,net2,at,side='B',auto=True,fp=None):
    return comp(ref,val,fp or (C0603 if ref[0]=='C' else R0603),{1:net1,2:net2},at,side,auto)
def conn(ref,val,nets,at,fp=None):return comp(ref,val,fp or GH(len(nets)),{i+1:n for i,n in enumerate(nets)},at,note='Pin numbers are PCB connector numbers; harness mating view must be continuity checked.')
def flags(cs,nets):
    for i,n in enumerate(nets,1):cs.append(comp('#FLG'+str(i),'External supply boundary (UNVALIDATED)','',{1:pin('Power source',n,'power_out')},[0,0,0],note='Represents an external supply boundary and its required qualification; not an ERC suppression.'))
def holes(cs,xy):
    for i,(x,y) in enumerate(xy,1):cs.append(comp('H'+str(i),'M2 clearance','MountingHole:MountingHole_2.2mm_M2',{},[x,y,0]))

def motion():
    # PCB module origin: original board (0,0) -> (6,34.11), rotated90deg.
    assigns={
      'PA9':('S288_TX','output'),'PA10':('S288_RX','input'),'PA2':('HEAD_TX','output'),'PA3':('HEAD_RX','input'),
      'PC6':('LINK_TX','output'),'PC7':('LINK_RX','input'),'PA5':('IMU_SCK_M','output'),'PA6':('IMU_MISO','input'),
      'PA7':('IMU_MOSI_M','output'),'PA4':('IMU_CS_M','output'),'PB0':('IMU_DRDY','input'),
      'PC0':('BAT_ADC','input'),'PC1':('WHEEL_ADC','input'),'PC2':('CURRENT_ADC','input'),
      'PB5':('S288_OE_REQ_N','output'),'PB6':('HEAD_OE_REQ_N','output'),'PB7':('ARM_CLK','output'),
      'PB8':('CLR_N','open_collector'),'PC4':('CHG_N','input'),'PC5':('ARM_FEEDBACK','input'),
      'PC13':('USER_KEY_N','input'),'PB3':('FAULT_N','input')}
    cs=[]
    p1=['VB','GND','PC14','PC13','PC0','PC15','PC2','PC1','PA0','PC3','PA2','PA1','PA4','PA3','PA6','PA5','PC4','PA7','PB0','PC5','PB2','PB1','PB11_NC_VCAP','PB10']
    p2=['PB9','GND','PB7','PB8','PB5','PB6','PB3','PB4','PC12','PD2','PC10','PC11','PA12','PA15','PA10','PA11','PA8','PA9','PC8','PC9','PC6','PC7','PB14','PB15']
    for ref,names,at in [('J101',p1,[7.37,32.74,90]),('J102',p2,[7.37,4.80,90])]:
        pins={}
        for i,n in enumerate(names,1):
            net,typ=assigns.get(n,('GND','power_in') if n=='GND' else (None,'passive'))
            pins[i]=pin(n,net,typ)
        cs.append(comp(ref,'WeAct-F412RET6-V1.1 '+('P1' if ref=='J101' else 'P2'),HEADER(12),pins,at,source='https://github.com/WeActStudio/WeActStudio.STM32F4_64Pin_CoreBoard'))
    cs.append(comp('J103','WeAct P3 3V3 / GND',HEADER(3),{i:pin('3V3' if i%2 else 'GND','+3V3' if i%2 else 'GND','power_out' if i==1 else 'passive') for i in range(1,7)},[37.85,32.74,90]))
    cs.append(comp('J104','WeAct P4 / 5V',HEADER(3),{1:pin('PB12',None),2:pin('PB13',None),3:pin('5V','+5V_MOTION','power_in'),4:pin('5V','+5V_MOTION'),5:pin('GND','GND'),6:pin('GND','GND')},[37.85,4.80,90]))
    # P5 only NRST is connected on carrier. SWD remains accessible on module top.
    dbg=['GND','GND','PA10','PA14_SWCLK','PA9','PA13_SWDIO','NRST','3V3']
    cs.append(comp('J105','WeAct P5 / NRST tap',HEADER(4),{i+1:pin(n,'NRST' if i==6 else None) for i,n in enumerate(dbg)},[32.39,19.28,0],note='P5.7 NRST tap; other carrier holes intentionally unwired. Debug probe plugs onto module TOP.'))
    # One purchased module is one physical assembly. All through-holes belong to
    # its complete footprint, not five colliding standalone header courtyards.
    module_pins={}; module_pads=[]
    import math
    for hc in cs:
        tag={'J101':'A','J102':'B','J103':'C','J104':'D','J105':'E'}[hc['ref']]
        ax,ay,angle=hc['at'];rad=math.radians(angle)
        for pn,pn_data in hc['pins'].items():
            i=int(pn)-1;lx=(i%2)*2.54;ly=(i//2)*2.54
            key=tag+pn;module_pins[key]=dict(pn_data,name=tag+'.'+pn+' '+pn_data['name'])
            x=ax+lx*math.cos(rad)+ly*math.sin(rad)-6
            y=ay-lx*math.sin(rad)+ly*math.cos(rad)-.89
            module_pads.append((key,x,y))
    custom=Path(__file__).resolve().parents[1]/'kicad/custom.pretty';custom.mkdir(parents=True,exist_ok=True)
    footprint='(footprint "WeAct_F4_64Pin_V11" (version 20241229) (generator "mori_v12") (layer "F.Cu") (attr through_hole)\n'
    footprint+='(fp_rect (start 0 0) (end 41.6 33.22) (stroke (width 0.1) (type default)) (fill none) (layer "F.Fab"))\n'
    footprint+='(fp_rect (start -0.25 -0.25) (end 41.85 33.47) (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))\n'
    for key,x,y in module_pads:
        footprint+=f'(pad "{key}" thru_hole {"rect" if key.endswith("1") and len(key)==2 else "circle"} (at {x:.4f} {y:.4f}) (size 1.7 1.7) (drill 1) (layers "*.Cu" "*.Mask"))\n'
    footprint+=')';(custom/'WeAct_F4_64Pin_V11.kicad_mod').write_text(footprint)
    cs=[comp('U100','WeAct STM32F412RET6 64Pin V1.1','MORI_Custom:WeAct_F4_64Pin_V11',module_pins,[6,.89,0],source='https://github.com/WeActStudio/WeActStudio.STM32F4_64Pin_CoreBoard',note='A=P1 B=P2 C=P3 D=P4 E=P5. Complete module footprint; manufacturer drawing, NOT measured. P5 SWD accessible from module top; E7 reset tap only.')]
    cs += [conn('J1' ,'MOTION 5V IN',['+5V_MOTION','GND'],[52,4,0]),
       conn('J2','S288 DATA ONLY',['S288_BUS','GND'],[64,4,0]),
       conn('J3','HEAD DATA ONLY',['HEAD_BUS','GND',None],[52,29,0]),
       conn('J4','BODY IMU SPI',['+3V3','GND','IMU_SCK','IMU_MOSI','IMU_MISO','IMU_CS','IMU_DRDY','GND'],[52,16,90]),
       conn('J5','CAM J11 MATCH',['CAM_RX','CAM_TX','CAM_3V3','GND'],[64,15,90],fp='Connector_JST:JST_SH_BM04B-SRSS-TB_1x04-1MP_P1.00mm_Vertical'),
       conn('J6','USER BUTTON',['USER_KEY_N','GND'],[64,25,0]),
       conn('J7','POWER CONTROL',['+3V3','ARM_Q','FAULT_N','CHG_N','BAT_ADC_IN','WHEEL_ADC_IN','CURRENT_ADC_IN','GND'],[61,32,0]),
       conn('J8','LATCHED ENABLE LOOP',['LOOP_3V3','CLR_N'],[46,26,90])]
    for connector in cs[1:]:
        connector['auto']=True
        if connector['ref'] in ['J6','J8']:connector['side']='B'
    # Local 3.3-V tri-state PHY. 1Y=6, 2Y=3: do NOT use a generic 125 pin order.
    for ref,prefix,at in [('U1','S288',[12,13,0]),('U2','HEAD',[22,13,0])]:
        cs.append(comp(ref,'SN74LVC2G125DCUR',VSSOP,{1:pin('1OE_N',prefix+'_OE_N','input'),2:pin('1A_TX',prefix+'_TX','input'),3:pin('2Y_RX',prefix+'_RX','tri_state'),4:pin('GND','GND','power_in'),5:pin('2A_BUS',prefix+'_BUS','input'),6:pin('1Y_TX',prefix+'_TX_BUF','tri_state'),7:pin('2OE_N','GND','input'),8:pin('VCC','+3V3','power_in')},at,'B',source='https://www.ti.com/lit/ds/symlink/sn74lvc2g125.pdf',note='Ioff; bus input 0..5.5V. External actuator VIH/VOH not yet verified. Default no transmission.'))
    cs.append(comp('U3','SN74LVC2G32DCUR',VSSOP,{1:pin('1A','S288_OE_REQ_N','input'),2:pin('1B','ARM_Q_N','input'),3:pin('2Y','HEAD_OE_N','output'),4:pin('GND','GND','power_in'),5:pin('2A','HEAD_OE_REQ_N','input'),6:pin('2B','ARM_Q_N','input'),7:pin('1Y','S288_OE_N','output'),8:pin('VCC','+3V3','power_in')},[17,21,0],'B',source='https://www.ti.com/lit/ds/symlink/sn74lvc2g32.pdf'))
    cs.append(comp('U4','TXU0202DCUR',VSSOP,{1:pin('B2','CAM_TX','input'),2:pin('GND','GND','power_in'),3:pin('VCCA','+3V3','power_in'),4:pin('A2Y','LINK_RX','output'),5:pin('A1','LINK_TX','input'),6:pin('OE','+3V3','input'),7:pin('VCCB','CAM_3V3','power_in'),8:pin('B1Y','CAM_RX_BUF','output')},[41,13,0],'B',source='https://www.ti.com/lit/ds/symlink/txu0202.pdf',note='VCC isolation and Ioff; J11.3 powers only translator B rail, never feeds motion regulator.'))
    cs.append(comp('U5','SN74LVC1G74DCUR',VSSOP,{1:pin('CLK','ARM_CLK','input'),2:pin('D','+3V3','input'),3:pin('Q_N','ARM_Q_N','output'),4:pin('GND','GND','power_in'),5:pin('Q','ARM_Q','output'),6:pin('CLR_N','CLR_N','input'),7:pin('PRE_N','+3V3','input'),8:pin('VCC','+3V3','power_in')},[25,22,0],'B',source='https://www.ti.com/lit/ds/symlink/sn74lvc1g74.pdf',note='Physical loop + supervisor + faults clear latch; only a new explicit ARM rising edge re-enables.'))
    cs.append(comp('U6','TLV803EA29DBZR',SOT23,{1:pin('GND','GND','power_in'),2:pin('RESET_N','CLR_N','open_collector'),3:pin('VDD','+3V3','power_in')},[9,23,0],'B',source='https://www.ti.com/lit/ds/symlink/tlv803e.pdf',note='2.93V threshold,200ms reset; exact non-R/non-V pinout.'))
    for ref,cath in [('D1','NRST'),('D2','FAULT_N'),('D3','CHG_N')]:
        cs.append(comp(ref,'BAT54H,115','Diode_SMD:D_SOD-123',{1:cath,2:'CLR_N'},[22,26,0],'B',True,note='Cathode pin1; pulls latch clear low, does not reset MCU on ordinary disable.'))
    rs=[('68','S288_TX_BUF','S288_BUS'),('68','HEAD_TX_BUF','HEAD_BUS'),('10k','S288_OE_REQ_N','+3V3'),('10k','HEAD_OE_REQ_N','+3V3'),
        ('10k','ARM_CLK','GND'),('1k','+3V3','LOOP_3V3'),('10k','CLR_N','GND'),('10k','USER_KEY_N','+3V3'),
        ('47','CAM_RX_BUF','CAM_RX'),('33','IMU_SCK_M','IMU_SCK'),('33','IMU_MOSI_M','IMU_MOSI'),('33','IMU_CS_M','IMU_CS'),
        ('10k','IMU_CS','+3V3'),('1k','BAT_ADC_IN','BAT_ADC'),('1k','WHEEL_ADC_IN','WHEEL_ADC'),('1k','CURRENT_ADC_IN','CURRENT_ADC'),
        ('10k','FAULT_N','+3V3'),('10k','CHG_N','+3V3'),('1k','ARM_Q','ARM_FEEDBACK')]
    cs.extend(passive('R'+str(i+1),v,a,b,[15+(i%6)*5,8+(i//6)*6,0]) for i,(v,a,b) in enumerate(rs))
    caps=[('+3V3','100n')]*6+[('CAM_3V3','100n'),('+5V_MOTION','10u'),('BAT_ADC','10n'),('WHEEL_ADC','10n'),('CURRENT_ADC','10n'),('CLR_N','100n')]
    cs.extend(passive('C'+str(i+1),v,n,'GND',[12+(i%6)*5,10+(i//6)*12,0]) for i,(n,v) in enumerate(caps))
    cap_targets=[[11,10.5,0],[21,10.5,0],[16,18.5,0],[40,10.5,0],[24,19.5,0],[8,21,0],[43,11,0],[52,4,0]]
    for c in cs:
        if c['ref'] in ['C'+str(i) for i in range(1,9)]:c['at']=cap_targets[int(c['ref'][1:])-1]
    flags(cs,['+5V_MOTION','GND','CAM_3V3'])
    # Two left holes are clear of the module, two right holes avoid signal connectors.
    holes(cs,[(2.5,2.5),(2.5,32.5),(67.5,2.5),(67.5,32.5)])
    return dict(size=[70,35],layers=2,clearance=.15,description='MORI motion carrier / WeAct STM32F412RET6 V1.1 adaptation / NO MOTOR CURRENT ON THIS PCB',components=cs,module_outlines=[[6,.89,47.6,34.11]],power_nets=['+5V_MOTION','+3V3'])

def imu():
    cs=[comp('U1','ICM-42688-P','Package_LGA:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y',{
      1:pin('SDO','MISO_IC','output'),2:pin('RESV','GND'),3:pin('RESV','GND'),4:pin('INT1','DRDY','output'),5:pin('VDDIO','+3V3','power_in'),6:pin('GND','GND','power_in'),7:pin('RESV','GND'),8:pin('VDD','+3V3','power_in'),9:pin('FSYNC','GND','input'),10:pin('RESV','GND'),11:pin('RESV','GND'),12:pin('CS_N','CS_N','input'),13:pin('SCLK','SCK','input'),14:pin('SDI','MOSI','input')},[10,9,0],source='https://www.lcsc.com/datasheet/C1850418.pdf',note='Prototype based on vendor DS-000347 pinout. No raw cell welding; IC requires reflow. Assembly pad review required.'),
      conn('J1','BODY RIGID IMU',['+3V3','GND','SCK','MOSI','MISO','CS_N','DRDY','GND'],[10,3.5,0]),
      passive('C1','100n','+3V3','GND',[13,8,0],'F'),passive('C2','2.2u','+3V3','GND',[14,11,0],'F'),passive('C3','10n','+3V3','GND',[8,11,0],'F'),
      passive('R1','33','MISO_IC','MISO',[6,8,0],'F'),passive('R2','10k','CS_N','+3V3',[6,12,0],'F')]
    holes(cs,[(2.5,12.5),(17.5,12.5)]);flags(cs,['+3V3','GND'])
    return dict(size=[20,16],layers=2,clearance=.15,description='MORI body IMU daughterboard / ICM-42688-P / SPI 6MHz initial target / rigid body mounting',components=cs,module_outlines=[])

def designs():
    from power_P1 import power
    return {'MORI_motion_P1':motion(),'MORI_imu_P1':imu(),'MORI_power_P1':power()}

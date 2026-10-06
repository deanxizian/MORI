"""Power conditioning prototype. External finished pack/charger/regulators are
explicit boundaries, not fictitious implemented charger circuitry.
"""
from design_P1 import comp,conn,pin,passive,flags,holes,GH,SOT23
SO8='Package_SO:SOIC-8_3.9x4.9mm_P1.27mm'
XT='Connector_AMASS:AMASS_XT30UPB-M_1x02_P5.0mm_Vertical'
XH='Connector_JST:JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical'
SMA='Diode_SMD:D_SMA';CP='Capacitor_THT:CP_Radial_D10.0mm_P5.00mm'
def power():
 cs=[]
 def xp(ref,label,positive,at,negative='GND'):
  cs.append(comp(ref,label,XT,{1:pin('MINUS',negative),2:pin('PLUS',positive)},at,note='AMASS XT30UPB-M PCB: pin1 minus, pin2 plus; mating housing polarization plus continuity check mandatory.'))
 xp('J1','PACK AFTER 6.3A FUSE / MASTER','BAT_IN',[7,7,0])
 xp('J2','WHEEL BUCK VIN','BAT_MON',[24,7,0]);xp('J3','WHEEL BUCK 9V RETURN','W9_IN',[44,7,0])
 xp('J4','HEAD BUCK VIN','BAT_MON',[10,38,0]);xp('J5','HEAD BUCK 6V RETURN','H6_IN',[24,39,0])
 xp('J6','LOGIC BUCKS VIN / FUSED HARNESS','BAT_MON',[44,39,0])
 xp('J11','WHEEL DUMP 5R6 EXTERNAL','W_VM',[66,7,0],negative='W_DUMP_D')
 xp('J12','HEAD DUMP 10R EXTERNAL','H_VM',[66,39,0],negative='H_DUMP_D')
 for ref,bus,at in [('J7','W',[12,20,0]),('J8','W',[26,20,0]),('J9','H',[12,30,0])]:
  cs.append(comp(ref,('S288 L' if ref=='J7' else 'S288 R' if ref=='J8' else 'SCS0009 CHAIN'),XH,{1:pin('GND','GND'),2:pin('V+',bus+'_VM'),3:pin('BUS',bus+'_BUS')},at,note='Board-side XH 3-pin interface only. SCS original 5264-3P uses 1GND/2VCC/3TTL. S288 factory mating plug remains unverified; adapter harness must be confirmed.'))
 cs += [conn('J10','MOTION CONTROL',['+3V3','ARM_Q','FAULT_N','CHG_N','BAT_ADC','WHEEL_ADC','CURRENT_ADC','GND'],[63,22,90]),
 conn('J13','S288 DATA',['W_BUS','GND'],[43,20,0]),conn('J14','HEAD DATA',['H_BUS','GND',None],[43,30,0]),
 conn('J15','CHARGE INTERLOCK',['CHG_N','GND'],[53,29,90]),
 conn('J16','CHARGER RAW VBUS SENSE',['VBUS_CHARGE','GND'],[76,26,90])]
 # Open J15 is NOT fail-safe. A normally-closed mechanical insertion contact
 # must short J15 in the plugged state, independently of charger firmware.
 def fet(ref,src,drain,gate,at):
  cs.append(comp(ref,'AO4407A',SO8,{1:src,2:src,3:src,4:gate,5:drain,6:drain,7:drain,8:drain},at,'B',source='https://www.aosmd.com/sites/default/files/res/datasheets/AO4407A.pdf'))
 fet('Q1','BAT_REV','BAT_IN','REV_GATE',[10,12,0])
 cs += [passive('R1','10k','REV_GATE','GND',[10,14,0]),
 comp('D1','BZT52H-C10,115','Diode_SMD:D_SOD-123F',{1:'BAT_REV',2:'REV_GATE'},[13,12,0],'B',True),
 passive('R2','WSL2512R0100FEA 10mR 1% 1W','BAT_REV','BAT_MON',[20,12,0],fp='Resistor_SMD:R_2512_6332Metric')]
 cs.append(comp('U1','INA180A1IDBVR','Package_TO_SOT_SMD:SOT-23-5',{1:pin('OUT','CURRENT_ADC','output'),2:pin('GND','GND','power_in'),3:pin('IN+','KELVIN_P','input'),4:pin('IN-','KELVIN_N','input'),5:pin('VS','+3V3','power_in')},[22,16,0],'B',source='https://www.ti.com/lit/ds/symlink/ina180.pdf',note='Kelvin sense of 10mR; gain20 =>0.2V/A. Discharge only; reverse current not measured.'))
 cs.extend([passive('R3','0','BAT_REV','KELVIN_P',[24.5,13.5,0]),passive('R4','0','BAT_MON','KELVIN_N',[16,13.5,0])])
 # Supply reverse blocking and hardware enable. Logic loss removes actuator power.
 for base,prefix,vin,at in [(10,'W','W9_IN',[45,11,0]),(30,'H','H6_IN',[25,34,0])]:
  cs.append(comp('D'+str(base),'B540C-13-F','Diode_SMD:D_SMC',{1:prefix+'_PRE',2:vin},at,'B',source='https://www.diodes.com/datasheet/download/B540C.pdf',note='Cathode pin1; B540C-13-F verified DS13012 Rev18-2. Board thermal and domestic quote unqualified.'))
  fet('Q'+str(base),prefix+'_PRE',prefix+'_VM',prefix+'_GATE',[at[0]+8,at[1],0])
  cs.append(comp('Q'+str(base+1),'AO3400A',SOT23,{1:'ARM_Q',2:'GND',3:prefix+'_GATE_LOW'},[at[0]+8,at[1]+6,0],'B',source='https://www.aosmd.com/sites/default/files/res/datasheets/AO3400A.pdf'))
  cs += [passive('R'+str(base),'10k',prefix+'_GATE',prefix+'_PRE',[at[0]+4,at[1]+4,0]),passive('R'+str(base+1),'100',prefix+'_GATE',prefix+'_GATE_LOW',[at[0]+10,at[1]+4,0])]
  cs.append(comp('C'+str(base),'Panasonic EEU-FR1C102 1000uF 16V',CP,{1:prefix+'_VM',2:'GND'},[at[0]+12,at[1]+7,0],note='D10 x H16; height is vendor capacitor envelope, NOT fitted into old10mm allocation.'))
 # Brakes run from each actual actuator rail, even after BMS/control disconnect.
 for base,prefix,at,top,ovtop in [(20,'W',[68,14,0],'33.2k','37.4k'),(40,'H',[68,32,0],'16.5k','18.7k')]:
  cs.append(comp('U'+str(base),'LM393BDR',SO8,{1:pin('OUT1',prefix+'_BRAKE_GATE','open_collector'),2:pin('IN1-',prefix+'_REF','input'),3:pin('IN1+',prefix+'_SENSE','input'),4:pin('GND','GND','power_in'),5:pin('IN2+',prefix+'_REF','input'),6:pin('IN2-',prefix+'_OVSENSE','input'),7:pin('OUT2','FAULT_N','open_collector'),8:pin('VCC',prefix+'_VM','power_in')},at,'B',source='https://www.ti.com/lit/ds/symlink/lm393b.pdf'))
  cs.append(comp('U'+str(base+1),'TL431BIDBZR',SOT23,{1:pin('K',prefix+'_REF'),2:pin('REF',prefix+'_REF','input'),3:pin('A','GND')},[at[0]-7,at[1],0],'B',source='https://www.ti.com/lit/ds/symlink/tl431.pdf',note='DBZ pin1 cathode,2 reference,3 anode. B grade +/-0.5% at25C; thermal error in tolerance model.'))
  cs.append(comp('Q'+str(base),'AO3400A',SOT23,{1:prefix+'_BRAKE_GATE',2:'GND',3:prefix+'_DUMP_D'},[at[0]+7,at[1],0],'B',source='https://www.aosmd.com/sites/default/files/res/datasheets/AO3400A.pdf'))
  cs.append(comp('D'+str(base),'BZT52H-C10,115','Diode_SMD:D_SOD-123F',{1:prefix+'_BRAKE_GATE',2:'GND'},[at[0]+7,at[1]+4,0],'B',True))
  rr=[('2.2k',prefix+'_VM',prefix+'_REF'),(top+' 0.1%',prefix+'_VM',prefix+'_SENSE'),('10k 0.1%',prefix+'_SENSE','GND'),('1M 0.1%',prefix+'_BRAKE_GATE',prefix+'_SENSE'),('2.2k',prefix+'_VM',prefix+'_BRAKE_GATE'),(ovtop+' 0.1%',prefix+'_VM',prefix+'_OVSENSE'),('10k 0.1%',prefix+'_OVSENSE','GND')]
  cs += [passive('R'+str(base+i),v,a,b,[at[0]-6+(i%4)*3,at[1]+4+(i//4)*3,0]) for i,(v,a,b) in enumerate(rr)]
  cs += [passive('C'+str(base),'100n',prefix+'_VM','GND',[at[0],at[1]-4,0]),passive('C'+str(base+1),'10n',prefix+'_OVSENSE','GND',[at[0]-5,at[1]-4,0])]
 # ADC dividers, passive charge detect, ARM pulldown. No false charger/BMS block.
 for base,net,out,at in [(50,'BAT_MON','BAT_ADC',[23,24,0]),(52,'W_VM','WHEEL_ADC',[30,24,0])]:
  cs.extend([passive('R'+str(base),'100k 0.1%',net,out,at),passive('R'+str(base+1),'27k 0.1%',out,'GND',[at[0],at[1]+3,0])])
 cs.extend([passive('R54','10k','ARM_Q','GND',[53,23,0]),passive('R55','47k','VBUS_CHARGE','CHG_BASE',[74,24,0]),passive('R56','100k','CHG_BASE','GND',[74,28,0]),passive('C1','100n','+3V3','GND',[25,16,0]),passive('C2','1u 25V','BAT_MON','GND',[27,12,0])])
 cs.append(comp('Q50','MMBT3904LT1G',SOT23,{1:pin('B','CHG_BASE','input'),2:pin('E','GND'),3:pin('C','CHG_N','open_collector')},[74,21,0],'B',note='SOT23 1B 2E 3C. Raw VBUS detect only; neither CC nor charging control.'))
 for c in cs:
  if c['ref'].startswith(('U','Q','D','C','R')):c['auto']=True
  if c['ref'] in ['R2','U1']:c['auto']=False
  if c['ref']=='Q1':c['pins']['1']=pin('SOURCE PROTECTED OUTPUT','BAT_REV','power_out')
  if c['ref'] in ['Q10','Q30']:c['pins']['5']=pin('DRAIN SWITCHED OUTPUT',c['pins']['5']['net'],'power_out')
 flags(cs,['+3V3','GND','BAT_IN','W9_IN','H6_IN'])
 holes(cs,[(2.5,2.5),(77.5,2.5),(2.5,42.5),(77.5,42.5)])
 return dict(size=[80,45],layers=2,clearance=.2,description='MORI POWER CONDITIONER P1 / external protected3S pack + qualified buck/charger boundaries / DOES NOT FIT OLD POWER ALLOCATION',components=cs,module_outlines=[],power_nets=['+3V3'],high_current_nets=['BAT_IN','BAT_REV','BAT_MON','W9_IN','W_PRE','W_VM','W_DUMP_D','H6_IN','H_PRE','H_VM','H_DUMP_D'])

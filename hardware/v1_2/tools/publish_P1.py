#!/usr/bin/env python3
"""Publish reviewed P1 hardware facts. Does not write mechanical/software-owned files."""
from pathlib import Path
import json,csv,copy,hashlib
R=Path(__file__).resolve().parents[3];H=R/'hardware/v1_2';REV='V1.2-H0.2-P1'
def read(p):return json.loads(p.read_text())
def put(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
cat=read(R/'contracts/components.json');elec=read(R/'contracts/electrical_interfaces.json');base=read(R/'config/project_baseline.json');mech=read(R/'contracts/mechanical_interfaces.json');sources=read(H/'sources/index.json')
cat['revision']=elec['revision']=sources['revision']=base['hardware_revision']=REV
cat['physical_tests']='NOT_TESTED';cat['engineering_revision_note']='P1 native CAD and offline analyses; no purchased hardware. Motor/display/camera unchanged; explicit F412 adaptation ADR.'
newsrc=[
 ('HW12-WEACT','WeAct 64Pin V1.1 original schematic/drawing/STEP','https://github.com/WeActStudio/WeActStudio.STM32F4_64Pin_CoreBoard','hardware/v1_2/sources/weact_f4/WeAct-STM32F4_64PIN-CoreBoard_V11 SchDoc.pdf','Exact F412RET6 populated variant and domestic price still to match.'),
 ('HW12-F412-RM','ST RM0402 Rev6','https://www.st.com/resource/en/reference_manual/rm0402-stm32f412-advanced-armbased-32bit-mcus-stmicroelectronics.pdf','hardware/v1_2/sources/weact_f4/RM0402 STM32F412 Reference manual.pdf','Clock table6 p60; DMA table30/31 p199 verified; runtime firmware not built here.'),
 ('HW12-F412-DS','ST DS11139 STM32F412xE/xG','https://www.st.com/resource/en/datasheet/stm32f412re.pdf','hardware/v1_2/sources/weact_f4/DS11139 STM32F412xE.pdf','512KB flash/256KB RAM for RET6; manufacturer source copy in WeAct repository.'),
 ('HW12-ICM','TDK DS000347 ICM42688P','https://www.lcsc.com/datasheet/C1850418.pdf',None,'Web cached vendor datasheet rev1.2 preproduction used for pins/land review; latest TDK download blocked. Latest silicon/datasheet reconciliation remains a gate.'),
 ('HW12-POL9','Pololu D36V50F9 #4094','https://www.pololu.com/product/4094',None,'9V module engineering reference; USD price is not CNY quote. China stock/price NOT_CONFIRMED.'),
 ('HW12-POL6','Pololu D24V22F6 #2859','https://www.pololu.com/product/2859',None,'6V reference. Thermal current depends voltage/cooling; China stock/price NOT_CONFIRMED.'),
 ('HW12-POL5','Pololu D24V22F5 #2858','https://www.pololu.com/product/2858',None,'Two independent5V converters proposed; no stock/price qualification.'),
 ('HW12-IP2326','Injoinic IP2326 v1.11','https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1132/IP2326.pdf','hardware/v1_2/sources/parts/IP2326.pdf','3S charging selectable via CON_SEL1k; built-in balance only2S. Reference chip, NOT a qualified finished module and NOT drawn as an implemented charger.'),
 ('HW12-PASSIVE','Yageo exact thin-film resistor series example','https://www.yageogroup.com/component-documentation/download/specsheet/RT0603BRD07100KL',None,'Other values selected using series ordering code, exact supplier match still required.'),
 ('HW12-CAP','Panasonic EEUFR1C102','https://industrial.panasonic.com/ww/products/pt/aluminum-cap-lead/models/EEUFR1C102',None,'1000uF16V, D10 H16 pitch5; vendor documented, NOT measured.'),
 ('HW12-DIODE','Diodes B540C-13-F DS13012 Rev18-2','https://www.diodes.com/datasheet/download/B540C.pdf',None,'Manufacturer PDF reviewed through web; direct local download403. SMC cathode band,0.55V at5A25C; board thermal rating unqualified.'),
 ('HW12-JST-SH','JST SH connector and contact','https://www.jst.com/wp-content/uploads/2021/01/eSH.pdf',None,'SH SSH-003T-P0.2-H28-32AWG; use30AWG signal leads.'),
 ('HW12-PCB','Native KiCad P1 source',None,'hardware/v1_2/tools/design_P1.py','Design-generated board outlines/holes, not vendor parts. No Gerber release.')]
for name in ['sn74lvc2g125','sn74lvc2g32','sn74lvc1g74','txu0202','tlv803e','lm393b','tl431','ina180']:
 newsrc.append(('HW12-TI-'+name,name+' TI datasheet','https://www.ti.com/lit/ds/symlink/'+name+'.pdf','hardware/v1_2/sources/parts/'+name+'.pdf','Pin mapping read from vendor document.'))
for name in ['ao4407a','ao3400a']:
 newsrc.append(('HW12-AOS-'+name,name+' AOS datasheet','https://www.aosmd.com/sites/default/files/res/datasheets/'+name.upper()+'.pdf','hardware/v1_2/sources/parts/'+name+'.pdf','Ratings are device conditions, not board thermal test.'))
for key in ['LCD35079_STEP','LCD35079_DRAWING','CAM33700_DRAWING']:
 s=mech['vendor_geometry_sources'][key];newsrc.append(('HW12-MECH-'+key,key,s.get('url'),s['path'],'Inherited latest mechanical source and its dimensional caveats; never overwrites mechanical truth.'))
ids={x['id'] for x in sources['sources']}
for i,t,u,p,n in newsrc:
 if i not in ids:sources['sources'].append(dict(id=i,title=t,url=u,local_path=p,access_date='2026-09-22',note=n));ids.add(i)
parts={p['id']:p for p in cat['components']}
previous_quotes={p['full_model']:copy.deepcopy(p) for p in cat['components'] if p.get('unit_price_cny') is not None}
parts['motion_mcu'].update(full_model='WeAct STM32F4 64Pin CoreBoard V1.1 / STM32F412RET6',board_revision='V1.1 2026-05-30; populated F412RET6 option',data_status='VENDOR_DOCUMENTED',dimensions_mm={'board_xy':[41.6,33.22],'populated_height':None,'includes_cable':False},mass_g=None,specification='5V board input; local3.3V; 512KB flash /256KB SRAM; HSE8MHz -> SYSCLK96MHz proposed',interface='USART1/2/6 + SPI1/EXTI0 + ADC1 + top SWD',purchase_channel='https://weactstudio.taobao.com/',purchase_option='64Pin V1.1 STM32F412RET6; not F411CEU6 BlackPill',selection_status='EXPLICIT_ADAPTATION_PROTOTYPE',source_ids=['HW12-WEACT','HW12-F412-RM','HW12-F412-DS'],missing=['\u56fd\u5185\u6240\u9009\u89c4\u683c\u62a5\u4ef7\u4e0e\u677f\u4fee\u8ba2','\u5b8c\u6574\u5806\u53e0\u9ad8\u5ea6/\u8d28\u91cf/\u63d2\u62d4\u7a7a\u95f4','\u5b9e\u7269\u65f6\u949f\u4e0e6Mbps\u7269\u7406\u94fe\u8def'],notes='ADR-HW-V1_2-002.md; pinout/DMA frozen for prototype; no motor or application-count change.')
parts['body_imu'].update(full_model='TDK ICM-42688-P / MORI_imu_P1 daughterboard',board_revision='P1',data_status='VENDOR_DOCUMENTED',dimensions_mm={'chip_xy':[2.5,3.0],'designed_board_xy':[20,16],'board_thickness':1.6,'installed_height':None},specification='3.3V VDD/VDDIO; SPI1 initial6MHz, ODR1000Hz/DRDY timestamp target',source_ids=['HW12-ICM','HW12-PCB'],mechanical_contract_keys=['body_imu'],selection_status='PROTOTYPE_DISCRETE_IMU_BOARD',missing=['\u6700\u65b0\u91cf\u4ea7\u624b\u518c/\u5c01\u88c5\u786e\u8ba4','\u56fd\u5185\u82af\u7247\u62a5\u4ef7\u4e0eSMT\u6253\u6837','\u8f74\u5411\u88c5\u914d\u786e\u8ba4\u4e0e\u6570\u636e\u5ef6\u8fdf\u5b9e\u6d4b'],notes='Bare LGA requires reflow/assembly service; no claim user can hand-solder it with current equipment.')
for cid,mkey in [('display','display'),('interaction_cam','cam_board')]:
 p=parts[cid];v=mech['components'][mkey];p['dimensions_mm']=copy.deepcopy(v['vendor_dimensions']);p['dimensions_mm']['mechanical_notes']=v['notes'];p['source_ids']+= [s for s in ['HW12-MECH-'+v['geometry_source_id']] if s not in p['source_ids']];p['data_status']='VENDOR_DOCUMENTED';p['mass_g']=None
parts['display']['missing']=['\u91c7\u8d2dRev1\u5bf9\u5e94/\u51c0\u91cd','STEP9.35\u4e0ePDF9.1ref\u5dee\u5f02\u3001\u5b54\u4f4d\u7ea60.06mm\u5dee\u5f02','\u6392\u7ebf\u63a5\u89e6\u9762/\u63d2\u62d4\u51c0\u7a7a\u4e0e16\u201318\u811a\u5b9a\u4e49','\u6240\u9009SKU\u56fd\u5185\u4ef7\u683c']
parts['interaction_cam']['missing']=['\u5b8c\u6574\u5b89\u88c5\u9ad8\u5ea6/\u5b54\u5f84/\u51c0\u91cd/\u8fde\u63a5\u5668\u9ea6\u514b\u98ce\u5929\u7ebf\u4f4d\u7f6e','DVP\u539f\u88c5\u6392\u7ebf\u957f\u5ea6/\u63a5\u89e6\u9762','\u5177\u4f53OV3660\u7248\u56fd\u5185\u4ef7\u683c','\u76f8\u673a+\u5c4f+\u97f3\u9891\u538b\u529b\u6d4b\u8bd5']
parts['head_servo']['ratings']={'at6V':{'rated_torque_Nm':.75*.0980665,'rated_current_A':.4,'stall_torque_Nm':2.3*.0980665,'stall_current_A':1.0,'no_load_current_A':.15},'at4p8V':{'rated_torque_Nm':.65*.0980665,'rated_current_A':.3,'stall_current_A':.8},'position_feedback':'carbon potentiometer in2020A/0;300deg/1024, current sold revision not matched','backlash_deg_documented_max':.5}
parts['head_servo']['missing']=['\u91c7\u8d2d\u4fee\u8ba2\u5339\u914d/\u7a0e\u8fd0\uff1b\u56fd\u5185103\u5143\u578b\u53f7\u62a5\u4ef7\u5df2\u6709','\u4fdd\u6301\u7535\u6d41/\u566a\u58f0/\u6e29\u5347\u53ca\u539f\u59cbA0\u8fde\u7eed\u989d\u5b9a\u7684\u9002\u7528\u7248\u672c','TTL\u9608\u503c/\u5bc4\u5b58\u5668\u4e0e\u96f6\u70b9\u5b9e\u6d4b']
parts['wheel_power'].update(full_model='Pololu D36V50F9 #4094 9V buck (engineering reference)',dimensions_mm={'xyz':[25.4,25.4,9.525]},mass_g=7,source_ids=['HW12-POL9'],selection_status='ENGINEERING_REFERENCE_CN_QUOTE_PENDING',specification='9V5A typical,9.9\u201350Vinput; actual curve/thermal limit required',notes='P1 adds B540C blocking, switched output and rail-powered brake on separate power PCB. Do not mistake D24V50F9 for a real selected part.')
parts['head_power'].update(full_model='Pololu D24V22F6 #2859',dimensions_mm={'xyz':[17.8,17.8,8]},mass_g=2.3,source_ids=['HW12-POL6'],selection_status='ENGINEERING_REFERENCE_CN_QUOTE_PENDING',specification='6V nominal; output after blocking diode estimated5.21\u20136.04V',notes='Use4.8V head rated torque for conservative check; not a6V guarantee at servo pins.')
parts['logic_power'].update(full_model='Pololu D24V22F5 #2858',quantity=2,dimensions_mm={'xyz':[17.8,17.8,8]},mass_g=2.3,source_ids=['HW12-POL5'],selection_status='ENGINEERING_REFERENCE_CN_QUOTE_PENDING',specification='5V; two separate regulated branches for motion and CAM',notes='Shared battery remains common cause. DMM/bench verification and branch fuse selection required.')
parts['carrier_pcb'].update(full_model='MORI_motion_P1 70x35 + MORI_imu_P1 20x16 + MORI_power_P1 80x45',quantity=1,quantity_unit='three-board prototype set',dimensions_mm={'motion_xy':[70,35],'imu_xy':[20,16],'power_xy':[80,45],'thickness':1.6},source_ids=['HW12-PCB'],selection_status='NATIVE_ROUTED_PROTOTYPE_NO_FAB_RELEASE',notes='FR4 prototype; motion/IMU1oz, power2oz proposed. Includes SMT setup quote in this line; assembly parts individually listed below. Power does not fit44x16 allocation.')
parts['usb_charge'].update(full_model='UNSELECTED finished3S USB-C CC/CV module',source_ids=['HW12-IP2326','HW12-SPEC'],notes='IP2326 reference reviewed: 3S charge supported, on-chip balancing only2S; no finished module qualified. No native charger falsely represented by power-conditioner PCB.',missing=['\u786e\u5207\u6a21\u5757\u578b\u53f7/\u4fee\u8ba2/\u539f\u7406\u56fe/\u5c3a\u5bf8','CC advertisement/input limit and ordinary5V behavior','3S voltage accuracy/current/NTC and pack balance','\u56fd\u5185\u62a5\u4ef7'])
parts['user_button'].update(full_model='C&K PTS645SL50SMTR92LFS candidate + printed cap',interface='normally-open dry contact to motion J6 /PC13; no MCU reset',selection_status='EXACT_ORDER_CODE_PENDING_VENDOR_MATCH',notes='Button mechanically outside PCB; existing WeAct user switch is test fallback, not exterior user control.')
parts['physical_disable'].update(full_model='NC maintained dry-contact inhibit loop + master DC switch + inline6.3A fuse; exact panel parts pending',interface='J8 open clears hardware latch; master interrupts battery; local button does not reset MCU',notes='Dry-contact inhibit loop carries<3mA, not motor current. Master switch requires >=15VDC/6A qualified rating. Exact user-accessible switch envelope remains a procurement gap.')
parts['lcd_cable'].update(full_model='Waveshare LCD35079 supplied FFC18P 0.5mm 200mm same-side contacts',dimensions_mm={'pitch':.5,'positions':18,'length':200},selection_status='VENDOR_PACKING_LIST; ASSEMBLY_DIRECTION_NOT_TESTED',notes='Included in display package if actual order confirms; not counted as free without quote. Reconcile CAM connector mating orientation by continuity before energizing.')
# Remove obsolete placeholders that would double-count implemented board parts.
remove={'s288_phy','scs_phy','link_protection','power_monitor','pcb_components'}
cat['components']=[p for p in cat['components'] if p['id'] not in remove and not p['id'].startswith('p1_') and p['id'] not in ['usb_adapter','usb_charge_cable']]
for extra_id, purpose in [('usb_adapter','External USB-C adapter matched to charger input profile'),('usb_charge_cable','USB-C charging cable matched to current/CC/PD profile')]:
 p=copy.deepcopy(parts['usb_charge']);p.update(id=extra_id,purpose=purpose,full_model='UNSELECTED: dependent on qualified3S charger',quantity=1,unit_price_cny=None,stock_status='UNKNOWN',selection_status='BLOCKED_CHARGER_SELECTION',notes='User owns no components; mandatory accessory cost retained as UNKNOWN, not zero.');cat['components'].append(p)
# Every on-board item is in a separate manufacturing/sub-BOM, with no invented price.
# Candidate passive MPNs preserve ordering-code verification as an explicit gate.
rval={'0':'RC0603JR070RL','10k':'RC0603FR0710KL','1k':'RC0603FR071KL','33':'RC0603FR0733RL','47':'RC0603FR0747RL','68':'RC0603FR0768RL','100':'RC0603FR07100RL','2.2k':'RC0603FR072K2L','47k':'RC0603FR0747KL','100k':'RC0603FR07100KL'}
prec={'100k':'RT0603BRD07100KL','27k':'RT0603BRD0727KL','33.2k':'RT0603BRD0733K2L','37.4k':'RT0603BRD0737K4L','10k':'RT0603BRD0710KL','1M':'RT0603BRD071ML','16.5k':'RT0603BRD0716K5L','18.7k':'RT0603BRD0718K7L'}
cap={'100n':'CL10B104KB8NNNC','10n':'CL10B103KB8NNNC','2.2u':'CL10A225KP8NNNC','10u':'CL10A106KP8NNNC','1u 25V':'CL10A105KA8NNNC'}
groups={};assembly=[];cad={}
for folder in sorted((H/'kicad').glob('MORI_*_P1')):
 d=read(folder/'connectivity.json');cad[folder.name]=d
 for c in d['components']:
  ref,val,fp=c['ref'],c['value'],c['footprint']
  if not fp or ref.startswith('H') or ref=='U100' or val=='ICM-42688-P':continue
  source=[];verification=('EXACT_IC_VENDOR_PINMAP; CN_QUOTE_PENDING' if c.get('source') else 'ORDER_CODE_AND_PINMAP_CANDIDATE_VERIFY_VENDOR');mpn=val
  if ref.startswith('R'):
   if 'WSL2512' in val:mpn='WSL2512R0100FEA';verification='VENDOR_SERIES; CN_QUOTE_PENDING'
   else:mpn=prec[val.split()[0]] if '0.1%' in val else rval[val];verification='ORDER_CODE_CANDIDATE_VERIFY_EXACT_DATASHEET';source=['HW12-PASSIVE']
  elif ref.startswith('C'):
   mpn='EEUFR1C102' if '1000uF' in val else cap[val];verification='VENDOR_DOCUMENTED' if mpn=='EEUFR1C102' else 'ORDER_CODE_CANDIDATE_VERIFY_EXACT_DATASHEET';source=['HW12-CAP'] if mpn=='EEUFR1C102' else []
  elif ref.startswith('J'):
   fn=fp.split(':')[1]
   if 'GH_' in fn:mpn=fn.split('GH_')[1].split('_1x')[0]+'(LF)(SN)'
   elif 'SH_' in fn:mpn='BM04B-SRSS-TB(LF)(SN)'
   elif 'XH_' in fn:mpn='B3B-XH-A(LF)(SN)'
   else:mpn='AMASS XT30UPB-M'
   verification='KICAD_LIBRARY_FOOTPRINT; MATCH_VENDOR_AND_MATE'
  for ss in sources['sources']:
   if c.get('source') and ss['url']==c['source']:source=[ss['id']]
  key=mpn+'|'+fp
  if key not in groups:groups[key]=dict(model=mpn,value=val,footprint=fp,quantity=0,references=[],verification=verification,source_ids=source)
  groups[key]['quantity']+=1;groups[key]['references'].append(folder.name+':'+ref)
  assembly.append(dict(revision=REV,board=folder.name,reference=ref,value=val,mpn=mpn,footprint=fp,side=c['side'],placed_mm=c.get('placed_at',c['at']),status=verification,unit_price_cny=None))
template=copy.deepcopy(parts['harness'])
for i,g in enumerate(groups.values(),1):
 p=copy.deepcopy(template);p.update(id='p1_'+str(i).zfill(3),category='pcb_part',purpose='P1\u88c5\u914d\uff1a'+', '.join(g['references']),quantity=g['quantity'],quantity_unit='piece',full_model=g['model'],board_revision='P1',specification=g['value'],interface=g['footprint'],source_ids=g['source_ids'] or ['HW12-PCB'],data_status='VENDOR_DOCUMENTED' if g['verification'].startswith(('EXACT_IC','VENDOR_DOCUMENTED')) else 'ASSUMED',dimensions_mm={'package_footprint':g['footprint']},mass_g=None,shaft_hole_interface=g['footprint'],connector_clearance_mm=None,mechanical_contract_keys=[],mounting_release=False,purchase_channel='\u7acb\u521b\u5546\u57ce/\u6dd8\u5b9d\u6388\u6743\u5e97\uff1b\u672a\u5f62\u6210\u6240\u9009SKU\u7ed3\u7b97\u8bc1\u636e',purchase_option=g['model'],unit_price_cny=None,quote_date=None,stock_status='UNKNOWN',confirmation_status='BLOCKED_QUOTE_AND_ASSEMBLY',selection_status=g['verification'],included_in=None,alternative_model=None,readaptation_requirement='\u5c01\u88c5/\u5f15\u811a/\u989d\u5b9a/\u516c\u5dee\u4e0d\u7b49\u540c\u5219\u91cd\u65b0\u9002\u914d',missing=['\u56fd\u5185\u7cbe\u786eMPN\u5c0f\u6279\u91cf\u4ef7\u683c\u3001\u5e93\u5b58\u3001\u7a0e\u8fd0','\u5019\u9009\u8ba2\u8d27\u7801\u4e0e\u5382\u5546\u6570\u636e\u9875\u9010\u4e00\u786e\u8ba4'] if 'CANDIDATE' in g['verification'] else ['\u56fd\u5185\u7cbe\u786eMPN\u5c0f\u6279\u91cf\u4ef7\u683c\u3001\u5e93\u5b58\u3001\u7a0e\u8fd0'],notes='Native schematic/PCB BOM cross-reference; not a quote and not purchased.')
 cat['components'].append(p)
# External brake resistors need pulse qualification and thermal clearance.
for idx,value,mpn in [('wheel','5.6ohm','AC05000005608JAC00'),('head','10ohm','AC05000001009JAC00')]:
 p=copy.deepcopy(template);p.update(id='p1_dump_'+idx,category='power',purpose=idx+'\u5236\u52a8\u5916\u7f6e\u529f\u7387\u7535\u963b',quantity=1,full_model='Vishay '+mpn+' candidate',specification=value+'5W; pulse energy NOT_QUALIFIED',source_ids=['HW12-PCB'],dimensions_mm=None,mass_g=None,selection_status='PULSE_CURVE_AND_CN_QUOTE_PENDING',notes='Do not substitute5W nameplate for20W wheel pulse capability. Heat isolation and mounting external to crowded PCB required.');cat['components'].append(p)
# Preserve matched prior quote fields; a populated price is not automatically qualified.
for p in cat['components']:
 old=previous_quotes.get(p['full_model'])
 if old:
  for field in ['unit_price_cny','quote_date','price_status','stock_status','purchase_channel','purchase_option','shipping_basis','currency','tax_included']:
   if field in old:p[field]=old[field]
# Motion pin truth from actual native symbol, without editing runtime firmware.
motion=cad['MORI_motion_P1'];u=next(c for c in motion['components'] if c['ref']=='U100');pins=[p for p in elec['pinmap'] if p['domain']!='motion']
periph={'PA9':'USART1_TX AF7 /DMA2 S7 C4','PA10':'USART1_RX AF7 /DMA2 S2 C4','PA2':'USART2_TX AF7 /DMA1 S6 C4','PA3':'USART2_RX AF7 /DMA1 S5 C4','PC6':'USART6_TX AF8 /DMA2 S6 C5','PC7':'USART6_RX AF8 /DMA2 S1 C5','PA5':'SPI1_SCK AF5','PA6':'SPI1_MISO AF5 /DMA2 S0 C3','PA7':'SPI1_MOSI AF5 /DMA2 S3 C3','PA4':'GPIO CS_N','PB0':'EXTI0 DRDY timestamp','PC0':'ADC1_IN10','PC1':'ADC1_IN11','PC2':'ADC1_IN12','PB8':'GPIO open drain clear latch'}
for key,p in u['pins'].items():
 gpio=p['name'].split()[-1]
 if not p['net'] or gpio in ['GND','3V3','5V','NRST']:continue
 pins.append(dict(revision=REV,domain='motion',net=p['net'],mcu_pin=gpio,peripheral=periph.get(gpio,'GPIO'),direction=p['type'],connector='WeAct '+{'A':'P1','B':'P2','C':'P3','D':'P4','E':'P5'}[key[0]],pin_number=int(key[1:]),carrier_pad='U100.'+key,logic_level='3.3V; external actuator VIH/VOH unqualified',source_ids=['HW12-WEACT','HW12-F412-DS','HW12-F412-RM'],assignment_status='P1_SCHEMATIC_ASSIGNED_NOT_BENCH_VERIFIED',boot_default='GPIO input except external pull states; NO ARM',bench_status='NOT_TESTED',notes='No TF/USB pin reuse. PB3 requires JTAG disabled while preserving SWD; PB8 open-drain only.'))
for p in pins:p['revision']=REV
elec['pinmap']=pins;elec['status']='PROTOTYPE_ROUTED_UNVALIDATED';elec['route']['motion']=parts['motion_mcu']['full_model'];elec['route']['body_imu']='MORI_imu_P1 /ICM-42688-P'
elec['bus_interfaces']['s288'].update(transceiver_model='SN74LVC2G125DCUR + SN74LVC2G32DCUR hardware OE mask',UART_candidate='USART1 PA9/PA10 AF7',candidate_clock_status='DOCUMENT_REVIEWED_NOT_BENCH_VERIFIED',default_state='TX high impedance; ARM latch cleared by supervisor/NRST/physical loop/fault/charge',interface_release='USART TC (not DMA transfer complete) then OE release; echo discard and bounded turnaround; measured timing required')
elec['bus_interfaces']['head']['transceiver_model']='separate SN74LVC2G125DCUR;1Mbps USART2'
elec['bus_interfaces']['motion_interaction'].update(baud=1000000,format='8N1',physical='TXU0202DCUR dual-rail/Ioff translator; shared signal GND; motion3.3V sideA, CAMJ11.3 sideB; NO power-rail tie')
elec['clock_and_dma']={'MCU':'STM32F412RET6','HSE_Hz':8000000,'PLL_M':8,'PLL_N':192,'PLL_P':2,'PLL_Q':4,'SYSCLK_Hz':96000000,'AHB_div':1,'APB1_div':2,'APB2_div':1,'USART1_BRR':16,'USART2_BRR':48,'USART6_BRR':96,'oversampling':16,'FLASH_wait_states':3,'VOS_bits':'11 scale1','USB_48MHz':True,'DMA_allocations':periph,'status':'DOCUMENT_AND_HOST_ARITHMETIC; firmware/clock measurement NOT_TESTED','references':['HW12-F412-RM table6 p60 andtable30/31 p199','HW12-WEACT crystal8MHz']}
elec['resource_review'].update(ADC_current_measurement='INA180A1+10mohm,0.2V/A DISCHARGE ONLY,PC2ADC12; no charge current',user_button_gpio='PC13 via J6 normally open dry contact')
elec['safety'].update(physical_disable='J8 normally closed maintained loop; open clears SN74LVC1G74. Power Q10/Q30 and both TX OE require latched ARM_Q. No automatic recovery after fault.',low_battery='provisional10.8V warning/10.2V urgent support, with filtering; require pack/dropout bench calibration. Not BMS-cutoff balancing.',IWDG='Motion firmware must enable independent watchdog; external supervisor is voltage/reset latch, not a software liveness monitor.')
elec['power_domains']=[dict(id='BAT_3S',nominal_V=11.1,max_V=12.6,status='CHEMISTRY_REQUIREMENT_PACK_UNSELECTED',note='Factory finished pack, matching balance/protection/NTC; these numbers are design requirements, not a selected battery rating'),dict(id='WHEEL9V',target_V=9,estimated_motor_range_V=[8.09,9.16],status='P1_CONDITIONER_NOT_TESTED',note='Pololu9V reference ->B540C ->ARM PMOS ->bulk+rail-powered brake; OV fault11.67..11.99V static only'),dict(id='HEAD6V',target_V=6,estimated_motor_range_V=[5.21,6.04],status='P1_CONDITIONER_NOT_TESTED',note='Independent6V buck/block/switch/dump; use4.8V rated torque conservatively'),dict(id='MOTION5V',target_V=5,status='SEPARATE_BUCK_REFERENCE_UNQUALIFIED',note='WeAct onboard3.3V; not motor source'),dict(id='CAM5V',target_V=5,status='SEPARATE_BUCK_REFERENCE_UNQUALIFIED',note='regulated5V only through qualified CAM USB pigtail; disconnect robot supply before host USB service'),dict(id='CAM3V3',target_V=3.3,status='ONBOARD',note='J11.3 onlytranslatorVCCB; never parallel regulators')]
elec['shared_battery_note']='Separate regulated branches and fault latch reduce specific failures; shared battery/ground/fuse still common cause; not independent safety redundancy.'
elec['charging'].update(ordinary_5V_behavior='UNQUALIFIED: do not attach battery until exact3S module/input limit/CC behavior validated',CCCV_module=None,CAM_USB_backfeed='Maintenance procedure: support/DISARM, disconnect CAM regulated5V pigtail before host USB; never connect both power sources; CAM BAT unused',charge_with_logic_enabled='DISALLOWED in P1 until a qualified power-path charger is selected',P1_power_board_is_charger=False)
elec['display_ffc'].update(cable_pitch_mm=.5,cable_length_mm=200,contact_orientation='LCD vendor supplied cable SAME-SIDE; CAM mating orientation and end-to-end continuity NOT_TESTED',matching_status='SIGNALS_DOCUMENTED; RESERVED_PINS_AND_PHYSICAL_CONTINUITY_PENDING')
# Current power/connector-to-pin map is generated from routed design connectivity.
harness=[]
for bn,d in cad.items():
 for c in d['components']:
  if not c['ref'].startswith('J'):continue
  harness.append(dict(revision=REV,id=bn+':'+c['ref'],from_=bn+'.'+c['ref'],to='See harness endpoint table in engineering_review.md',nets=[dict(pin=p,signal=x['net']) for p,x in c['pins'].items()],connector=c['footprint'],length_mm=None,wire_gauge=('20AWG XT30; final DC rating/polarity qualified' if 'XT30' in c['footprint'] else '22AWG XH branch; SXH-001T-P0.6; branch current qualification required' if 'XH_' in c['footprint'] else '30AWG SH; SSH-003T-P0.2-H' if 'SH_' in c['footprint'] else '28AWG GH; SSHL-002T-P0.2'),rated_current_A=None,view_direction='PCB component-side view (F top/B bottom); physical pad numbers in assembly SVG. Mating harness view is mirrored, check pin-to-pin continuity.',status='PROTOTYPE; MATE_AND_RATING_PENDING',notes=c.get('note','')))
elec['harness']=harness;elec['pcb_projects']={n:{'path':'hardware/v1_2/kicad/'+n,'dimensions_mm':d['size'],'status':'PROTOTYPE / NOT_TESTED','fabrication_release':False} for n,d in cad.items()};elec['engineering_review']='hardware/v1_2/reviews/engineering_review.md'
for x in [elec,cat]:x['procurement_release']=False
cat['manufacturing_release']=False;elec['manufacturing_outputs_allowed']=elec['pcb_release']=elec['hardware_freeze']=False
put(R/'contracts/components.json',cat);put(R/'contracts/electrical_interfaces.json',elec);put(R/'config/project_baseline.json',base);put(H/'sources/index.json',sources)
put(H/'reports/assembly_parts.json',dict(revision=REV,parts=assembly))
with (H/'assembly_parts.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(assembly[0]));w.writeheader();w.writerows(assembly)
# Hardware-owned mechanical change request, not an edit to mechanical allocation.
boards={}
for n,d in cad.items():
 boards[n]={'outline_xy_mm':d['size'],'board_thickness_mm':1.6,'outline_status':'DESIGN_GENERATED','holes':[{'id':c['ref'],'xy_mm':c['at'][:2],'diameter_mm':2.2} for c in d['components'] if c['ref'].startswith('H')],'connectors':[{'ref':c['ref'],'position_rotation_mm_deg':c.get('placed_at',c['at']),'side':c['side'],'footprint':c['footprint'],'mating_height_and_clearance_mm':None} for c in d['components'] if c['ref'].startswith('J')],'installed_envelope_height_mm':None,'mass_g':None,'STEP':'hardware/v1_2/mechanical/'+n+'_BARE_BOARD.step','STEP_scope':'bare board only; not a certified populated assembly'}
put(H/'handoff/mechanical_P1.json',dict(revision=REV,mechanical_revision_read=mech['revision'],mechanical_sha256=hashlib.sha256((R/'contracts/mechanical_interfaces.json').read_bytes()).hexdigest(),coordinates='PCB +X right +Y down; F component side +Z. Robot transformation requires mechanical owner approval.',boards=boards,power_conflict={'existing_allocation':[44,16,10],'power_conditioner_board':[80,45,1.6],'largest_documented_capacitor':[10,10,16],'additional_external_modules':['9V25.4x25.4x9.525','6V17.8x17.8x8','two5V17.8x17.8x8','charger/battery/dump resistors/mating leads unknown'],'status':'BLOCKED_RELAYOUT_REQUIRED'},motion_height='70x35 outline fits allocation; stack and bottom-facing J6/J8 mating clearance NOT_VERIFIED; no complete fit PASS',body_IMU='20x16 board fits allocation footprint; JSTGH mating plug likely exceeds5mm total reserve; measure/revise',owned_files_not_modified=['config/geometry.json','contracts/mechanical_interfaces.json','contracts/wire.h','contracts/wire.c']))
print(REV,len(cat['components']),'BOM lines',len(pins),'pins',len(harness),'board connectors')

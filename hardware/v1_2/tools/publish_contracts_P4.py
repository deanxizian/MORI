"""Publish P4 hardware-owned contracts from native pin maps and prior sourced BOM.

Preserve mechanical and firmware files; preserve the pre-P4 contracts separately.
No price, stock, physical dimension or test result is invented.
"""
from pathlib import Path
from collections import defaultdict
import json, csv, re, copy, hashlib
H=Path(__file__).resolve().parents[1];ROOT=H.parents[1];O=H/'layout_P4'
REV='V1.2-H0.4-P4';DATE='2026-09-23';BAK=H/'revisions/before_P4_contracts'
load=lambda p:json.loads(p.read_text())
dump=lambda p,x:p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def write_csv(p,rows):
 keys=list(dict.fromkeys(k for row in rows for k in row))
 with p.open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,keys);w.writeheader()
  for row in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in row.items()})
verification=load(O/'reports/verification.json')
assert all(v['status']=='PASS' for v in verification['native_checks'].values())
assert not verification['P3R1_changed_files']
components=load(BAK/'components.json');electrical=load(BAK/'electrical_interfaces.json')
old=components['components'];old_by_id={c['id']:c for c in old}
catalog={c['mpn']:c for c in load(O/'connector_catalog.json')}
native={kind:load(H/'kicad'/f'MORI_{kind}_P4'/'connectivity.json') for kind in ['motion','imu','power','rear']}
native_by={kind:{c['ref']:c for c in d['components']} for kind,d in native.items()}
parts=[];prior_ref={};prior_mpn={}
for c in old:
 prior_mpn[c['full_model']]=c
 for kind,ref in re.findall(r'MORI_(motion|imu|power)_(?:P\d|S3)[:/]([A-Z]+\d+)',c.get('purpose','')+' '+str(c.get('schematic_references',[]))):prior_ref[kind,ref]=c
aliases={'100k':'RC0603FR07100KL','10k':'RC0603FR0710KL'}
explicit={('power','Q90'):'AO4407A',('power','R90'):'RC0603FR07100KL',('power','R91'):'RC0603FR0710KL',('power','D90'):'BZT52H-C10,115',
 ('rear','USB1'):'TYPE-C-31-M-12',('rear','SW1'):'MS-202V-G3',('rear','F1'):'045101.5MRL',('rear','D1'):'SMF24A',('rear','D2'):'PESD5V0L1BA,115',('rear','D3'):'PESD5V0L1BA,115',('rear','C1'):'GRM188R71H104KA93D'}
covered={('motion','U100'):'motion_mcu',('imu','U1'):'body_imu',('power','U60'):'logic_power',('power','U70'):'logic_power',('rear','SW1'):'physical_disable'}
assembly=[];groups=defaultdict(list)
for kind,d in native.items():
 for c in d['components']:
  ref=c['ref'];fp=c.get('footprint','')
  if not fp or ref.startswith(('H','TP')):continue
  if (kind,ref) in covered:
   assembly.append(dict(board=f'MORI_{kind}_P4',ref=ref,full_model=old_by_id[covered[kind,ref]]['full_model'] if ref!='SW1' else 'MS-202V-G3',quantity=1,main_bom_id=covered[kind,ref],footprint=fp,physical_tests='NOT_TESTED'));continue
  m=re.search(r'PH_B(\d)B',fp)
  if m:mpn=f'B{m[1]}B-PH-K-S(LF)(SN)'
  elif 'PH_S5B' in fp:mpn='S5B-PH-K-S(LF)(SN)'
  elif 'XT30' in fp:mpn='AMASS XT30UPB-M'
  elif 'JST_XH_B3B' in fp:mpn='B3B-XH-A(LF)(SN)'
  elif 'JST_XH_B2B' in fp:mpn='B2B-XH-A(LF)(SN)'
  elif (kind,ref) in explicit:mpn=explicit[kind,ref]
  elif (kind,ref) in prior_ref:mpn=prior_ref[kind,ref]['full_model']
  else:raise AssertionError(('BOM mapping missing',kind,ref,c['value']))
  dnp=bool(c.get('dnp',False)) or (kind=='power' and ref=='J6')
  row=dict(board=f'MORI_{kind}_P4',ref=ref,full_model=mpn,quantity=0 if dnp else 1,DNP=dnp,value=c['value'],footprint=fp,source=c.get('source',''),physical_tests='NOT_TESTED')
  assembly.append(row)
  if not dnp:groups[mpn].append(row)
template=copy.deepcopy(old_by_id['p1_002'])
for i,(mpn,refs) in enumerate(sorted(groups.items()),1):
 c=copy.deepcopy(prior_mpn.get(mpn,template));c.update(id=f'p4_{i:03}',category='pcb_part',full_model=mpn,quantity=len(refs),quantity_unit='piece',board_revision='P4',purpose='P4 PCB装配：'+', '.join(v['board']+':'+v['ref'] for v in refs),specification='; '.join(sorted({v['value'] for v in refs})),interface='; '.join(sorted({v['footprint'] for v in refs})),source_date=DATE,schematic_references=[v['board']+':'+v['ref'] for v in refs],included_in=None)
 if mpn not in prior_mpn:
  c.update(unit_price_cny=None,quote_date=None,stock_quantity=None,stock_status='NOT_LIVE_CONFIRMED',purchase_option=mpn,data_status='ASSUMED',source_ids=['HW12-P4'],source_urls=sorted({r['source'] for r in refs if r['source']}),source_local_paths=[],dimensions_mm=None,shaft_hole_interface=c['interface'],missing=['国内精确SKU结算报价与库存','实物/装配及电气验证'],confirmation_status='BLOCKED_QUOTE_AND_ASSEMBLY',selection_status='PROTOTYPE_SELECTED_NOT_PURCHASED',notes='P4原生工程对应的器件；不能视为整机已核价。')
 if mpn in catalog:
  q=catalog[mpn];c.update(purchase_channel=q.get('domestic_url') or '立创商城目录 '+q['lcsc_code'],purchase_option=q['lcsc_code']+' / '+mpn,data_status='VENDOR_DOCUMENTED',dimensions_mm=dict(bare_xyz=q['bare_xyz_mm'],mated_height=q.get('mated_height_mm'),mated_depth=q.get('mated_depth_mm'),wire_bend=None),source_urls=[q['source']],source_ids=['HW12-P4-CONNECTORS'],confirmation_status='CN_CATALOG_FOUND_QUOTE_PENDING',notes='厂商尺寸与国内目录料号已记录；库存、价格、线束和安装间隙未实测。')
 parts.append(c)
 for a in assembly:
  if a['full_model']==mpn and a.get('quantity'):a['main_bom_id']=c['id']
base=[copy.deepcopy(c) for c in old if c['category']!='pcb_part']
by={c['id']:c for c in base}
by['body_imu'].update(full_model='TDK ICM-42688-P / MORI_imu_P4 daughterboard',board_revision='P4',schematic_references=['MORI_imu_P4:U1'])
by['body_imu']['notes']='本行只计ICM芯片；PCB、无源器件及贴装另列，不把整个子板与散件重复计价。LGA需回流服务，现有万用表/限流电源不是贴装设备。'
by['motion_mcu']['schematic_references']=['MORI_motion_P4:U100']
by['logic_power'].update(board_revision='P4 routed prototype; S3 buck circuit retained',schematic_references=['MORI_power_P4:U60','MORI_power_P4:U70'])
by['user_button'].update(quantity=0,selection_status='NOT_APPLICABLE',confirmation_status='NOT_APPLICABLE',purpose='已移除的外部功能按钮（保留历史条目）',notes='M1.11明确移除独立外壳按钮；运动J6仅保留机内PC13维护输入，非RESET。未额外购买C&K按钮。')
by['physical_disable'].update(full_model='SOFNG MS-202V-G3',board_revision='P4',quantity_unit='piece',purpose='后接口板双刀物理电源/禁驱开关',specification='0.5A/30VDC catalog rating; low-current contacts only',interface='rear SW1; pole A controls power Q90 via10k, pole B opens motion J8 latch-clear loop',schematic_references=['MORI_rear_P4:SW1'],purchase_channel='https://item.szlcsc.com/44278924.html',purchase_option='C42378287 / MS-202V-G3',dimensions_mm={'body_xyz':[9.1,3.5,3.5],'stem_mm':3,'travel_mm':2,'installed_envelope':'See hardware/v1_2/handoff/mechanical_P4.json'},data_status='VENDOR_DOCUMENTED',unit_price_cny=None,quote_date=None,source_ids=['HW12-P4-CONNECTORS'],missing=['样品万用表确认双刀状态/本地编号','国内结算报价','操作机构/外壳适配','Q90浪涌/SOA/温升'],notes='主电流通过电源板Q90/Q1；小开关不承载电机电流。OFF会失去平衡；托架使用。故障恢复不得自动ARM。',confirmation_status='CN_CATALOG_FOUND_QUOTE_PENDING')
by['carrier_pcb'].update(full_model='MORI_motion_P4 + MORI_imu_P4 + MORI_power_P4 + MORI_rear_P4',board_revision='P4',quantity_unit='four-board prototype set',specification='motion70x35 four-layer; IMU20x16, power80x55, rear24x25 two-layer; all1.6mm; power70um nominal, others35um; supplier stack-up/quote unconfirmed',notes='含四块板的一次基础打样额度，非报价；LGA与细脚器件装配服务须计价。原生检查PASS不等于制造释放。',missing=['四板打样/贴装/铜厚的国内报价','完整机械插合包络','实机验证'])
by['usb_charge']['notes']='后部P4仅提供USB-C、CC/ESD/保险和开关接口；外部3S充电/PD/温度/电源路径模块仍未选定，不能据接口PCB称充电完整。'
by['harness']['notes']='按P4逐针线束表制作；线长及弯曲待机械交接。PH配对壳/端子单列，线材、XT30/XH对端、工厂转接及压接加工仍包含在本项，未免除费用。'
geometry=load(ROOT/'config/geometry.json');wi=geometry['wheel_interface']
by['tyres'].update(full_model=f"Ø{geometry['wheel_diameter_mm']}×{geometry['wheel_width_mm']}轮胎/胎圈（机械要求，具体商品未选）",data_status='ASSUMED',dimensions_mm={'mechanical_requirement_diameter':geometry['wheel_diameter_mm'],'mechanical_requirement_width':geometry['wheel_width_mm'],'vendor_envelope':None},notes='以当前config/geometry.json为机械尺寸来源；不是已核商品尺寸。不得采购旧Ø95胎后缩放硬件模型。')
by['wheel_bearings'].update(full_model='686ZZ candidate; exact manufacturer/order suffix pending',quantity=4,data_status='ASSUMED',dimensions_mm={'mechanical_required_ID_OD_width':[wi['bearing_id_mm'],wi['bearing_od_mm'],wi['bearing_width_mm']],'selected_vendor_confirmed':False},specification='M1.14/M1.15 wheel interface requires two686ZZ per wheel,6x13x5mm',notes='替换旧4ID/10OD/4W占位要求；机械方案是尺寸需求，非本次实物/供应商确认。')
by['wheel_couplers'].update(full_model='M1.14 custom metal flanged shaft / double-D hub interface, candidate',notes='继承当前mechanical wheel_interface设计；两根定制钢轴/隔套及接口报价未取得，不是现成已购件。加工、公差、输出小孔螺钉、同轴度、强度与载荷试验尚未通过。')
components['mechanical_requirements_source']=dict(path='config/geometry.json',revision=geometry['revision'],sha256=hashlib.sha256((ROOT/'config/geometry.json').read_bytes()).hexdigest(),status='DESIGN_REQUIREMENTS_ONLY_NOT_PURCHASED_DIMENSIONS')
extra=copy.deepcopy(template);extra.update(id='p4_external_master_fuse',category='power',purpose='电池线束串联总保险与绝缘保险座',quantity=1,quantity_unit='set',full_model='6.3A DC inline fuse + holder; exact part UNSELECTED',board_revision='external harness',specification='DC voltage/interrupt rating and time-current curve must match finished3S pack;6.3A is design target, not a selected rating',interface='finished protected pack positive -> fuse -> power J1.2',purchase_option=None,purchase_channel=None,unit_price_cny=None,dimensions_mm=None,schematic_references=['MORI_power_P4:J1'],missing=['精确DC保险及座型号、曲线、尺寸','成品电池短路与放电额定','国内报价'],notes='从旧physical_disable组合拆出，不能随开关更新漏掉此必需件。')
parts.append(extra)
for id,purpose,model,note in [
 ('p4_assembly_service','四板首台装配/回流及必要钢网辅料','Qualified small-batch double-sided PCBA service; quote pending','含IMU LGA和电源细脚元件；若板厂报价已含钢网/辅料则合并，不重复计价。工具与人工的排除口径不等于免费商业贴装。'),
 ('p4_motion_module_sockets','WeAct模块与载板可拆插接件','WeAct V1.1 matching socket/header set; exact MPN/stack height UNSELECTED','按实际P1/P2/P3/P4孔阵列确认；P5维护/NRST方式分别核对。不能假定模块已附合适排母或拿未知插合高度证明机械适配。')]:
 c=copy.deepcopy(template);c.update(id=id,category='assembly',purpose=purpose,quantity=1,quantity_unit='set',full_model=model,board_revision='P4',specification=purpose,interface='P4 native assembly + vendor module drawing',purchase_option=None,purchase_channel=None,unit_price_cny=None,quote_date=None,dimensions_mm=None,source_ids=['HW12-P4'],missing=['精确报价与所含项目','实际装配/插合与检验'],notes=note);parts.append(c)
# Minimum PH cable halves provisioned for populated board headers; no free harness.
ph=defaultdict(int)
for c in parts:
 if re.match(r'[BS]\dB-PH',c['full_model']):ph[int(re.search(r'\d',c['full_model'])[0])]+=c['quantity']
for n,qty in sorted(ph.items()):
 c=copy.deepcopy(template);c.update(id=f'p4_phr_{n}',category='harness_part',purpose=f'P4 PH{n}板座配对线端壳体',full_model=f'PHR-{n}',quantity=qty,board_revision='P4 harness',specification='JST PH2.0 mating housing',interface=f'SPH-002T-P0.5S contacts; see exact cable table',purchase_option=f'PHR-{n}',unit_price_cny=None,quote_date=None,dimensions_mm=None,source_ids=['HW12-P4-CONNECTORS'],missing=['国内精确SKU/结算价','插合/锁扣与线缆路径'],notes='按已装板座每座一只线端壳的备料量；维护/NC接口可依实际装配清单少装，不能无说明计零。');parts.append(c)
c=copy.deepcopy(template);c.update(id='p4_ph_contacts',category='harness_part',purpose='PH线端压接端子备料',full_model='SPH-002T-P0.5S',quantity=sum(n*q for n,q in ph.items()),board_revision='P4 harness',specification='JST PH crimp contact; wire/insulation per manufacturer',interface='PHR-2/3/4/5/8',purchase_option='SPH-002T-P0.5S',unit_price_cny=None,quote_date=None,dimensions_mm=None,source_ids=['HW12-P4-CONNECTORS'],missing=['国内精确SKU/价格','线规/压接/拉力验证'],notes='按所有预留孔位的端子数备料，包含未用孔；损耗另核，不保证压接一次成功。');parts.append(c)
components.update(revision=REV,date=DATE,status='PROTOTYPE_ROUTED_UNVALIDATED',components=base+parts,additional_source_index='hardware/v1_2/layout_P4/connector_sources.json',assembly_cross_reference='hardware/v1_2/layout_P4/assembly_parts_with_mpn.csv',engineering_revision_note='P4 common PH2.0 connectors, revised routes, four boards incl rear interface and Q90 master cutoff. No GPIO reassignment; no fabrication or bench qualification.')
components['excluded_duplicate_purchases'] += ['P4 assembly U100/ICM/U60/U70/SW1 are counted under motion_mcu/body_imu/logic_power/physical_disable; do not add them again from the assembly cross-reference.','Power J6 RAW BAT SERVICE is DNP; no old external5V module attached. PH cable housings/contacts are separately counted; remaining harness work still charged.']
components['pcb_routing_style_review']=dict(status='FAIL',scope='User routing requirements; the previous same-side body classification did not verify path smoothness, shortest topology, placement alternatives or outward escape.',report='hardware/v1_2/layout_P4/user_review_20260923/review.json',visual_acceptance='FAIL',source_R14='FAIL: exact bend setback not fully applied',physical_tests='NOT_TESTED',reason='P4 rejected in the user-marked review. Native ERC/DRC and file-consistency PASS must never promote this field to PASS.')
components['budget']['full_total_cny']=None;components['budget']['compliance']='BLOCKED'

# Preserve every MCU assignment; change board revisions and physical connector facts.
pinmap=copy.deepcopy(electrical['pinmap'])
for row in pinmap:
 row['revision']=REV
 for key in ['connector','carrier_pad','notes']:
  if isinstance(row.get(key),str):row[key]=re.sub(r'MORI_(motion|imu|power)_P[123]',r'MORI_\1_P4',row[key])
 if row.get('net')=='USER_KEY_N' or row.get('mcu_pin')=='PC13':row['notes']='P4 J6机内维护干接点输入；外部功能按钮已按M1.11移除。非RESET；GPIO保持PC13。'
 row['bench_status']='NOT_TESTED'
def end(kind,ref,pin):
 c=native_by[kind][ref];p=c['pins'][str(pin)]
 return dict(board=f'MORI_{kind}_P4',connector=ref,pin=str(pin),signal=p['net'],footprint=c['footprint'])
harness=[]
def wire(id,a,z,gauge,note=''):
 harness.append(dict(revision=REV,harness_id=id,from_=a,to=z,wire_gauge=gauge,length_mm=None,pin_view='Native PCB pad numbers, component-side F/B as connector_pinmap.csv; mating wire view is mirrored',notes=note,physical_tests='NOT_TESTED'))
for ident,a,ar,z,zr,n in [('H01','power','J17','motion','J1',2),('H02','motion','J2','power','J13',2),('H03','motion','J3','power','J14',2),('H04','motion','J4','imu','J1',8),('H05','motion','J7','power','J10',8)]:
 for pin in range(1,n+1):wire(ident,end(a,ar,pin),end(z,zr,pin),'AWG24' if ident=='H01' else 'AWG26-28, qualified PH crimp','H03 pin3 NC: no terminal fitted' if ident=='H03' else '')
for pin in range(1,5):wire('H06',end('motion','J5',pin),dict(board='Waveshare33700',connector='J11',pin=str(pin),signal=['CAM_RX','CAM_TX','CAM_3V3','GND'][pin-1],family='factory SH1.0, exact mating verify'),'PH end AWG28; factory SH tail per terminal rating','PH4 to factory SH4 adapter; same pin numbers, RX/TX names referenced to CAM; do not cross twice. CAM3V3 is translator reference, never tied to motion3V3.')
for a,z in [(1,1),(2,2)]:wire('H07',end('rear','J3',a),end('power','J19',z),'AWG26-28','MASTER_RETURN can be at battery potential while OFF; never plug into logic port.')
for a,z in [(3,1),(4,2)]:wire('H07',end('rear','J3',a),end('motion','J8',z),'AWG26-28','Same rear PH4 branches into two labeled PH2 plugs. Not a straight4-pin cable.')
for pin,role in [(1,'VBUS input after rear fuse'),(2,'GND'),(3,'CC1; sink supplies Rd'),(4,'CC2; sink supplies Rd')]:wire('H08',end('rear','J2',pin),dict(board='EXTERNAL_PD_CHARGER_UNSELECTED',connector=None,pin=None,signal=role),'AWG24 VBUS/GND; AWG26-28 CC','Exact module terminal mapping BLOCKED until selected; no duplicated local Rd.')
wire('H08',end('rear','J2',5),end('power','J16',1),'AWG26-28','VBUS_RAW presence sense only, not charge current.')
wire('H08',end('rear','J2',2),end('power','J16',2),'AWG24 common ground; branch AWG26-28','Harness Y branch, verify crimp/splice rating; do not put two wires in unapproved contact.')
for ref,role in [('J1','finished3S protected pack after6.3A external fuse'),('J2','9V buck INPUT'),('J3','9V buck OUTPUT'),('J4','6V buck INPUT'),('J5','6V buck OUTPUT'),('J7','leftS288'),('J8','rightS288'),('J9','SCS0009 chain'),('J11','external5R6 braking resistor'),('J12','external10R braking resistor'),('J18','CAM regulated5V USB power pigtail')]:
 for pin,pn in native_by['power'][ref]['pins'].items():wire('P_'+ref,end('power',ref,pin),dict(board=role,connector='factory end / exact mating qualification pending',pin=None,signal=pn['net']),'AWG20 XT30; AWG22 XH, per exact terminal','J11/J12 pin1 is switched drain, NOT GND. Peripheral pin numbers are not inferred; verify factory cable before energizing.')
for pin in [1,2]:wire('I01',end('power','J15',pin),dict(board='maintenance cradle interlock / optional additional contact',connector=None,pin=None,signal=['CHG_N','GND'][pin-1]),'AWG26-28','Dry contact closes to inhibit; not MCU reset; broken open loop is not self-diagnosing. Primary USB presence path remains J16/Q50.')
write_csv(H/'interfaces'/f'harness_{REV}.csv',harness)
dump(O/'harness.json',harness)
electrical['historical_pcb_projects'].update(electrical['pcb_projects'])
handoff=load(H/'handoff/mechanical_P4.json')
electrical.update(revision=REV,status='PROTOTYPE_ROUTED_UNVALIDATED',pinmap=pinmap,harness=harness,pcb_projects={},active_schematics={},hardware_schematic_revision=REV,gpio_change=False,engineering_review='hardware/v1_2/layout_P4/README.md',mechanical_handoff='hardware/v1_2/handoff/mechanical_P4.json',schematic_validation='hardware/v1_2/layout_P4/reports/verification.json',layout_validation='hardware/v1_2/layout_P4/reports/verification.json',pcb_routing_style_review=components['pcb_routing_style_review'],pcb_revision_relationship=dict(existing='P4',synchronized=True,reason='PH replacements preserve signal pin assignments; power adds Q90 switch and rear interface. P3/P3R1 retained.'),connector_pinmap='hardware/v1_2/layout_P4/connector_pinmap.csv')
for kind in native:
 name=f'MORI_{kind}_P4';b=handoff['boards'][name]
 electrical['pcb_projects'][name]=dict(path=f'hardware/v1_2/kicad/{name}',dimensions_mm=b['outline_mm'],board_thickness_mm=1.6,layers=b['copper_layers'],copper_nominal_um=b['copper_nominal_um'],status='PROTOTYPE',native_checks=verification['native_checks'][kind],fabrication_release=False,physical_tests='NOT_TESTED')
 electrical['active_schematics'][kind]=f'hardware/v1_2/kicad/{name}/{name}.kicad_sch'
electrical['route']['body_imu']='MORI_imu_P4 / ICM-42688-P'
electrical['safety']['physical_disable']='Rear SW1 two poles: poleA pulls Q90 gate via10k to control pack load; poleB opens motionJ8 latch clear. Off/reset/fault requires explicit fresh ARM after passed checks; no automatic re-arm. Switch contacts carry only control current. OFF removes balance; cradle required.'
electrical['resource_review']['user_button_gpio']='PC13 on internal J6 only; independent exterior button removed by M1.11. No exterior RESET.'
electrical['charging'].update(rear_board='MORI_rear_P4; interface/protection only, not a charger',rear_pinmap='hardware/v1_2/layout_P4/connector_pinmap.csv',rear_design_continuous_input_A=1,series_fuse_A=1.5,external_input_limit_required=True,PD_controller=None,CC_termination='External qualified sink must provide independent CC1/CC2 Rd incl dead-battery startup; none on rear board',master_off_charging='Charger must connect to exact finished-pack approved charge terminals before Q90; P-/C- roles unresolved. No battery hookup until selected.',qualification='BLOCKED')
electrical['logic_power_startup']['sequence']='Rear SW1 enables Q90 input. TPS54302 EN internal pullups start both independent5V rails; MCU-local3V3 retained. ARM_Q not required for logic rails. Sequence/inrush tests NOT_TESTED.'
dump(ROOT/'contracts/components.json',components);dump(ROOT/'contracts/electrical_interfaces.json',electrical)
write_csv(ROOT/'hardware/pinmap.csv',pinmap);write_csv(H/'interfaces'/f'pinmap_{REV}.csv',pinmap)
write_csv(O/'assembly_parts_with_mpn.csv',assembly)
assembly_table=[]
for a in assembly:
 kind=a['board'].split('_')[1];c=native_by[kind][a['ref']]
 assembly_table.append(dict(revision=REV,board=a['board'],reference=a['ref'],value=c['value'],mpn=a['full_model'],footprint=c['footprint'],side=c.get('side'),placed_mm=c.get('placed_at',c.get('at')),status='DNP' if a.get('DNP') else 'PROTOTYPE_NOT_TESTED',unit_price_cny=None,main_bom_id=a.get('main_bom_id')))
if not (BAK/'assembly_parts.csv').exists() and (H/'assembly_parts.csv').exists():
 (BAK/'assembly_parts.csv').write_bytes((H/'assembly_parts.csv').read_bytes())
write_csv(H/'assembly_parts.csv',assembly_table)
rows=[]
for c in components['components']:
 row=dict(revision=REV,**c)
 price=c.get('unit_price_cny');row['subtotal_cny']=None if price is None else price*c['quantity']
 row['price_status']='NOT_APPLICABLE' if c['quantity']==0 else 'UNCONFIRMED' if price is None else 'PRIOR_RECORDED_QUOTE_RECHECK_REQUIRED'
 rows.append(row)
write_csv(H/'bom.csv',rows);write_csv(H/f'bom_{REV}.csv',rows)
write_csv(ROOT/'hardware/bom.csv',rows);write_csv(ROOT/'hardware/harness.csv',harness)
gate_path=H/'reports/budget_gate.json'
if not (BAK/'budget_gate.json').exists():(BAK/'budget_gate.json').write_bytes(gate_path.read_bytes())
gate=load(BAK/'budget_gate.json');required=[c for c in components['components'] if c['quantity']>0];priced=[c for c in required if c.get('unit_price_cny') is not None]
gate.update(revision=REV,required_lines=len(required),published_model_quote_lines=len(priced),exact_quoted_lines=0,unknown_price_ids=[c['id'] for c in required if c.get('unit_price_cny') is None],published_model_quote_subtotal_cny=sum(c['quantity']*c['unit_price_cny'] for c in priced),full_landed_total_cny=None,over_cap_cny=None,remaining_cap_cny=None,status='BLOCKED',physical_tests='NOT_TESTED')
dump(gate_path,gate);dump(O/'reports/budget_gate.json',gate)
dump(O/'reports/contract_publication.json',dict(revision=REV,component_rows=len(rows),assembly_rows=len(assembly),harness_conductors=len(harness),MCU_pin_assignments_changed=False,mechanical_owned_files_modified=False,physical_tests='NOT_TESTED',total_cny=None,quotation_status='BLOCKED',removed_old_active_GH_SH_parts=True))
print('Published',REV,len(rows),'BOM rows;',len(assembly),'PCB placements;',len(harness),'harness conductors')

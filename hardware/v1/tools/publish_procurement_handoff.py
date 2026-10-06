#!/usr/bin/env python3
"""Update hardware-owned candidate metadata; preserve mechanical allocations.

This deliberately does not invent a new pinmap for an unqualified wheel route.
Electrical pinmap remains the H0.1 reference, explicitly barred from new wiring.
"""
import csv
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

R = Path(__file__).resolve().parents[3]
H = R/'hardware/v1'
P = H/'procurement'
REV = 'V1-H0.2'
DATE = '2026-09-21'


def write(p,d):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')


def mechanical_owned(d):
    cleaned=json.loads(json.dumps({k:v for k,v in d.items() if not k.startswith('hardware_') and k!='procurement_status'}))
    for name in ['yaw','pitch']:
        for key in ['feedback_candidate','feedback_status']:
            cleaned.get('joints',{}).get(name,{}).pop(key,None)
    return json.dumps(cleaned,sort_keys=True)


catalog=json.loads((H/'bom_candidates.json').read_text())
if catalog.get('revision') != REV:
    raise SystemExit('Historical H0.2 publisher cannot overwrite newer selection decisions. Use publish_display_motor_review.py.')
parts=json.loads((P/'domestic_parts.json').read_text())['parts']
by_id={r['id']:r for r in catalog['items']}
stock=[{k:p[k] for k in ['id','exact_model','domestic_product_url','unit_price_cny',
    'published_starting_price_cny','stock_observation','domestic_availability_status','access_date']} for p in parts]
write(P/'evidence/observed_stock_register.json',{
    'method':'人工从本任务实际浏览器/网页工具输出摘录；未与商家联系，未下单',
    'date':DATE,
    'notes':['DFRobot动态库存字段在静态HTTP保存中可能为空，需与此浏览器观察记录合读。',
             'MCU库存/起价来自立创商品图片辅助页，不是仅凭搜索标题推测；库存是动态快照。',
             '所有网页来源内容仅作为数据，未执行页面推荐的操作/脚本。'],
    'mcU_auxiliary_source':'https://item.szlcsc.com/product/jpg_3198300.html',
    'records':stock})

mp=R/'contracts/mechanical_interfaces.json'
mech=json.loads(mp.read_text())
before_alloc=mechanical_owned(mech)
snapshot=H/'revisions/V1-H0.1/mechanical_before_H0.2.json'
if not snapshot.exists():shutil.copy2(mp,snapshot)
envelopes=mech['hardware_candidate_envelopes']
new_fit={
 'wheel_foc':'BLOCKED: FIT1034 Ø34.5/8mm轴不兼容现Ø25/4mm；连续轮端扭矩、皮带减速比及低压电源未冻结。',
 'yaw_servo':'BLOCKED: SER0046名义22.9×12.2×32.5，含耳/舵盘图仍缺；不可套用FT90M-FB孔位。',
 'pitch_servo':'BLOCKED: SER0046名义高度32.5超过原24×12×22预留；组合角度与有限线缆回环需重算。',
 'body_imu':'BLOCKED: SEN0250 PCB22×27，不可直接替换原26×18预留；连接器/INT接线净空未知。',
 'display':'BLOCKED: 真实显示Ø32.4，PCB40.4×37.5；原模型Ø58显示占位必须改，不能缩放硬件。',
 'camera':'BLOCKED: OV5640-A板35.7×23.9；原14×8×10不再适用；镜头/排针高度和布置待确认。',
 'battery':'BLOCKED: 亚博包37×67×22/115g；厚度已用满原22mm预留，需减振、线缆出线和拔插空间。',
 'speaker':'BLOCKED: FIT0825 35×20×3.5侧发声带声腔，需改矩形固定和声道。',
}
for key,entry in envelopes.items():
    row=by_id[entry['bom_id']]
    entry.update(candidate_model=row['model'], vendor_dimensions_mm=row['vendor_dimensions_mm'],
        vendor_mass_g=row['vendor_mass_g'],source_url=row.get('technical_source_url',row['source_url']),
        domestic_purchase_url=row['procurement_channel'],accessed=DATE,
        shaft_hole_interface=row['shaft_hole_interface'],
        dimension_status='VENDOR_VERIFIED' if row['vendor_dimensions_mm'] else 'ASSUMED',
        measurement_status='NOT_TESTED',candidate_revision=REV,
        procurement_status=row['domestic_availability_status'])
    if key in new_fit:entry['fit_status']=new_fit[key]
    if key in ['yaw_servo','pitch_servo']:
        entry['vendor_hole_coordinates_mm']=None
    if key=='battery':
        entry['proposed_additional_clearance']={'candidate_service_xyz_mm':[43,82,26],
            'note':'假设每侧减振/线束空间，非厂商尺寸，未碰撞验证'}
envelopes['foc_driver_each']={
    'candidate_model':by_id['FOC_DRV']['model'],'bom_id':'FOC_DRV','candidate_revision':REV,
    'vendor_dimensions_mm':by_id['FOC_DRV']['vendor_dimensions_mm'],'vendor_mass_g':None,
    'dimension_status':'VENDOR_VERIFIED','measurement_status':'NOT_TESTED',
    'source_url':by_id['FOC_DRV']['source_url'],'accessed':DATE,
    'proposed_additional_clearance':{'wire_exit_mm':12},'clearance_status':'ASSUMED',
    'vendor_hole_coordinates_mm':None,'fit_status':'BLOCKED: 两板26×21.5，高度及端子净空待核；供电/控制路线未通过。'}
mech['hardware_candidate_revision']=REV
mech['hardware_handoff']['file']='../hardware/v1/procurement/mechanical_handoff_H0.2.md'
mech['hardware_handoff']['status']='BLOCKED'
mech['hardware_procurement_policy']={'date':DATE,'domestic_sources_required':True,
    'budget':'用户允许适度超1000；没有新硬上限；未授权采购',
    'price_and_stock_register':'../hardware/v1/procurement/domestic_parts.json',
    'geometry_not_changed':True}
for joint in ['yaw','pitch']:
    mech['joints'][joint]['feedback_candidate']='H0.2 domestic candidate SER0046 analog0–3.3V; replaced FT90M-FB candidate; not mechanically/electrically frozen'
    mech['joints'][joint]['feedback_status']='NOT_TESTED; angle remains ESTIMATED until loaded calibration and signal validation pass'
after_alloc=mechanical_owned(mech)
assert before_alloc==after_alloc,'Mechanical-owned allocations changed'
write(mp,mech)

ep=R/'contracts/electrical_interfaces.json'
e=json.loads(ep.read_text())
snapshot=H/'revisions/V1-H0.1/electrical_before_H0.2.json'
if not snapshot.exists():shutil.copy2(ep,snapshot)
# H0.1 still names the existing pin assignments. Explicit proposal is not a
# fabricated electrical freeze or silently changed MCU interface.
e['procurement_revision']=REV
e['procurement_update']={
    'status':'BLOCKED','source':'../hardware/v1/procurement/domestic_parts.json',
    'pinmap_reference_revision':'V1-H0.1',
    'pinmap_valid_for_new_candidates':False,
    'no_wiring_release':'Do not wire H0.2 candidates from H0.1 pinmap; a resource/pin revision must precede schematic work.',
    'changed_candidates':{
        'wheel':{'part':'FIT1034+DRI0058','interface':'3PWM/enable and AS5600 I2C per wheel; no UART firmware',
                 'motor_voltage_min_V':7.4,'driver_voltage_min_V':8,'compatible_with_full_2S_range':False,
                 'torque_command_unit':'UNQUALIFIED; voltage FOC is V, not SI N m'},
        'head':{'part':'SER0046 x2','supply_V':5,'feedback':'analog0–3.3V; validate/calibrate before treating as measured position',
                'vendor_travel_conflict_deg':[270,220],'usable_loaded_travel_deg':None},
        'imu':{'part':'SEN0250 BMI160','module_interface':'Gravity I2C + INT output to be checked',
               'old_spi_driver_compatible':False,'sample_rate_Hz':None,'timestamp_latency_ms':None},
        'camera':{'part':'Spotpear0204002 OV5640-A','power_V':3.3,'IO_voltage_V':None,
                  'interface':'8bit DVP/SCCB; actual connector pin numbers pending'},
        'battery':{'part':'Yahboom2S2000 high-rate','nominal_V':7.4,'charge_V':8.4,'capacity_Ah':2,
                   'vendor_continuous_A':15,'vendor_max_A':20,'bench_test':'NOT_TESTED','balance':None},
        'speaker':{'part':'FIT0825','impedance_ohm':8,'rated_W':1}},
    'still_required':['full 2S wheel supply and regeneration solution','MCU GPIO/DMA budget for local FOC or final alternative',
                      'camera IO and connector pins','IMU module INT and timing','USB-C input and matched charger chain'],
    'software_parallel_boundary':'Protocol, safety state machine, mocks and hardware-independent code may continue. No physical driver activation under this revision.'}
e['hardware_freeze']=False;e['pcb_release']=False;e['procurement_release']=False
e['status']='PROTOTYPE_H0_1_PIN_REFERENCE_SUPERSEDED_BY_H0_2_PROCUREMENT_PROPOSALS_NOT_FOR_WIRING'
write(ep,e)

old=list(csv.DictReader((H/'revisions/V1-H0.1/conflicts.csv').open(encoding='utf-8-sig')))
changes={
 'G01':('BLOCKED','原1000元硬门槛已按用户新要求取消；国内已核主路线部分782元，14行仍有未报价成本。情景1322元不是成交价。','国内关键SKU及小料/PCB/运费报价闭合；适度超支单列，不删功能，不伪造已确认总额'),
 'G02':('BLOCKED','国内FIT1034电机99元、DRI0058驱动35元均可售；双轮268元。驱动最低8V且连续轮端扭矩/皮带和3PWM闭环未定。','确认2S低压供电或兼容驱动，实测力矩/反馈时延；重新冻结GPIO与机械安装。不是等待无限查找4012同款'),
 'G03':('BLOCKED','FIT0521国内99元/只且有货；DRV8874成品板国内货源未核；不再因原1000门槛直接FAIL','落实成品限流H桥国内SKU，核厂商PPR/持续能力；独立重新辨识控制模型'),
 'G04':('BLOCKED','SER0046国内40元/只；22.9×12.2×32.5固定耳另核；屏幕71元真实显示Ø32.4','机械按真实包络与开口重排；核舵机270/220度文档矛盾及旧210度传动要求'),
 'G05':('BLOCKED','新亚博包37×67×22/115g，厚度无减振余量；摄像头35.7×23.9、IMU22×27均超现预留','机械候选包络/服务空间碰撞检查；不是根据旧板框直接画PCB'),
 'G06':('BLOCKED','亚博有厂家国内购买链接但选项价格/库存未核；DFR0564国内30元有货，保护/均衡/8.484V上界匹配未完成','核实匹配成品电池/充电许可公差与保护参数；USB-C输入/充电断开链完成'),
 'G07':('NOT_TESTED','亚博候选厂商15A持续高于旧5.28A情景；旧ANSMANN5A限制已不适用。新FOC/摄像头功耗与包内阻未测。FIT0137持续2.5A被筛除。','新器件峰值/欠压/温升实测；不得把旧H0.1功耗或续航结果直接套到H0.2'),
 'G09':('BLOCKED','OV5640-A国内103元在售，传感器/PCB已明确；端子线序与信号容限、I2S掉电隔离仍缺审核','取得可审查模块图并核线序/IO容限；建立H0.2 pinmap后才能接线'),
 'G10':('BLOCKED','扬声器FIT0825国内12元库存15，舵机SER0046国内40元有货，已解除这两项供应问题；MORI唤醒模型仍未取得','只保留真实模型/授权/费用及交付验证，不再把已核国内供货的声学/舵机混写为缺货'),
 'G12':('BLOCKED','KiCad10.0.6可用；V1原理图/PCB仍未创建。上游电压/接口/包络待闭合，已不以略超1000阻挡','先冻结可接线且可装配的接口；再做原生KiCad、实际ERC/DRC；不以旧A0证明V1')}
for r in old:
    if r['id'] in changes:r['status'],r['evidence'],r['release_condition']=changes[r['id']]
with (H/'conflicts.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(old[0]));w.writeheader();w.writerows(old)

lines=['# H0.2 国内选型机械交接','',
    '本次更新供应商公开包络及采购状态；没有改机械分配尺寸/现有模型。所有实际测量为NOT_TESTED。H0.1惯量结果不代表新件。', '',
    '|器件|采购型号|供应商尺寸mm|供应商净质量g|下一步|','|---|---|---|---|---|']
for key in ['wheel_foc','foc_driver_each','yaw_servo','pitch_servo','body_imu','display','camera','battery','speaker']:
    r=envelopes[key]
    lines.append(f"|{key}|{r['candidate_model']}|{json.dumps(r['vendor_dimensions_mm'],ensure_ascii=False)}|{r['vendor_mass_g'] if r['vendor_mass_g'] is not None else '未知'}|{r['fit_status']}|")
lines += ['', '孔距、固定耳、连接器总高没有资料就留null；模型预留不是厂商实物尺寸。新增/变更件的安装孔先不定。其余板框建议沿用原交接作为占位，未通过即不冻结PCB板框。', '',
    '没有切换成三电机。两轮+两头部舵机仍四执行器，两颗ESP32-S3-WROOM-1-N16R8仍为双主控。FOC3PWM驱动不包含第三颗主控；其闭环资源必须重新审核。', '',
    '原始机械210°要求来自旧传动；当前V1 yaw±60°/pitch−20..25°的舵机轴到关节比仍要明确。不能看到商品标题270°就结束限位校核。', '',
    '公开价格/供货证据见[BOM核验](BOM_国内采购核验.md)。电气契约的procurement_update只发布候选变更，不授权用旧pinmap接线。','']
lines += ['补充筛选计算见[calculation_checks.json](calculation_checks.json)：2S低压直接带DRI0058不合格；300g·cm仅为约0.0294N·m，连续能力未知。现x=40.5mm低位皮带轮平面按理想球壳筛选向下半径空间约7.75mm，不能直接换成半径19.1mm的60齿GT2轮来获得3:1减速；实际带侧切壳网格仍待碰撞检查。','']
(P/'mechanical_handoff_H0.2.md').write_text('\n'.join(lines))

# Keep the old full report available; replace only our current landing page.
budget=json.loads((P/'budget_domestic.json').read_text())
readme='''# MORI V1-H0.2：国内采购核验更新

用户已允许预算适度超出1000元。当前需要闭合的是可采购SKU、电压/控制接口与安装包络；不再把原1000元硬预算作为不能继续的理由。

本次逐项核到16种国内公开有货/在售器件，15种有人民币公开单价；含不同轮驱评估件和被筛除的电池，不能全部相加。**完整BOM尚未冻结，也没有达到可整套下单状态。**

- [国内采购核验表](procurement/BOM_国内采购核验.md) / [CSV](procurement/BOM_国内采购核验.csv)：具体商品链接、选项、价格、库存观察、日期、供货与适配分栏。
- [当前主/备选候选BOM](bom_candidates.csv) / [JSON](bom_candidates.json)：保留USB-C、保护、回灌、线束、机械件、PCB、打印和运费等必要未报价项；没有记作免费已有。
- [国内预算计算](procurement/budget_domestic.json)：FOC国内已核标价部分782元，加入尚未报价额度的情景为1322元；有刷相应为767/1442元。均非含运费成交总价，风险余量100元未额外计入。
- [机械交接](procurement/mechanical_handoff_H0.2.md)：新器件真实公开尺寸已写共享机械契约，旧模型分配未变；未知孔位/高度/净质量保留null。
- [冲突表](conflicts.csv)：逐项说明供货问题已解决到哪一步，以及仍不能定板的具体原因。

头部主候选改SER0046×2，机身IMU改SEN0250，摄像头改OV5640-A，扬声器改FIT0825；圆屏使用国内Spotpear0201213。双主控仍ESP32-S3-WROOM-1-N16R8×2，功能和四执行器数量未删。

FOC评估对象现为FIT1034+DRI0058×2，电机/编码器/驱动共268元；供应商可售，但驱动最低8V，2S低压区不兼容，且没有轮端连续力矩证明。它不是Hover同款，也不能套旧UART接口。有刷FIT0521只作为一套备选，其成品H桥国内供货尚未核完。

电池优先候选为亚博2S2000mAh高倍率成品保护包，厂家国内销售链接已找到，选项价格/库存未取得。国内有货148元的FIT0137持续仅2.5A，不因有货就用来代填。

**接口状态：** shared electrical contract仍保留H0.1引脚作为历史候选，新增procurement_update明确H0.2器件不可照旧表接线。新FOC为3PWM，IMU为I2C，摄像头型号已变；要先审核资源并发布新的pinmap，再画原理图。

**验证状态：** 没有实物。全部硬件试验NOT_TESTED。V1原生KiCad工程/PCB仍未创建，ERC/DRC未执行；未导出制造文件、未采购。旧A0工程的检查不证明V1。H0.1质量/动力/续航是旧器件假设的敏感性分析，不能直接作为新BOM结果。

历史[H0.1完整报告](revisions/V1-H0.1/README.md)、[计算脚本](calculations/README.md)、[测试计划](test_plan.csv)仍保留。软件可继续[协议与模拟设备工作](software_parallel_prompt.md)，新外设驱动和实机使能需要候选接口闭合。

复算本次采购输出：`python3 hardware/v1/tools/build_domestic_bom.py`，然后运行`python3 hardware/v1/tools/publish_procurement_handoff.py`。旧H0.1生成脚本应在历史副本运行，不能覆盖本版。

新增[数值筛选](procurement/calculation_checks.json)可用`python3 hardware/v1/tools/check_domestic_feasibility.py`复算。亚博包14.8Wh按80%可用SOC和90%容量余量得到约10.7Wh；沿用旧11.34W压力情景仅约56分钟，故不能沿用进口大电池的92分钟估算。新BOM实际功耗/质量/惯量仍需补数据。
'''
(H/'README.md').write_text(readme)
checks={
    'revision':REV,'status':'PASS',
    'scope':'采购数据/加总/文件一致性；不证明电气、安装、供应商实物库存或实机性能',
    'part_rows':len(parts),'domestic_availability_rows':sum(p['domestic_availability_status']=='PASS' for p in parts),
    'priced_rows':sum(p['unit_price_cny'] is not None for p in parts),
    'mechanical_owned_fields_preserved':before_alloc==after_alloc,
    'actuator_count_each_route':4,'main_mcu_count':by_id['MCU']['quantity'],
    'missing_price_is_null':all(p['unit_price_cny'] is None for p in parts if p['price_status']=='BLOCKED'),
    'excluded_battery_not_in_main':all(r['model']!='DFRobot FIT0137 / 7.4V 2500mAh带保护电池' for r in catalog['items']),
    'pinmap_not_falsely_released':e['procurement_update']['pinmap_valid_for_new_candidates'] is False,
    'physical_tests':'NOT_TESTED','ERC':'NOT_TESTED','DRC':'NOT_TESTED'}
assert by_id['MCU']['quantity']==2
for motor in ['WH_FOC','WH_BRUSH']:assert by_id[motor]['quantity']+by_id['HD_SERVO']['quantity']==4
assert all(r.get('currency')=='CNY' for r in catalog['items'])
for p in parts:
    if p['unit_price_cny'] is not None:assert p['subtotal_cny']==round(p['quantity']*p['unit_price_cny'],2)
    if p['archived_http_sha256']:
        html=P/'evidence'/f"{p['id']}.html"
        assert hashlib.sha256(html.read_bytes()).hexdigest()==p['archived_http_sha256']
checks['archived_http_hashes_verified']=True
write(P/'validation.json',checks)
old_status=json.loads((H/'revisions/V1-H0.1/reports/validation_status.json').read_text())
old_status.update(revision=REV,generated_at_utc=datetime.now(timezone.utc).isoformat(),
    artifact_checks=checks,procurement='BLOCKED: incomplete domestic prices/parts; not original budget ceiling',
    historical_H0_1_checks='revisions/V1-H0.1/reports/validation_status.json')
old_status['KiCad']['reason']='Wheel power/control interface and mechanical fit remain unresolved. No V1 native schematic/PCB/ERC/DRC. Budget relaxation is recorded.'
write(H/'reports/validation_status.json',old_status)
manifest_files=[H/'README.md',H/'bom_candidates.json',H/'bom_candidates.csv',H/'conflicts.csv',
    mp,ep,P/'domestic_parts.json',P/'BOM_国内采购核验.csv',P/'BOM_国内采购核验.md',P/'budget_domestic.json',
    P/'mechanical_handoff_H0.2.md',P/'validation.json',P/'calculation_checks.json']
write(H/'reports/deliverables_manifest.json',{'revision':REV,'scope':'Current procurement and shared candidate metadata only',
    'files':[{'path':str(p.relative_to(R)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in manifest_files if p.exists()],
    'schematic_and_PCB_created':False,'manufacturing_files_exported':False})
print(json.dumps(checks,ensure_ascii=False,indent=2))

#!/usr/bin/env python3
"""Publish dated domestic procurement evidence, without claiming design release.

Run from any directory with Python 3.9+. All prices below are observed list
prices, never inferred transaction prices. Historical H0.1 inputs stay archived.
"""
import copy
import csv
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
H = ROOT / 'hardware/v1'
OUT = H / 'procurement'
REV = 'V1-H0.2'
DATE = '2026-09-21'


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def write_csv(path, rows):
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v
                         for k, v in row.items()} for row in rows)


# Source of truth for each observed product, not an automatic basket of all rows.
parts = []


def part(key, use, qty, model, url, price, stock, dims, mass, voltage, interface,
         decision, issue, bom_id=None, option=None, floor=None):
    evidence = OUT / 'evidence' / (key + '.json')
    source = json.loads(evidence.read_text()) if evidence.exists() else {}
    available = stock not in ('未核实', '未找到国内在售单品')
    parts.append(dict(id=key, bom_id=bom_id, purpose=use, quantity=qty,
        exact_model=model, purchase_option=option or model, domestic_product_url=url,
        unit_price_cny=price, published_starting_price_cny=floor,
        subtotal_cny=round(qty * price, 2) if price is not None else None,
        price_status='PASS' if price is not None else 'BLOCKED',
        price_basis='国内商品公开单价；不是成交或含运费报价' if price is not None else '小批量价格未核实；起价不代替1–2件单价',
        stock_observation=stock, domestic_availability_status='PASS' if available else 'BLOCKED',
        evidence_scope='网页有货/在售仅证明公开销售状态；未下单、未向商家确认交期',
        access_date=DATE, currency='CNY',
        shipping_basis='目的地结算未核；运费单列；不假定所有附件合单免邮',
        vendor_dimensions_mm=dims, vendor_mass_g=mass,
        voltage_or_rating=voltage, shaft_hole_interface=interface,
        selection_decision=decision, engineering_status='BLOCKED',
        engineering_issue=issue, physical_test_status='NOT_TESTED',
        alternative_and_readaptation='仅同表注明的单一轮驱备选；更换需重新核电压、孔位、线序、质量及驱动，不共用旧增益。',
        archived_http_evidence=str(evidence.relative_to(H)) if evidence.exists() else None,
        archived_http_sha256=source.get('sha256'),
        stock_evidence_method='浏览器可访问商品页/辅助技术页；动态库存人工读取，静态HTML空库存不当作缺货',
    ))


part('SER0046', '头部 yaw / pitch 位置舵机，模拟位置反馈', 2,
     'DFRobot SER0046 — 9g 270度金属带模拟值反馈舵机',
     'https://www.dfrobot.com.cn/goods-2594.html', 40, '有货',
     {'vendor_nominal_xyz':[22.9,12.2,32.5], 'including_mounting_ears':None}, 12,
     '4.8–6V；本设计5V稳压；6V堵转≤1.10±0.03A，不是连续电流',
     '红V+、黑GND、白PWM、棕模拟反馈0–3.3V；孔距/花键/固定耳另核',
     '国内主候选，替代未核国内价的FT90M-FB',
     '270±5°操作角与220±10°极限角相互矛盾；不能承诺带载210°。V1直接关节yaw±60°、pitch−20..25°仍需机构/行程校准；禁止直接打到500/2500us。质量±1g。', 'HD_SERVO')
part('MCU_C2913202', '两个主控模组', 2, 'Espressif ESP32-S3-WROOM-1-N16R8 / 立创C2913202',
     'https://item.szlcsc.com/3198300.html', None, '商品图片辅助页显示现货7233个（动态快照）',
     {'x':18,'y':25.5,'z':3.1}, None, '3.0–3.6V；16MB Flash / 8MB Octal PSRAM',
     '41pad SMD；天线净空另留；GPIO35/36/37不可当外设脚',
     '保留原主型号；国内渠道已确认，小批量单价未确认',
     '20.81元是“起”价，不能作为两只单价；网页商品毛重2.42g不能当模组净重。', 'MCU', floor=20.81)
part('SEN0250', '刚性机身IMU', 1, 'DFRobot SEN0250 / Gravity BMI160 6轴IMU',
     'https://www.dfrobot.com.cn/goods-1693.html', 49, '有货', {'pcb_xy':[22,27],'assembled_z':None}, None,
     '模块3.2–6V；采购后用3.3V；Gravity I2C；16bit；FIFO1024byte',
     'I2C与2个可编程中断；INT焊点/连接器端号待模块原理图复核',
     '国内主候选，替代Adafruit4438',
     '旧LSM6DSOX SPI引脚/833Hz配置不可沿用；需要I2C+DRDY、时戳与总线占用复核；22×27大于原26×18预留。', 'IMU')
part('LCD_0201213', '黑底双眼圆屏', 1, 'Spotpear 0201213 / 1.28inch-LCD-Module / GC9A01',
     'https://spotpear.cn/index/product/detail/id/742.html', 71, '在售（未公开件数）',
     {'active_diameter':32.4,'glass_diameter':37.5,'pcb_xy':[40.4,37.5],'assembled_z':None}, None,
     '240×240；SPI；3.3V供电和信号',
     'VCC/GND/DIN/CLK/CS/DC/RST/BL；含PH2.0 8PIN 20cm线',
     '国内主候选；用此完整SKU，不替换成7针裸屏',
     '显示区确为Ø32.4，不能画成原模型Ø58；保持黑色面罩但重做眼睛间距/显示支架。连接器高度及孔位仍待确认。', 'LCD')
part('OV5640_A', '头部照片/跟踪摄像头', 1, 'Spotpear 0204002 / OV5640-Camera-Board-(A)',
     'https://spotpear.cn/index/product/detail/id/260/no/198.html', 103, '在售（未公开件数）',
     {'pcb_xy':[35.7,23.9],'lens_and_connector_z':None}, None,
     '模块3.3V；8bit DVP + SCCB；最高2592×1944；对角视场63°',
     '选A型普通视角，不选B鱼眼/C自动对焦；模块端子线序待图纸',
     '国内主候选，替代未核国内来源的M0031',
     '明显大于14×8×10预留；先检查头部镜头位置和PCB朝向。网站PDF受访问限制，未确认信号IO电压/排针朝向。最高像素不是实时帧率；S3 JPEG/跟踪+音频并发NOT_TESTED。', 'CAM')
part('SEN0327', '单I2S麦克风', 1, 'DFRobot SEN0327 / I2S MEMS麦克风模块',
     'https://www.dfrobot.com.cn/goods-2567.html', 15, '有货', {'diameter':14,'z':None}, None,
     '1.8–3.3V；I2S', 'VCC/GND/SCK/WS/SD/LR；实际MEMS芯片不能凭外观认作INMP441',
     '保留，国内可售与价格已核', '声孔、隔振及完整厚度需机械复核；AEC播放参考从实际输出PCM取得。', 'MIC')
part('DFR0954', '扬声器I2S功放', 1, 'DFRobot DFR0954 / MAX98357 I2S功放模块',
     'https://www.dfrobot.com.cn/goods-3573.html', 30, '有货', None, None,
     '5V；8Ω最大输出标称1.8W，需限幅到所选喇叭',
     'I2S输入；OUT+与OUT−均不可接GND；SD静音与掉电隔离需核',
     '保留，国内可售与价格已核', 'PCB全尺寸/SD与I2S掉电容限仍需复核；不能按原22×18×6预留当实物尺寸。', 'AMP')
part('FIT0825', '扬声器，带声腔', 1, 'DFRobot FIT0825 / 1W扬声器（带音腔）',
     'https://www.dfrobot.com.cn/goods-3226.html', 12, '库存15（浏览器快照）',
     {'x':35,'y':20,'z':3.5,'dimension_tolerance':0.2,'wire_length':150}, None,
     '8Ω；1W；播放目标≤2.83Vrms并验证失真/温升',
     '1.25mm两线端子，确切系列及正负针序待核；侧面出声',
     '国内主候选，替代缺货Adafruit1890',
     '用厂家明确mm尺寸行；参数表另一行cm为明显冲突。现圆形安装位需改为矩形侧发声声道，不移除声学设计。', 'SPK')
part('DFR0564', '2S CC/CV充电模块', 1, 'DFRobot DFR0564 / 7.4V锂电池USB充电模块',
     'https://www.dfrobot.com.cn/goods-1706.html', 30, '有货',
     {'pcb_xy':[28,37],'assembled_z':None,'heatsink':[14,14,7]}, None,
     '输入3–6V；输出8.4V±1%；最大1A（受输入功率限制）',
     '板上microUSB；外观USB-C需单独CC识别/输入限流/ESD前端',
     '保留为2S充电候选；国内有货不等于整链匹配',
     '无均衡/LOAD；系统断开且托架上充电。8.484V公差上界、终止电流、保护包允许值尚未匹配；不能替代BMS。', 'CHG')
part('DFR0570', '运动/交互独立3.3V支路', 2, 'DFRobot DFR0570 / DC-DC 5.5–28V转3.3V模块',
     'https://www.dfrobot.com.cn/goods-1788.html', 15, '有货', {'pcb_xy':[16.5,22],'assembled_z':None}, None,
     '5.5–28V输入；3.3V输出；每域先按≤0.7A设计验证',
     '各域独立稳压但共电池共地；跨域UART防反向供电',
     '保留，国内可售与价格已核', '3A标题与2.4A峰值描述不一致；未宣称3A持续输出。', 'REG_3V3')
part('DFR0753', '头部/音频5V稳压支路', 1, 'DFRobot DFR0753 / DC-DC 6–14V转5V8A模块',
     'https://www.dfrobot.com.cn/goods-2971.html', 55, '有货', None, None,
     '6–14V输入；5V输出；8A为网页额定，壳内温升NOT_TESTED',
     '独立5V轨；母线回灌不可默认流过降压器',
     '保留，国内可售与价格已核', '完整板框/高度待CAD；两舵机并发与功放需验证，不能直接接8.4V。', 'REG_HEAD')
part('SEN0291', '电池电压/电流/功耗监测', 1, 'DFRobot SEN0291 / Gravity INA219数字功率计',
     'https://www.dfrobot.com.cn/goods-1890.html', 39, '有货', {'pcb_xy':[30,22],'assembled_z':None}, 4,
     '26V共模；分流10mΩ；网页量程8A', 'I2C；默认地址0x45；接线端子持续额定待核',
     '保留，国内可售与价格已核', '不能将INA219当硬件过流保护。板框超出原分配，Kelvin及高电流回路须布局。', 'PWR_MON')
part('FIT1034', 'FOC轮驱评估电机（非已通过的轮驱）', 2, 'DFRobot FIT1034 / 2804 BLDC+AS5600',
     'https://www.dfrobot.com.cn/goods-4230.html', 99, '库存8（23:51浏览器快照）',
     {'diameter':34.5,'length':19.5,'shaft_diameter':8,'hollow_bore_range':[5.4,6.5]}, None,
     '7.4–16V；标称12V；页面约0.03Nm；0.4A额定/1A最大；不当作已验证持续轮端扭矩',
     'AS5600 3.3V，12bit，默认I2C；UVW；7极对；GH/MX1.25-4P标注冲突待核',
     '国内FOC优先评估对象；不是Hover同款/不是装机放行',
     '2S低电压低于电机7.4V下限；还需驱动供电。8mm轴和Ø34.5不能套用Ø25/4mm支架。12V×0.4A≠网页12W；连续扭矩未知，必须实测。', 'WH_FOC')
part('DRI0058', 'FOC轮驱功率板', 2, 'DFRobot DRI0058 / SimpleFOCmini',
     'https://www.dfrobot.com.cn/goods-4248.html', 35, '有货', {'pcb_xy':[26,21.5],'assembled_z':None}, None,
     '输入8–30V；网页每路最高2.5A；3.3V控制兼容',
     'UVW+3PWM/使能，非UART智能轮驱；不含已核实的相电流采样',
     '与FIT1034成对评估；需重新设计控制接口',
     '2S全放电区间不兼容；不得忽略8V下限。电压FOC命令是V而非SI Nm；更换原UART方案需新的GPIO资源表与闭环实现。', 'FOC_DRV')
part('FIT0521', '唯一有刷轮驱备选', 2, 'DFRobot FIT0521 / 6V 210RPM金属编码减速电机',
     'https://www.dfrobot.com.cn/goods-1427.html', 99, '有货；商品页免邮标记',
     {'diameter':24.4,'length':52}, 96, '额定6V；候选独立5V轨降额；编码器3.3V；3.2A为6V堵转',
     '真实A/B反馈；PH2.0-6P；轴/安装孔需尺寸图',
     '保留唯一关键替代，不自动切换主路线',
     '有货但连续扭矩未核；厂家PPR乘法/功率点矛盾；DRV8874成品驱动国内货源尚未核实；不得套用Hover增益。', 'WH_BRUSH')
part('YAHBOOM_2S_2000', '成品高倍率2S保护电池包', 1, '亚博智能 7.4V 2S 2000mAh 高倍率电池（官方选项）',
     'https://detail.tmall.com/item.htm?id=694699380589', None, '未核实',
     {'x':37,'y':67,'z':22}, 115,
     'Li-ion 2S；7.4V/2000mAh；满8.4V；厂商15A持续/20A最大；放电范围5.6–8.4V',
     '工厂电池包带过充/过放/过流/短路保护；AWG14出线15cm；接头型号及均衡未知',
     '国内电池优先候选，替代进口ANSMANN；价格/库存未核，不许写已确认',
     '官方链接跳转登录且浏览器访问被限制；没有绕过。不能借其他容量低价代填。保护不是均衡，充电允许公差/回灌/NTC还需匹配。尺寸厚22无减振余量。', 'BAT',
     option='7.4V / 2000mAh / 高倍率；不选6600或9900mAh，也不选电池盒')
part('FIT0137', '被筛除的国内电池比较件（不加入主BOM）', 1, 'DFRobot FIT0137 / 7.4V 2500mAh带保护电池',
     'https://www.dfrobot.com.cn/goods-434.html', 148, '有货', {'x':103,'y':34,'z':15}, None,
     '2S；18.5Wh；持续1C=2.5A；页面5C最大无时长', 'DC2.1插头，额定电流/保护阈值待核',
     '不推荐装机；采购有货，电气适配FAIL',
     '2.5A持续不足现5.28A并发目标，且103mm长需重布。网页另有不安全充电文字，不采纳；只能用匹配CC/CV充电器。')


def main():
    current = json.loads((H / 'bom_candidates.json').read_text())
    if current.get('revision') not in ('V1-H0.1', 'V1-H0.2'):
        raise SystemExit('H0.2 generator is historical. Use publish_display_motor_review.py for H0.3; refusing to restore withdrawn screen/motor candidates.')
    OUT.mkdir(parents=True, exist_ok=True)
    archive = H / 'revisions/V1-H0.1'
    if not (archive / 'bom_candidates.json').exists():
        old = json.loads((H / 'bom_candidates.json').read_text())
        if old['revision'] != 'V1-H0.1':
            raise RuntimeError('Refuse to infer missing H0.1 archive from another revision')
        for rel in ['bom_candidates.json', 'bom_candidates.csv', 'README.md', 'conflicts.csv',
                    'reports/budget.json', 'reports/deliverables_manifest.json',
                    'reports/validation_status.json']:
            src = H / rel
            if src.exists():
                dst = archive / rel; dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src,dst)
    base = json.loads((archive / 'bom_candidates.json').read_text())
    byid = {r['id']: r for r in base['items']}
    mapped = {p['bom_id']:p for p in parts if p['bom_id']}
    # Add actual FOC driver and explicitly account for the missing compatible rail.
    byid['FOC_DRV'] = copy.deepcopy(byid['WH_FOC'])
    byid['FOC_DRV'].update(id='FOC_DRV', purpose='FOC功率板', planning_unit_allowance_cny=None)
    byid['FOC_SUPPLY'] = copy.deepcopy(byid['BRAKE'])
    byid['FOC_SUPPLY'].update(id='FOC_SUPPLY', route='FOC', purpose='覆盖2S放电范围的FOC升压供电与保护',
        model='尚未选定符合电流/回灌要求的国内模块', quantity=1, unit_price=None,
        planning_unit_allowance_cny=45, source_url='', procurement_channel='未核实',
        notes='45元为情景额度，不是商品报价。DRI0058最低8V，FIT1034最低7.4V；不能直接接2S至低电量。')
    for row in byid.values():
        row.update(revision=REV, domestic_availability_status='BLOCKED', stock_observation='未核实',
                   stock_access_date=None, procurement_evidence=None,
                   selection_status='CANDIDATE_NOT_RELEASED', engineering_status='BLOCKED')
        if row['id'] in mapped:
            p = mapped[row['id']]
            row.update(model=p['exact_model'], procurement_channel=p['domestic_product_url'],
                source_url=p['domestic_product_url'], unit_price=p['unit_price_cny'],currency='CNY',
                price_date=DATE if p['unit_price_cny'] is not None else None,
                price_status=p['price_basis'], vendor_dimensions_mm=p['vendor_dimensions_mm'],
                vendor_mass_g=p['vendor_mass_g'], voltage_or_rating=p['voltage_or_rating'],
                shaft_hole_interface=p['shaft_hole_interface'],
                domestic_availability_status=p['domestic_availability_status'],
                stock_observation=p['stock_observation'], stock_access_date=DATE,
                procurement_evidence='procurement/domestic_parts.json#'+p['id'],
                notes=p['engineering_issue'], confirmation_status=p['selection_decision'],
                shipping_basis=p['shipping_basis'], purchase_option=p['purchase_option'],
                published_starting_price_cny=p['published_starting_price_cny'],
                planning_unit_allowance_cny=None if p['unit_price_cny'] is not None else row.get('planning_unit_allowance_cny'))
        elif row['id']=='BR_REG':
            p = mapped['REG_HEAD']
            row.update(domestic_availability_status='PASS', stock_observation=p['stock_observation'],
                       stock_access_date=DATE, procurement_evidence='procurement/domestic_parts.json#DFR0753')
        elif row.get('currency') != 'CNY':
            row['historical_foreign_price']={'amount':row['unit_price'],'currency':row['currency'],
                'note':'历史参考；不算国内可买或国内报价'}
            row.update(unit_price=None, currency='CNY', price_date=None,
                price_status='国内小批量价格待核；国外参考不计入国内已核价小计',planning_unit_allowance_cny=90)
    byid['BAT']['planning_unit_allowance_cny']=100
    byid['BAT']['technical_source_url']='https://www.yahboom.com/public/upload/upload-html/1706341250/机器人充电与电池注意事项.html'
    byid['MCU']['procurement_stock_source_url']='https://item.szlcsc.com/product/jpg_3198300.html'
    for key in ['USB_C','SAFE','BRAKE','IO_SAFE','PASSIVE','PCB','HARNESS','MECH_DRIVE','FASTEN','PRINT','SHIP']:
        byid[key]['notes'] += ' 国内具体SKU/服务报价尚未逐项确认，不列入“已核国内现货”。'
    base.update(revision=REV, status='PROTOTYPE_DOMESTIC_PROCUREMENT_INCOMPLETE', accessed=DATE,
        budget_cny={'original_main_target':900,'original_limit':1000,'original_reserve':100,
                    'current_hard_limit':None,'policy':'用户2026-09-21允许适度超出；没有新的明确上限；不再仅因超过1000判FAIL；不代表无限预算或采购授权'},
        fx_cny_per_unit={'CNY':1},fx_status='国内核价全部CNY；历史USD/EUR不换汇混算',
        physical_models_status='H0.1质量/惯量/续航报告是历史敏感性结果；器件变化后不得当成H0.2实物计算',
        items=list(byid.values()))
    write_json(H / 'bom_candidates.json', base)
    write_csv(H / 'bom_candidates.csv', base['items'])
    write_json(OUT / 'domestic_parts.json', dict(revision=REV, access_date=DATE,
        procurement_complete=False, assembly_released=False, parts=parts))
    write_csv(OUT / 'BOM_国内采购核验.csv', parts)
    budget={'revision':REV,'status':'BLOCKED','blocking_reason':'主轮驱供电/电池实时报价及必需小料未闭合，不是1000元硬预算',
            'budget_policy':base['budget_cny'],'full_landed_quote_cny':None,'routes':{}}
    for route in ['FOC','BRUSH']:
        rs=[r for r in base['items'] if r['route'] in ['COMMON',route]]
        known=sum(r['quantity']*r['unit_price'] for r in rs if r['unit_price'] is not None)
        unknown=[r['id'] for r in rs if r['unit_price'] is None]
        scenario=sum(r['quantity']*(r['unit_price'] if r['unit_price'] is not None else r['planning_unit_allowance_cny']) for r in rs)
        budget['routes'][route]={'domestic_public_price_subtotal_cny':round(known,2),
            'unquoted_rows':unknown,'unquoted_count':len(unknown),
            'planning_total_with_unquoted_allowances_cny':round(scenario,2),
            'scenario_over_original_1000_cny':round(scenario-1000,2),
            'not_a_landed_quote':True, 'stock_and_price_complete':False,
            'allowances_include_shipping_and_prototype':True,'risk_reserve_included':False}
    write_json(OUT / 'budget_domestic.json',budget)
    # Current entry point must not keep presenting foreign H0.1 sums as current.
    write_json(H / 'reports/budget.json',budget)
    rows=['# MORI V1-H0.2 国内采购核验', '',
          '核验日期：2026-09-21。**国内在售与装机适配分栏；这不是完整定型/下单BOM。** 用户已允许预算适度超出1000元，不据此放宽电气/安装要求，也未授权购买。', '',
          '|用途|数量|完整采购型号 / 商品页|单价CNY|网页供货状态|结论|',
          '|---|---:|---|---:|---|---|']
    for p in parts:
        price=f"{p['unit_price_cny']:.2f}" if p['unit_price_cny'] is not None else '待核价'
        rows.append(f"|{p['purpose']}|{p['quantity']}|[{p['exact_model']}]({p['domestic_product_url']})|{price}|{p['stock_observation']}|{p['selection_decision']}|")
    rows += ['', '“有货”为厂商页面动态显示；“在售”没有公开库存件数，两者不混写。“起价”不是本次数量成交价。运费、交期和收货地址结算未核实；没有加入购物车或下单。', '',
             f"已找到{sum(p['domestic_availability_status']=='PASS' for p in parts)}种国内公开在售/有货对象，其中{sum(p['unit_price_cny'] is not None for p in parts)}种有确定人民币标价；含被筛除的FIT0137与FOC/有刷不同路线，**不能把整表相加当一台成本**。亚博电池只有厂家提供的国内销售链接，实时选项价格/库存未核实。", '',
             '## 两条路线的成本口径', '',
             '|路线|国内已核公开标价部分|未核价行数|含未报价额度的情景总额|',
             '|---|---:|---:|---:|']
    for route,r in budget['routes'].items():
        rows.append(f"|{route}|¥{r['domestic_public_price_subtotal_cny']:.2f}|{r['unquoted_count']}|¥{r['planning_total_with_unquoted_allowances_cny']:.2f}|")
    rows += ['', '情景总额含未报价预算额度，包含一次PCB/组装、线束、紧固件、打印料和运费；不含额外100元风险余量。它不是可付款总价。没有必要零件记为“已有免费”。具体额度见主BOM的planning_unit_allowance_cny。', '',
        '## 原来三处为何没闭合，以及本次改正', '',
        '1. **轮驱**：此前只留Hover的“4012”，没有可采购完整型号。本次找到FIT1034+DRI0058，双轮电机/编码器/驱动公开价合计268元。但0.03Nm不是足够的轮端连续扭矩证明，且驱动最低8V。它是可买的评估候选，不能直接当作2S整机定型。FIT0521双电机198元为唯一有刷备选，独立驱动国内货源仍待落实；没有偷换成PWM并沿用Hover增益。',
        '2. **电池/充电**：亚博2S2000mAh高倍率工厂包给出了尺寸、15A持续与20A最大规格，国内官方销售页需登录，本次未取得价格/库存。另核到了有货148元的FIT0137，但2.5A持续能力不足原5.28A并发目标，不能为了填满BOM就选它。DFR0564可国内购买，但保护、均衡、输入限流、充电电压公差和回灌不是一个“BMS”能概括。',
        '3. **其他型号/尺寸**：舵机、IMU、摄像头和扬声器现有国内具体替代，并已记实际公开尺寸。固定耳、摄像头板和连接器净空需要回写机械；这属于适配，不能再笼统说“零件买不到”。', '',
        '## 尚不能写成已确认的项目', '',
        '- 电池选项的实时价格/库存、MCU本次数量价格、FOC合规低压供电、备选H桥的国内成品板。',
        '- USB-C输入/保护/急停/回灌小料、端子线束、轮胎传动件、紧固件、打印材料、PCB及组装/运费尚未全部展开到国内具体SKU/服务报价。它们留在主BOM，不按零元删掉。',
        '- 所有电机连续能力、编码器时延、温升、声学、并发和60分钟续航均NOT_TESTED。没有因为国内有货就把样机资格改PASS。',
        '- 新版IMU为I2C，摄像头为OV5640，FOC评估板为3PWM接口；H0.1 pinmap仍是旧候选，不能拿来接这些新候选。硬件接口未冻结，软件可以继续协议/模拟设备工作。', '',
        '证据文件在[evidence/](evidence/)，尺寸和数据缺口在[完整CSV](BOM_国内采购核验.csv)。国内公开价格计算可用 `python3 hardware/v1/tools/build_domestic_bom.py` 重跑；没有访问硬件，也没有伪造实测。', '']
    (OUT / 'BOM_国内采购核验.md').write_text('\n'.join(rows))
    print(json.dumps(budget,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()

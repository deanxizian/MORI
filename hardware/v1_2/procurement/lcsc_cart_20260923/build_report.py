#!/usr/bin/env python3
"""Reconcile a user-exported LCSC cart with the read-only project BOM."""
from pathlib import Path
from decimal import Decimal
import csv, json, re, shutil, collections
import xlrd

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
download = Path('/Users/dean/Downloads/立创商城购物车详情.xls')
shutil.copy2(download, OUT / '立创商城购物车详情_20260923.xls')
s = xlrd.open_workbook(str(download)).sheet_by_index(0)
cart = [dict(zip(s.row_values(0), s.row_values(i))) for i in range(1, s.nrows)]
rows = list(csv.DictReader((ROOT / 'hardware/v1_2/bom.csv').open(encoding='utf-8-sig')))
def norm(x):
    return re.sub('[^A-Z0-9]', '', x.upper().replace('AMASS ', ''))
by_mpn = {norm(r['商品型号']): r for r in cart}
by_code = {r['商品编号']: r for r in cart}
special = {'body_imu': 'C1850418', 'speaker': 'D2884871', 'physical_disable': 'C42378287', 'logic_power': 'C311983', 'p1_dump_head': 'C1575735'}
preexisting = {'C1850418', 'C91874', 'C21404', 'D2884871'}
joined, used = [], set()
for r in rows:
    choice = 'LM393BIDR' if r['id'] == 'p4_027' else r['full_model']
    c = by_code.get(special.get(r['id'], '')) or by_mpn.get(norm(choice))
    note = ''
    if r['id'] == 'p4_027':
        note = '采购选型更正：LM393BDR未找到；采用TI完整订货号LM393BIDR。SOIC-8及U20/U40引脚逐项一致；原生KiCad和合同未改。'
    if r['id'] == 'speaker':
        choice = 'Same Sky CMS-4017-34SP（机械选型/购物车原有）'
        note = '机械M1.10已选，购物车原有1个；电气主BOM仍写待选，保留差异。'
    if c:
        used.add(c['商品编号'])
        state = '原购物车已有' if c['商品编号'] in preexisting else '本次已加入'
        if c['购买类型'] == '订货':
            note += ' 商城订货项，当前非现货，购物车价格与交期不是最终报价。'
    elif r['quantity'] == '0':
        state = 'NOT_APPLICABLE：数量0'
    elif r['id'] in ['wheel_servo', 'head_servo', 'motion_mcu', 'interaction_cam', 'display', 'wheel_power', 'head_power']:
        state = '按用户后续要求：开发板/成品模块不继续商城搜寻'
    elif r['id'] == 'p1_dump_wheel':
        state = 'BLOCKED：未获得可加购编号/报价（外接5.6Ω泄放电阻）'
    elif r['id'] == 'lcd_cable':
        state = '随LCD供货清单；未另购'
    elif r['id'] in ['carrier_pcb', 'printing', 'shipping', 'p4_assembly_service']:
        state = '定制制造/服务/运费；未下单'
    else:
        state = 'BLOCKED：精确型号或规格待定'
    joined.append({
        'BOM_ID': r['id'], '用途': r['purpose'], '单机用量': r['quantity'], '单位': r['quantity_unit'],
        '设计BOM型号': r['full_model'], '本次采购选型': choice,
        '立创编号': c['商品编号'] if c else '', '商城实际型号': c['商品型号'] if c else '',
        '厂家': c['品牌'] if c else '', '封装': c['封装规格'] if c else '',
        '购物车数量': int(c['购买数量']) if c else '', '渠道': c['购买类型'] if c else '',
        '显示单价_元': c['商品单价(元)'] if c else '', '显示小计_元': c['金额(元)'] if c else '',
        '处理结果': state, '位号': r.get('schematic_references', ''), '说明': note,
    })
assert len(cart) == 70 and len(used) == 70, (len(cart), len(used), set(by_code)-used)
assert all(r['立创编号'] for r in joined if r['BOM_ID'].startswith('p4_') and r['BOM_ID'][3:].isdigit())
assert all(r['立创编号'] for r in joined if r['BOM_ID'].startswith('p4_ph'))
for filename, data in [('MORI_单机硬件BOM_含采购结果.csv', joined), ('立创购物车明细.csv', cart)]:
    with (OUT / filename).open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(data[0]))
        w.writeheader()
        w.writerows(data)
summary = {
    'date': '2026-09-23', 'source_rows': len(rows), 'cart_rows': len(cart), 'added_rows': 66, 'preexisting_rows': 4,
    'cart_channels': dict(collections.Counter(c['购买类型'] for c in cart)),
    'cart_shown_cny': str(sum(Decimal(str(c['金额(元)'])) for c in cart)),
    'newly_added_shown_cny': str(sum(Decimal(str(c['金额(元)'])) for c in cart if c['商品编号'] not in preexisting)),
    'checkout_submitted': False, 'orders_submitted': False, 'native_design_updated': False,
    'coverage': 'All 59 PCB-part categories, ICM chip, TPS54302, rear switch and 6 PH harness categories mapped to cart; includes 3 PCB ordering categories. U100 module excluded.',
    'scope': 'One robot. P4 BOM quantities compared with four P5 assembly exports; no value changes. Source hashes unchanged at final check.',
    'selection_change': {'original': 'LM393BDR', 'selected': 'TI LM393BIDR', 'code': 'C2865059', 'refs': ['MORI_power_P5:U20', 'MORI_power_P5:U40'], 'per_robot': 2, 'cart_quantity': 5, 'package': 'SOIC-8_3.9x4.9mm_P1.27mm', 'pins': {'1': 'OUT1', '2': 'IN1-', '3': 'IN1+', '4': 'GND', '5': 'IN2+', '6': 'IN2-', '7': 'OUT2', '8': 'VCC'}, 'datasheet': 'https://www.ti.com/lit/ds/symlink/lm393b.pdf', 'orderable': 'https://www.ti.com.cn/product/cn/LM393B/part-details/LM393BIDR', 'check': 'VENDOR_DOCUMENTED package and native symbol pins checked; bench NOT_TESTED', 'handoff': 'Hardware owner should sync complete order code into active P5 BOM; no circuit or footprint change intended.'},
}
(OUT / 'procurement_result.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(summary, ensure_ascii=False, indent=2))

def clean(value):
    return str(value).replace('|', '/').replace('\n', ' ')

def table_row(values):
    return '|' + '|'.join(clean(v) for v in values) + '|'

def is_detail(row):
    k = row['BOM_ID']
    return k.startswith('p4_') and (k[3:].isdigit() or k.startswith('p4_ph'))

intro = '''# MORI 硬件 BOM 与立创购物车核对

核对日期：2026-09-23（北京时间），按1台MORI。主BOM共97行，含成品模块、器件、机械件、服务、运费和待选型项。

新增 **66种**，保留原购物车 **4种**，合计 **70种**。购物车显示 **¥550.12**，其中本次新增 **¥355.29**；65种现货、4种订货、1种原有海外代购。没有结算、提交订单或付款。

单机用量和购物车数量分别列出；后者按商城起订量/增量增加。订货项当前无现货，显示金额与交期不构成最终报价；邮费未核。

## 文件

- [完整97行BOM及采购结果](MORI_单机硬件BOM_含采购结果.csv)
- [立创实际导出购物车Excel](立创商城购物车详情_20260923.xls)
- [购物车明细CSV](立创购物车明细.csv)
- [机械物料明细，含打印件与占位件](MORI_机械物料明细_含占位件.csv)
- [结构化核验和选型更正](procurement_result.json)

## 选型更正

电源板U20、U40：**LM393BDR → TI LM393BIDR（C2865059）**。采用LM393B的完整可订货料号，保留SOIC-8封装。原生符号8个引脚与TI资料逐项一致：1OUT1、2IN1−、3IN1+、4GND、5IN2+、6IN2−、7OUT2、8VCC。单机2个，商城5个起，已加入5个。台架验证为NOT_TESTED。[TI订货信息](https://www.ti.com.cn/product/cn/LM393B/part-details/LM393BIDR) · [TI数据手册，第3页引脚表](https://www.ti.com/lit/ds/symlink/lm393b.pdf)。

“本次采购选型”列是本任务采用的采购BOM。P5由另一任务继续布局，本次没有覆盖原生KiCad、contracts/components.json或原设计BOM；U20/U40的完整订货号待硬件任务同步，电路与封装无意改变。四块P5导出的位号/元件值与P4比较无差异；源文件哈希已保存。

AO3400A / AO4407A采用原选型AOS，分别为C20917 / C16072。没有加入自动匹配的UMW同名替代料。商城RC0603电阻料号多一个连字符，是格式差异，未更改阻值或封装。

## 非现货与缺项

|项目|实际处理|
|---|---|
|PESD5V0L1BA,115 / C85380 ×5|购物车订货区；搜索页有订货渠道，当前无现货，数量、价格、交期需商家最终核价。|
|EEUFR1C102 / C407878 ×2|购物车订货区。|
|MS-202V-G3 / C42378287 ×1|购物车订货区；保留既定后板开关的机械接口。|
|AC05000001009JAC00 / C1575735 ×5|购物车订货区；外接10Ω泄放电阻，脉冲与散热未实测。|
|CMS-4017-34SP ×1|原购物车海外代购，页面交期8–14个工作日，保留原项。|
|AC05000005608JAC00 ×1|未取得可加入购物车的商品编号和报价；这是外接5.6Ω泄放电阻。|
|开发板、摄像头/显示模块、舵机、Pololu模块|按用户后续要求停止继续商城搜索，仍保留在整机BOM。|
|电池、充电器、外置保险座、未定线束/排母、紧固件|精确规格尚未确定，保留BLOCKED，未按占位参数购买。|
|自制PCB、打印、金属加工、贴装|没有提交制造订单。|

全部59类PCB散件、ICM芯片、TPS54302、后板开关及6类PH线束端子都有对应购物车项，其中3类板载器件为订货。开发板U100单列。DNP的电源J6、数量为0的独立功能按钮不计入购买数量。CAM板载麦克风、codec、功放不重复购买。

整机仍是PROTOTYPE / UNVALIDATED。当前购物车未覆盖全部电机、开发板、电池、加工和运费，不能据此宣称整机≤1000元。

## 整机模块、机构及服务

|ID|项目/型号|单机数量|采购结果|
|---|---|---:|---|
'''
lines = [intro.rstrip()]
for r in joined:
    if not is_detail(r):
        state = r['处理结果'] + (' / ' + r['立创编号'] if r['立创编号'] else '')
        lines.append(table_row([r['BOM_ID'], r['本次采购选型'], r['单机用量'], state]))
lines.extend(['', '## PCB散件与PH线束端子', '', '|ID|商城型号|厂家|单机用量|立创编号|购物车数量|渠道|显示小计¥|', '|---|---|---|---:|---|---:|---|---:|'])
for r in joined:
    if is_detail(r):
        lines.append(table_row([r['BOM_ID'], r['商城实际型号'], r['厂家'], r['单机用量'], r['立创编号'], r['购物车数量'], r['渠道'], r['显示小计_元']]))
lines.extend(['', '## 核验记录', '',
    '- 从已登录购物车读取初始4项，逐项加入66项并核对商品编号和数量；原有数量不变。',
    '- 通过购物车“更多操作 → 导出至Excel”下载70项明细。与采购BOM一对一对应，行金额合计¥550.12，和购物车显示一致。',
    '- 初始自动匹配错误包含其他厂家的同名MOS管、裸芯片代替开发板、SKU编号误作数量。这些错误项没有加入购物车；云端原始草稿已重命名“含误匹配，勿下单”并全部取消勾选。',
    '- 源文件：hardware/v1_2/bom.csv、四块P5 assembly_bom.csv、两个contracts文件、mechanical/reports/bom.csv；读取哈希见source_hashes.json。',
    '- 工具：Codex浏览器UI、Python csv/json/hashlib、xlrd 2.0.2。解析依赖放在/tmp/mori_bom_pydeps，未改变项目依赖。',
    '- 重建命令：PYTHONPATH=/tmp/mori_bom_pydeps python3 hardware/v1_2/procurement/lcsc_cart_20260923/build_report.py。',
    '- 未修改电路/布局，没有重新运行ERC/DRC；购物车准备不等于硬件资格验证。',
    ''])
(OUT / 'MORI_BOM与采购结果.md').write_text('\n'.join(lines))

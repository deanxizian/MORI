#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Derive assembly documentation from immutable P5R6/P5R4 native ports.

Run with KiCad Python. Writes only wiring_P5R6 documentation, never CAD or shared
contracts. Vendor-end unknown pins and cable lengths remain unknown.
"""
from pathlib import Path
from collections import defaultdict
import csv
import hashlib
import html
import json
import math
import re
import xml.etree.ElementTree as ET
import pcbnew as k

ROOT = Path(__file__).resolve().parents[3]
H = ROOT / 'hardware/v1_2'
OUT = H / 'wiring_P5R6'
REV = 'V1.2-H0.5-P5R6-W1'
VERSIONS = dict(power='P5R6', motion='P5R6', imu='P5R4', rear='P5R6')
LABEL = dict(power='电源板', motion='运动板', imu='IMU板', rear='后接口板')
NAME = {kind: f'MORI_{kind}_{v}' for kind, v in VERSIONS.items()}
ALIASES = {n: kind for kind, n in NAME.items()}
PURPOSE = {
 'power': {
  'J1': ('电池输入', '成品3S电池，经外部总保险', '1=GND，2=正极；电池及保险精确型号待确认'),
  'J2': ('轮降压器输入供电', '外部9V降压器 VIN/GND', '这里输出3S电池母线；不可直接接9V电机'),
  'J3': ('轮降压器输出回接', '外部9V降压器 VOUT/GND', '接稳压9V输出；不可与J2直接短接'),
  'J4': ('头部降压器输入供电', '外部6V降压器 VIN/GND', '这里输出3S电池母线；不可直接接6V舵机'),
  'J5': ('头部降压器输出回接', '外部6V降压器 VOUT/GND', '接稳压6V输出；不可与J4直接短接'),
  'J6': ('电池母线维护预留', '不接线，DNP', '默认不装；不是5V输出'),
  'J7': ('左轮电机电源及总线', '左 S288', '3脚为单线半双工数据；电机端针序待核'),
  'J8': ('右轮电机电源及总线', '右 S288', '与左轮共总线；两电机必须分配不同ID'),
  'J9': ('双轴头部舵机链', 'SCS0009 yaw/pitch链', '两舵机共头部总线；连接顺序/厂配线待确认'),
  'J10': ('运动控制及监测', '运动板 J7，同号接线', 'PH8，但不可与IMU用的PH8互换'),
  'J11': ('轮母线制动电阻', '外部5.6Ω制动电阻', '1=W_DUMP_D开关漏极，不是GND；电阻跨1、2'),
  'J12': ('头母线制动电阻', '外部10Ω制动电阻', '1=H_DUMP_D开关漏极，不是GND；电阻跨1、2'),
  'J13': ('轮数据输入', '运动板 J2，同号接线', '仅数据和参考地，不给电机供电'),
  'J14': ('头数据输入', '运动板 J3，1→1、2→2', '两端3号孔均不装端子，保持NC'),
  'J15': ('附加托架禁驱接点', '可选托架干接点', '闭合1–2拉低CHG_N禁驱；断线开路不能自诊断'),
  'J16': ('USB原始VBUS检测', '后板 J2.5→1、J2.2→2', '只检测，不是充电功率输入；RAW源端保护未闭合'),
  'J17': ('运动5V输出', '运动板 J1，同号接线', '1=+5V，2=GND；与电池XT30针序不同'),
  'J18': ('交互5V输出', 'CAM33700 稳压5V USB供电尾线', '1=+5V，2=GND；不得接CAM单节BAT口'),
  'J19': ('物理总开关控制', '后板 J3.1→1、J3.2→2', '1脚OFF时可能接近电池电位；不可混插其他PH2'),
  'JP60': ('运动5V维护关闭', '正常开路；托架上才可短接', '短接1–2关闭运动5V，会失去平衡'),
  'JP70': ('交互5V维护关闭', '正常开路；托架上才可短接', '短接1–2仅关闭交互5V；不是外部供电口'),
 },
 'motion': {
  'J1': ('运动5V输入', '电源板 J17，同号接线', 'MCU本地生成3.3V；不得直接接3S'),
  'J2': ('轮半双工总线', '电源板 J13，同号接线', '只接信号及地；不是两轮电源口'),
  'J3': ('头半双工总线', '电源板 J14，1→1、2→2', '两端3号孔均不装端子'),
  'J4': ('身体IMU SPI', 'IMU板 J1，1–8同号', '3.3V供电；两个GND都接；不与J7互换'),
  'J5': ('CAM UART及参考电源', 'CAM33700 J11，1–4同号', 'RX/TX按CAM端命名，不再交叉；3脚仅供U4 VCCB'),
  'J6': ('机内维护按键', '可选无源瞬时按键', '1–2闭合为低有效；不是RESET，也不是急停'),
  'J7': ('电源控制及ADC', '电源板 J10，1–8同号', 'PH8，但不可与J4的IMU线互换'),
  'J8': ('硬件解锁许可环路', '后板 J3.3→1、J3.4→2', '开路清除ARM；恢复闭合不能自动重新解锁'),
 },
 'imu': {'J1': ('身体IMU SPI及供电', '运动板 J4，1–8同号', '刚性装在身体，SPI线长按实际布置测量')},
 'rear': {
  'J2': ('PD/充电器及VBUS检测', '1–4外部PD；5分支至电源J16', '后装侧插PH5；1=FUSED、5=RAW，禁止桥接'),
  'J3': ('总开关及禁驱分叉线', '1/2至电源J19；3/4至运动J8', '必须一分二线束；两条控制回路不可短接'),
  'SW1': ('双刀物理电源开关', '板载器件，无独立外接线', 'ON接通1–2和4–5；拨杆方向须实测'),
  'USB1': ('唯一外部USB-C充电接口', 'USB-C电源，经外部PD/3S充电器', '无USB数据；本板没有PD协商/3S充电控制'),
 },
}


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p): return json.loads(p.read_text())
def dump(p, d): p.write_text(json.dumps(d, ensure_ascii=False, indent=2)+'\n')
def readcsv(p): return list(csv.DictReader(p.open(encoding='utf-8-sig')))
def xy(p): return [round(k.ToMM(p.x), 6), round(k.ToMM(p.y), 6)]
def clean(n): return 'NC' if n.startswith('unconnected-') else n.lstrip('/')
def sortref(r): return (re.sub(r'\d+', '', r), int(re.search(r'\d+', r)[0]) if re.search(r'\d+', r) else 0)


def csvout(name, rows):
    with (OUT/name).open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def voltage(net):
    if net == 'NC': return '不连接'
    if net == 'GND': return '0V参考地'
    if net in ['PACK_FUSED', 'BAT_MON']: return '3S母线，设计上限12.6V'
    if net == 'MASTER_RETURN': return '开关控制，OFF时可接近3S电压'
    if net == 'W9_IN': return '外部稳压9V'
    if net == 'H6_IN': return '外部稳压6V'
    if net in ['W_VM', 'W_DUMP_D']: return '轮母线，9V经保护后；含制动瞬态'
    if net in ['H_VM', 'H_DUMP_D']: return '头母线，6V经保护后；含制动瞬态'
    if net.startswith('+5V'): return '标称5V；设定计算约5.077V'
    if net in ['VBUS_RAW', 'VBUS_FUSED', 'VBUS_CHARGE']: return 'USB VBUS；允许电压待PD方案确认'
    if net in ['CC1', 'CC2']: return 'USB-C CC信号，由外部受电控制器处理'
    if net in ['M5_EN', 'C5_EN']: return 'EN内部上拉；仅允许拉GND关闭'
    if net.endswith('BUS'): return '板端3.3V TTL；执行器阈值待核'
    if 'ADC' in net: return '3.3V ADC域的模拟信号'
    return '3.3V逻辑/电源域'


def pin_detail(kind, ref, pin, net):
    text = {
      'GND': '信号/电源参考地', 'NC': '不连接；线束孔位不装端子',
      'PACK_FUSED': '外部总保险后的成品3S电池正极', 'BAT_MON': '开关/反接保护/分流器后的电池母线',
      'W9_IN': '外部轮降压器9V输出回接', 'H6_IN': '外部头降压器6V输出回接',
      'W_VM': '受ARM控制的轮电机供电', 'H_VM': '受ARM控制的头舵机供电',
      'W_DUMP_D': '轮制动MOS漏极；外置电阻另一端接W_VM',
      'H_DUMP_D': '头制动MOS漏极；外置电阻另一端接H_VM',
      'W_BUS': '两轮共用半双工数据', 'S288_BUS': '两轮共用半双工数据',
      'H_BUS': '双头舵机共用半双工数据', 'HEAD_BUS': '双头舵机共用半双工数据',
      'ARM_Q': '运动硬件锁存的执行器使能', 'FAULT_N': '低有效电源故障，清除ARM',
      'CHG_N': '低有效充电/托架禁驱信号', 'BAT_ADC': '电池分压采样', 'BAT_ADC_IN': '电池分压采样入板',
      'WHEEL_ADC': '轮母线分压采样', 'WHEEL_ADC_IN': '轮母线分压采样入板',
      'CURRENT_ADC': '电池分流电流检测输出', 'CURRENT_ADC_IN': '电池电流采样入板',
      'CAM_RX': 'STM PC6 TX经U4/R9到CAM GPIO44 RX', 'CAM_TX': 'CAM GPIO43 TX经U4到STM PC7 RX',
      'CAM_3V3': '来自CAM J11.3，仅供U4 VCCB；不并联运动3.3V',
      'USER_KEY_N': 'PC13维护输入，短接GND有效，非RESET',
      'LOOP_3V3': '运动3.3V经限流电阻送往物理许可环路',
      'CLR_N': '硬件锁存清除端；断开许可环路将撤销ARM',
      'MASTER_RETURN': '经后板开关接地控制Q90，非大电流回线',
      'VBUS_RAW': 'USB保险前VBUS；仅供定义后的检测分支',
      'VBUS_FUSED': '后板保险后VBUS，送外部PD/充电器功率输入',
      'VBUS_CHARGE': 'USB保险前VBUS存在检测，经板内电阻驱动Q50',
      'CC1': 'Type-C CC1，外部受电端提供独立Rd/协商',
      'CC2': 'Type-C CC2，外部受电端提供独立Rd/协商',
      'M5_EN': '运动5V降压EN；正常开路，维护拉低关闭',
      'C5_EN': '交互5V降压EN；正常开路，维护拉低关闭',
      '+5V_MOTION': '电源J17输出/运动J1输入，模块本地生成3.3V',
      '+5V_CAM': 'CAM稳压5V供电；不用CAM BAT口',
      '+3V3': '运动MCU本地3.3V，供IMU及电源板控制域',
    }.get(net)
    if not text:
        text = {'SCK':'SPI时钟，运动主机输出','MOSI':'SPI数据，运动主机输出',
                'MISO':'SPI数据，IMU输出','CS':'SPI片选，低有效','CS_N':'SPI片选，低有效',
                'DRDY':'IMU数据就绪，IMU输出'}.get(net.removeprefix('IMU_'),net)
    if net in ['GND', 'NC']: direction = '参考地' if net == 'GND' else '不连接'
    elif ref in ['SW1', 'JP60', 'JP70']: direction = '触点/维护'
    elif net.endswith('BUS'): direction = '双向数据'
    elif kind == 'motion':
        direction = '输入' if net in ['+5V_MOTION','CAM_TX','CAM_3V3','IMU_MISO','IMU_DRDY','FAULT_N','CHG_N','BAT_ADC_IN','WHEEL_ADC_IN','CURRENT_ADC_IN','USER_KEY_N','CLR_N'] else '输出'
    elif kind == 'imu': direction = '输出' if net in ['MISO','DRDY'] else '输入'
    elif kind == 'power':
        direction = '输入' if ref in ['J1','J3','J5','J16'] or net in ['+3V3','ARM_Q'] else '低有效禁驱节点' if net=='CHG_N' else '控制回路' if net=='MASTER_RETURN' else '输出'
    else: direction = '接口透传/触点'
    return text, direction


def connector_info(mpn, ref, count, side):
    if '-PH-' in mpn:
        return f'JST PH {count}P / 2.00mm', f'PHR-{count}', 'SPH-002T-P0.5S，线径/绝缘外径按厂商', ('侧向插入' if mpn.startswith('S') else '垂直插入')
    if '-XH-' in mpn:
        return f'JST XH {count}P / 2.50mm', f'XHP-{count}（同系列对插待实物核）', '具体端子料号按线规确认', '垂直插入'
    if 'XT30' in mpn:
        return 'AMASS XT30 2P', 'AMASS XT30配对母线端（精确型号待确认）', '焊接杯型线端，型号待确认', '垂直插入'
    if ref.startswith('JP'):
        return '2.54mm 1×2排针', '正常不装短路帽', '维护时使用匹配绝缘短路帽', '垂直接近'
    if ref == 'USB1': return 'USB Type-C 16电接点+外壳', 'USB-C插头', '成品USB线', '板边水平插入'
    return 'DPDT双刀滑动开关', '板载，不接线', '无', '触点组合已定义，拨杆方向待测'


def source_extract():
    expected = load(H/'reviews/P5R6_and_width_external_20260925/verification.json')['source_inputs']
    for block in expected.values():
        for name, digest in block.items(): assert sha(ROOT/name)==digest, ('current source changed',name)
    bom = {(r['board'],r['ref']):r for r in readcsv(H/'layout_P5R6/assembly_parts_with_mpn.csv')}
    oldpins = readcsv(H/'layout_P5R6/connector_pinmap.csv')
    oldmap = {(r['board'],r['reference'],r['pin']):r['net'] for r in oldpins}
    ports, pins, tests, raw, sourcehash = [], [], [], {}, {}
    for kind, name in NAME.items():
        directory=H/'kicad'/name; pcb=directory/(name+'.kicad_pcb'); b=k.LoadBoard(str(pcb))
        for ext in ['.kicad_pcb','.kicad_sch','.kicad_pro','.kicad_dru']:
            p=directory/(name+ext); sourcehash[str(p.relative_to(ROOT))]=sha(p)
        netlist=H/'layout_P5R6/reports'/kind/'netlist.xml'
        sourcehash[str(netlist.relative_to(ROOT))]=sha(netlist)
        xml = ET.parse(netlist).getroot()
        schpins = {(node.get('ref'),node.get('pin')):net.get('name') for net in xml.findall('./nets/net') for node in net.findall('node')}
        fps={f.GetReference():f for f in b.GetFootprints()}
        assert {r for r in fps if r.startswith(('J','USB','SW'))} == set(PURPOSE[kind])
        raw[kind]=dict(outline_mm={'power':[80,55],'motion':[70,35],'imu':[20,16],'rear':[24,25]}[kind],ports=[],holes=[])
        for ref in sorted(PURPOSE[kind],key=sortref):
            f=fps[ref]; pp=sorted(f.Pads(),key=lambda p:sortref(p.GetNumber())); groups=defaultdict(list)
            for p in pp:
                # Unnumbered mounting pads are mechanical features, not terminals.
                if p.GetNumber(): groups[p.GetNumber()].append(p)
            side='B' if f.IsFlipped() else 'F'; part=bom[(name,ref)];mpn=part['full_model']; purpose,target,note=PURPOSE[kind][ref]
            family,mate,terminal,approach=connector_info(mpn,ref,len(groups),side)
            defs=[]; rawport=dict(ref=ref,side=side,centre=xy(f.GetPosition()),pins=[])
            for pin, values in groups.items():
                nets={p.GetNetname() for p in values};assert len(nets)==1
                native_net=nets.pop(); assert oldmap[(name,ref,pin)]==native_net
                if not native_net.startswith('unconnected-'):assert schpins[(ref,pin)]==native_net,(kind,ref,pin)
                net=clean(native_net); detail,direction=pin_detail(kind,ref,pin,net)
                defs.append(f'{pin}={net}')
                positions=[xy(p.GetPosition())for p in values]
                pins.append(dict(板=LABEL[kind],接口=ref,针号=pin,信号=net,功能=detail,电压域=voltage(net),
                    相对本板方向=direction,安装面=side,板端坐标mm=json.dumps(positions),对接对象=target,
                    原生针表检查='PASS',实物='NOT_TESTED',注意=note,board_id=name,native_net=native_net))
                rawport['pins'] += [dict(number=pin,xy=p,net=net)for p in positions]
            ports.append(dict(板=LABEL[kind],接口=ref,用途=purpose,连接器=family,板座完整型号=mpn,
                针脚定义='；'.join(defs),对接对象=target,安装面=side,插入方向=approach,
                配套端壳=mate,端子=terminal,装配='DNP不装' if part.get('DNP')=='True' else '板载开关' if ref=='SW1' else '已定义，未实测',
                注意=note,board_id=name))
            raw[kind]['ports'].append(rawport)
        for ref,f in fps.items():
            if ref.startswith('TP'):
                p=list(f.Pads())[0];tests.append(dict(板=LABEL[kind],接口=ref,针号=p.GetNumber(),信号=clean(p.GetNetname()),
                  定义='5V测试点' if '5V' in p.GetNetname() else '测量参考地',用法='限流供电，先量电压；不是功率接线端子',状态='NOT_TESTED',位置mm=json.dumps(xy(p.GetPosition()))))
            if ref.startswith('H') and 'MountingHole' in f.GetFPIDAsString():raw[kind]['holes'].append(xy(f.GetPosition()))
    assert len(ports)==34
    csvout('01_端口总表.csv',ports);csvout('02_端口逐针定义.csv',pins)
    dump(OUT/'native_port_geometry.json',raw)
    return ports,pins,tests,sourcehash


def harness_rows(pins):
    pinmap={(p['board_id'],p['接口'],p['针号']):p for p in pins}
    source=load(H/'layout_P5R6/harness.json'); rows=[]
    external={
      'finished3S protected pack after6.3A external fuse':'成品3S电池/外部保险',
      '9V buck INPUT':'外部9V降压器输入','9V buck OUTPUT':'外部9V降压器输出',
      '6V buck INPUT':'外部6V降压器输入','6V buck OUTPUT':'外部6V降压器输出',
      'leftS288':'左轮S288','rightS288':'右轮S288','SCS0009 chain':'头部SCS0009链',
      'external5R6 braking resistor':'外置轮制动电阻5.6Ω','external10R braking resistor':'外置头制动电阻10Ω',
      'CAM regulated5V USB power pigtail':'CAM33700 5V USB供电尾线',
      'EXTERNAL_PD_CHARGER_UNSELECTED':'外部PD/3S充电模块（未选）',
      'maintenance cradle interlock / optional additional contact':'可选托架干接点',
      'Waveshare33700':'CAM33700',
    }
    gauge={'H01':'AWG24','H02':'AWG26–28','H03':'AWG26–28','H04':'AWG26–28','H05':'AWG26–28',
           'H06':'PH端AWG28；CAM端厂配SH尾线','H07':'AWG26–28','I01':'AWG26–28'}
    hnotes={'H01':'1→1、2→2，先确认+5V极性。','H02':'半双工数据及地，不能承担电机供电。',
      'H03':'两端第3孔均为空位，不压端子。','H04':'1–8同号，两根GND都接；不得插入运动J7。',
      'H05':'1–8同号；ADC入板网名带_IN；不得插入运动J4。',
      'H06':'1→1接CAM RX，2→2接CAM TX，不再额外交叉；3脚只供U4 VCCB。',
      'H07':'后板PH4分成两只PH2；两条回路不可混接；MASTER_RETURN可接近电池电压。',
      'H08':'J2.1为保险后功率输入，J2.5仅RAW检测；1和5不得桥接；RAW源端保护待完成。',
      'I01':'可选干接点闭合时禁驱；开路断线不能自诊断。'}
    for r in source:
        a,z=r['from_'],r['to'];hid=r['harness_id'];ap=pinmap[(a['board'],a['connector'],a['pin'])]
        assert ap['信号']==a['signal']
        is_custom=z['board'] in ALIASES
        if is_custom:
            zp=pinmap[(z['board'],z['connector'],z['pin'])];assert zp['信号']==z['signal']
        if hid=='H06':assert (z['connector'],str(z['pin']),z['signal']) in [('J11','1','CAM_RX'),('J11','2','CAM_TX'),('J11','3','CAM_3V3'),('J11','4','GND')]
        endpin=z.get('pin')
        ready='PASS' if is_custom or hid=='H06' else 'BLOCKED'
        missing='' if ready=='PASS' else '外设端子编号/插头未核定'
        if hid=='H08':ready='BLOCKED';missing='外部PD/充电方案与RAW源端保护未定'
        if hid=='I01':ready='NOT_APPLICABLE';missing='可选接点，未配置'
        wire=gauge.get(hid)
        if hid=='H08':wire='AWG24功率/共地；AWG26–28 CC/检测'
        if hid.startswith('P_'):wire='AWG22' if a['connector'] in ['J7','J8','J9','J18'] else 'AWG20'
        connector=z.get('connector') or '待确认'
        if connector.startswith('factory end'):connector='厂配端/端子待确认'
        rows.append(dict(线束=hid,起点板=LABEL[ALIASES[a['board']]],起点口=a['connector'],起点针=a['pin'],
            起点信号=a['signal'],终点板=LABEL[ALIASES[z['board']]] if is_custom else external.get(z['board'],z['board']),
            终点口=connector,终点针=str(endpin) if endpin is not None else '待确认',终点信号=z['signal'],
            线规建议=wire,长度mm=None,实装线色='',端点定义=ready,待确认项=missing,
            接线说明=hnotes.get(hid,PURPOSE['power'][a['connector']][2] if hid.startswith('P_')else''),
            通断实测='NOT_TESTED'))
    # This existing optional port was absent from the previous harness inventory.
    for pin,signal in [('1','USER_KEY_N'),('2','GND')]:
        rows.append(dict(线束='SVC01',起点板='运动板',起点口='J6',起点针=pin,起点信号=signal,
            终点板='可选机内维护按键',终点口='无源常开瞬时接点',终点针='两端无极性',终点信号='触点',
            线规建议='AWG26–28',长度mm=None,实装线色='',端点定义='NOT_APPLICABLE',待确认项='可选维护线，未配置',
            接线说明='按下短接1–2；非复位、非急停；无外壳新增按键。',通断实测='NOT_TESTED'))
    assert len(rows)==65
    csvout('03_逐针接线表.csv',rows)
    summary=[]
    groups=defaultdict(list)
    for r in rows:groups[r['线束']].append(r)
    for hid, wires in groups.items():
        endpoints=lambda prefix:' / '.join(dict.fromkeys(f"{r[prefix+'板']} {r[prefix+'口']}" for r in wires))
        summary.append(dict(线束=hid,起点=endpoints('起点'),终点=endpoints('终点'),导线段数=len(wires),
            逐针关系='；'.join(f"{r['起点口']}.{r['起点针']}→{r['终点口']}.{r['终点针']}" for r in wires),
            线规建议=wires[0]['线规建议'],长度mm=None,说明=wires[0]['接线说明']))
    csvout('04_线束汇总.csv',summary)
    return rows,summary


def maintenance(tests):
    for number,signal,note in [
        (1,'GND','调试器地，可与2脚择一'),(2,'GND','调试器地，可与1脚择一'),
        (3,'PA10 / USART1_RX','轮总线UART，不接日志串口'),(4,'PA14 / SWCLK','接调试器SWCLK'),
        (5,'PA9 / USART1_TX','轮总线UART，不接日志串口'),(6,'PA13 / SWDIO','接调试器SWDIO'),
        (7,'NRST','按调试器需要接RESET，复位会禁驱'),(8,'VDD33','仅接已确认的调试器VTref输入，禁止外部3.3V灌入')]:
        tests.append(dict(板='运动模块WeAct',接口='P5（模块本体）',针号=str(number),信号=signal,
            定义='厂商V1.1调试接口',用法=note,状态='NOT_TESTED',位置mm='见模块原厂丝印，不按承载板NC推断'))
    for kind,ref in [('power','JP60'),('power','JP70')]:
        tests.append(dict(板=LABEL[kind],接口=ref,针号='1–2',信号='EN-GND',定义='维护关闭跳线',
            用法=PURPOSE[kind][ref][2]+'；正常不装短路帽',状态='NOT_TESTED',位置mm='见端口定位图'))
    tests += [
      dict(板='CAM33700',接口='USB-C（模块本体）',针号='成品USB线',信号='USB数据/5V',定义='机内下载及日志',
           用法='托架/DISARM；先拔机器人J18供电尾线，再接主机USB',状态='NOT_TESTED',位置mm='模块板载接口'),
      dict(板='CAM33700',接口='J5',针号='1 / 2',信号='PA_OUTL+ / PA_OUTL-',定义='板载BTL功放扬声器输出',
           用法='分别接扬声器两端，均不能接GND；GH1.25-2P，实物针序/配套线待核',状态='BLOCKED',位置mm='头内CAM板'),
      dict(板='CAM33700',接口='J4 BAT',针号='不接',信号='单节锂电池接口',定义='MORI的3S方案不使用',
           用法='禁止接3S或J18的5V',状态='NOT_APPLICABLE',位置mm='头内CAM板'),
    ]
    csvout('05_维护与外设.csv',tests)
    electrical=load(ROOT/'contracts/electrical_interfaces.json')
    ffc=[]
    for r in electrical['display_ffc']['pin_number_review']:
        ffc.append(dict(CAM接口='L3',针号=str(r['pin']),CAM信号=r['cam_net'],屏幕信号=r['display_net'] or '未提供',
            定义状态='BLOCKED' if r['number_mapping_status']=='BLOCKED' else 'NOT_APPLICABLE' if r['pin']==10 else 'PASS',
            接线状态='BLOCKED',说明=r['notes']))
    csvout('06_屏幕FFC待核对.csv',ffc)
    return tests,ffc


def draw_maps(geometry):
    # Locator only: true native pad coordinates, no circuitry/3D manipulation.
    (OUT/'port_maps').mkdir(exist_ok=True)
    for kind,g in geometry.items():
        w,h=g['outline_mm'];scale=12 if kind in ['power','motion'] else 26
        margin=80;W=w*scale+2*margin;Hh=h*scale+2*margin
        body=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{Hh}" viewBox="0 0 {W} {Hh}">',
          '<rect width="100%" height="100%" fill="#f6f8fa"/>',
          f'<text x="{margin}" y="30" font-size="20" font-family="Arial,sans-serif" fill="#172b4d">{html.escape(NAME[kind])} · PORT LOCATOR · TOP COORDINATES</text>',
          f'<text x="{margin}" y="54" font-size="13" font-family="Arial,sans-serif">F = front; B = rear (dashed). This is not the cable mating view.</text>',
          f'<rect x="{margin}" y="{margin}" width="{w*scale}" height="{h*scale}" fill="white" stroke="#64748b" stroke-width="2"/>']
        tx=lambda x:margin+x*scale;ty=lambda y:margin+y*scale
        for x,y in g['holes']:body.append(f'<circle cx="{tx(x)}" cy="{ty(y)}" r="{1.1*scale}" fill="#dbe2e8" stroke="#94a3b8"/>')
        for p in g['ports']:
            pts=p['pins'];lo=[min(a['xy'][i]for a in pts)-.8 for i in [0,1]];hi=[max(a['xy'][i]for a in pts)+.8 for i in [0,1]]
            color='#2f5d8a' if p['side']=='F' else '#9a4b10';dash='' if p['side']=='F' else 'stroke-dasharray="5 3"'
            body.append(f'<rect x="{tx(lo[0])}" y="{ty(lo[1])}" width="{(hi[0]-lo[0])*scale}" height="{(hi[1]-lo[1])*scale}" fill="none" stroke="{color}" {dash}/>')
            label=f'{p["ref"]} {p["side"]}'
            body.append(f'<text x="{tx((lo[0]+hi[0])/2)}" y="{ty(lo[1])-6}" text-anchor="middle" font-size="14" font-family="Arial,sans-serif" font-weight="bold" fill="{color}">{label}</text>')
            for q in pts:
                x,y=q['xy'];first=q['number'] in ['1','A1'];r=4 if len(pts)>10 else 6
                body.append(f'<circle cx="{tx(x)}" cy="{ty(y)}" r="{r}" fill="{color if first else "#ffffff"}" stroke="{color}"/>')
                if len(pts)<=8:body.append(f'<text x="{tx(x)}" y="{ty(y)+3}" text-anchor="middle" font-size="8" font-family="Arial,sans-serif" fill="{"#fff" if first else color}">{q["number"]}</text>')
            if len(pts)>10:body.append(f'<text x="{tx(lo[0])}" y="{ty(hi[1])+14}" font-size="10" font-family="Arial,sans-serif">USB pins: see pin table</text>')
        body.append(f'<text x="{margin}" y="{Hh-25}" font-size="13" font-family="Arial,sans-serif">{w} x {h} mm · CAD pin numbering · Physical cable orientation NOT_TESTED</text></svg>')
        (OUT/'port_maps'/f'{kind}.svg').write_text('\n'.join(body))


def markdown(ports,pins,wires,summary,tests,ffc):
    def table(fields,rows):
        clean=lambda x:str(x if x is not None else '待测').replace('|','/').replace('\n','<br>')
        return '| '+' | '.join(fields)+' |\n| '+' | '.join(['---']*len(fields))+' |\n'+'\n'.join('| '+' | '.join(clean(r[f])for f in fields)+' |'for r in rows)+'\n'
    s='''# MORI 四板端口定义与接线表

文档版 **P5R6-W1 / 2026-09-25**。电源、运动、后接口为 P5R6，IMU 为 P5R4。本表以当前原生 PCB 焊盘及原理图网表为准，电路、针序、板框和现行硬件契约均未改。**端点定义核对 PASS 不等于实物接线或上电通过**；全部实物记录仍为 NOT_TESTED。

[端口总表 CSV](01_端口总表.csv) · [端口逐针 CSV](02_端口逐针定义.csv) · [逐针接线 CSV](03_逐针接线表.csv) · [线束汇总 CSV](04_线束汇总.csv) · [维护/调试 CSV](05_维护与外设.csv) · [屏幕 FFC 待核表](06_屏幕FFC待核对.csv)

[可筛选 Excel（含线长、实装线色和通断记录栏）](outputs/01a0c24f-ddc2-7f03-a9d4-d09dff26d30f/MORI_端口与接线表_P5R6.xlsx)

## 看表与认针

- 针号取自**板端连接器**，不是看线色猜测的次序。定位图统一为 KiCad 顶视坐标；`F` 前装、`B` 后装。后板 J2 与 USB1 在 B 面。线端插合面、线端进线面与板端视角会发生镜像，不能把图上的左右顺序直接用于压接。
- `1→1` 表示两个**已确认编号**相连，不保证购买的“直通线”符合该次序。装配前以板端1脚标识、厂商编号及万用表通断核对；未确认的外设端编号保持“待确认”。
- 同形插头不代表可互换。运动 J4（IMU）和 J7（电源控制）都是 PH8；电源 J19 和几个逻辑口都是 PH2，但 J19.1 关机时可接近电池电位。线束两端都应贴“板名-接口-线束号”。
- 线规为现有设计建议，仍需按具体端子、绝缘外径、长度、压降和温升核验。表内线长、实装线色留空供测量填写，没有虚构机械走线长度。两路5V是设计标称，设定计算约5.077V，不是已经测出的输出。

## 四板端口
'''
    for kind in VERSIONS:
        s+=f'\n### {LABEL[kind]} {VERSIONS[kind]}\n\n[端口定位图](port_maps/{kind}.svg)\n\n'
        s+=table(['接口','用途','连接器','针脚定义','对接对象','注意'],[p for p in ports if p['板']==LABEL[kind]])
    s+='''
## 线束连接总览

这里是接线关系汇总；可直接筛选、逐针勾对的源表为 `03_逐针接线表.csv`。现有 H01–H08、P_J*、I01 编号保留；本轮补列原先未进入线束清单的可选维护按键 SVC01，不增加外壳按钮。导线段数按两端连接关系计数；例如 H08 的 GND 分叉计为两段，不表示使用6芯插头。

'''+table(['线束','起点','终点','导线段数','逐针关系','线规建议'],summary)
    s+='''
### 后板 J3 一分二（H07）

| 后板端 | 终点 | 作用 |
|---|---|---|
| J3.1 MASTER_RETURN | 电源 J19.1 | Q90 总开关控制返回 |
| J3.2 GND | 电源 J19.2 | 开关参考地 |
| J3.3 LOOP_3V3 | 运动 J8.1 | 硬件许可环路供电 |
| J3.4 CLR_N | 运动 J8.2 | 硬件锁存清除 |

SW1 的电气 ON 为 **1–2、4–5 同时闭合**。它只开关控制电流，电池负载由 Q90 切断。OFF 会失去平衡，必须托架支撑；重新 ON 不等于自动 ARM。真实拨杆哪边为 ON 仍需通断测量，不能按图中左右猜。

### CAM UART（H06）

| 运动板 J5 | CAM33700 J11 | 实际方向 |
|---|---|---|
| 1 CAM_RX | 1 / GPIO44 RX | STM PC6 TX → U4/R9 → CAM RX |
| 2 CAM_TX | 2 / GPIO43 TX | CAM TX → U4 → STM PC7 RX |
| 3 CAM_3V3 | 3 / 3V3 | CAM 本地3.3V → U4 VCCB，仅作转换器电源 |
| 4 GND | 4 / GND | 共同参考地 |

按 **1→1、2→2、3→3、4→4**，不再次交叉。CAM J11 为 SH1.0-4P，运动端为 PH2.0-4P，需专用转接线；3脚不能与运动板另一稳压器输出并联。GPIO43/44 与 TF 复用，首轮不装TF、不初始化SD。CAM侧插头实际方向与供电行为尚未台架验证。

### 后板 J2 充电/检测分支（H08，尚不能据此给电池充电）

J2.1 VBUS_FUSED、J2.2 GND、J2.3 CC1、J2.4 CC2 送往**未选定的外部受电/充电模块**；J2.5 VBUS_RAW 分到电源 J16.1，共地分到 J16.2。J2.2 需在合格分叉点分线，不能擅自在只允许一根导线的端子里压入两根。

**J2.1 和 J2.5 不得桥接；RAW细检测线不可承担充电电流。** 端点的逻辑对应已定义，但 RAW 源端短路保护、PD 输入电压/限流、两个CC终端及3S CC/CV、成品电池专用充电端尚未确认，H08 保持 BLOCKED。后接口板与电源板都不是已完成资格确认的3S充电器；CAM的单节BAT口不接3S。充电必须放托架并禁自由移动。

### 外部9V/6V与执行器

电源 J2→9V降压器 VIN，降压器 VOUT→J3；J4→6V降压器 VIN，VOUT→J5。既有工程参考分别为 Pololu D36V50F9 #4094 与 D24V22F6 #2859，具体所购物版本的端子位置、使能接法、负载与低电压能力仍需确认。**本表不按照片猜外设针号，也不把 J2/J3 或 J4/J5 直接短接。**

电源 J7/J8 分别供左右 S288；J9 供两只 SCS0009 的独立头总线链。S288 ID 0/1、头舵机 ID 1/2 为现有建议，尚未逐只写入/核验。轮和头是两条不同半双工总线，不能互短；实际TTL阈值未验证。电机电流只走电源板功率接口，不经过运动板数据口。

J11 跨接轮5.6Ω制动电阻，J12 跨接头10Ω制动电阻，两者 **1脚均是开关漏极，不是GND**。电阻的脉冲功率、散热、固定与绝缘保持未验证。

## 维护、测试点与模块外设

'''+table(['板','接口','针号','信号','定义','用法','状态'],tests)
    s+='''
WeAct P5 编号依据原厂 V1.1 图；模块自身连接与承载板未另接的焊盘要分开看。承载板 U100.E1/E2/E3/E4/E5/E6/E8 标为未另接，不表示厂商模块P5上没有这些信号。优先SWD；不把PA9/PA10作为运行日志口，因为它们已用于轮驱。

CAM J5 为板载功放BTL两线输出，两个端子都不能接地。用户后续已选择的 FS4545DB0450-H25-R01 是4Ω/5W单元；5W是单元额定，不是CAM实际输出功率。硬件旧BOM仍写“4Ω3W待选”属于待同步资料，本轮不据此更改功放/线序。相机与麦克风均在CAM板上，不新增独立摄像头/麦克风线束。

屏幕由 CAM L3 的18P/0.5mm FFC连接，不能与PH线束混用。现有接口审查中第10脚TE在CAM侧未接，16–18脚屏侧定义不明，FFC接触面和实物连续性未验证，仍不批准直接插接。详细待核对表：

'''+table(['针号','CAM信号','屏幕信号','定义状态','接线状态'],ffc)
    s+='''
## 装配前核对顺序

1. 断开电池/USB，给每条线两端贴线束号与板端接口名；逐芯核对针号、空位、极性和无邻针短路，填写实装线色和线长。
2. 先核 H07 开关分叉及 OFF/ON 两组触点，再核 H01/H04/H05/H06；H03 第3孔不压端子。记录仍为 NOT_TESTED，不能预填通过。
3. 按既有测试计划用限流电源验证逻辑轨，保持执行器断开；充电模块/电池/RAW保护未闭合前不做充电接线。
4. 单外设、悬空单电机及后续台架测试沿用 [P5R6测试计划](../layout_P5R6/test_plan.md)。任何开关OFF、运动复位或JP60关闭都可能失去平衡，需要外部支撑。

本轮只整理文档。PCB/原理图/契约/固件未改，未下单或产生新的实测数据。导出源哈希与逐针检查见 [verification.json](verification.json)。
'''
    (OUT/'README.md').write_text(s)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    ports,pins,tests,sources=source_extract()
    wires,summary=harness_rows(pins)
    tests,ffc=maintenance(tests)
    draw_maps(load(OUT/'native_port_geometry.json'))
    markdown(ports,pins,wires,summary,tests,ffc)
    dump(OUT/'workbook_data.json',dict(revision=REV,ports=ports,pins=pins,wires=wires,harnesses=summary,maintenance=tests,ffc=ffc))
    for rel,digest in sources.items():assert sha(ROOT/rel)==digest
    sourcefiles=['contracts/electrical_interfaces.json','contracts/components.json','hardware/v1_2/layout_P5R6/harness.json',
      'hardware/v1_2/layout_P5R6/assembly_parts_with_mpn.csv','hardware/v1_2/layout_P5R6/connector_pinmap.csv',
      'hardware/v1_2/sources/CAM_schematic.pdf','hardware/v1_2/sources/weact_f4/WeAct-STM32F4_64PIN-CoreBoard_V11 SchDoc.pdf']
    sources.update({f:sha(ROOT/f)for f in sourcefiles})
    dump(OUT/'verification.json',dict(document_revision=REV,status='PASS',scope='Native port/SCH net mapping and preserved harness endpoint definitions only',
       custom_ports=len(ports),unique_numbered_port_pins=len(pins),source_harness_wires=63,documented_wires=len(wires),
       optional_service_wires_added=2,harness_groups=len(summary),source_sha256=sources,
       CAD_changed=False,contracts_changed=False,firmware_changed=False,physical_tests='NOT_TESTED',
       blockers=['Peripheral plug/pin metrology','H08 external PD/3S and RAW source protection','FFC reserved pins/contact orientation',
                 'Actual cable lengths/crimps/drop/temperature','Mechanical speaker selection not yet reflected in legacy component BOM'],
       historical_metadata='S3/P2 textual identifiers in older pinmap and contract notes are not used as current board names'))
    print(json.dumps(dict(ports=len(ports),pins=len(pins),wires=len(wires),harnesses=len(summary),status='PASS')))


if __name__=='__main__':main()

"""Finalize scoped motion prototype metadata after routes, then native checks."""
from update_native_P5R7 import *
from body_keepouts_P3R1 import rectangle

name,d,p=paths('motion');b=k.LoadBoard(str(p))
for z in list(b.Zones()):
    if z.GetZoneName().startswith(('P5R7_E_FULL_','P5R7_LONG_FULL_')):b.Delete(z)
rule='\n# P5R7 E socket: only the connected pin may use its outward escape corridor\n'
for layer in [k.F_Cu,k.B_Cu]:
    z=k.ZONE(b);z.SetIsRuleArea(True);z.SetLayer(layer)
    area='P5R7_E_FULL_'+b.GetLayerName(layer);z.SetZoneName(area)
    z.SetDoNotAllowTracks(False);z.SetDoNotAllowVias(False);z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False);z.SetDoNotAllowZoneFills(False)
    z.Outline().BooleanAdd(rectangle([33.66,17.76,38.74,28.42]));b.Add(z)
    rule+='(rule '+json.dumps('P5R7 E socket unrelated routes '+b.GetLayerName(layer))+'\n'
    rule+=' (condition '+json.dumps("A.intersectsArea('"+area+"') && A.NetName != '/NRST'")+')\n (constraint disallow track via)\n)\n'
u100=next(f for f in b.GetFootprints()if f.GetReference()=='U100')
for group,box in [('AC',[5.85,28.93,44.45,34.01]),('BD',[5.85,.99,44.45,6.07])]:
    own=sorted({q.GetNetname()for q in u100.Pads()if q.GetNumber()[0]in group and q.GetNetname()})
    for layer in [k.F_Cu,k.B_Cu]:
        z=k.ZONE(b);z.SetIsRuleArea(True);z.SetLayer(layer)
        area='P5R7_LONG_FULL_'+group+'_'+b.GetLayerName(layer);z.SetZoneName(area)
        z.SetDoNotAllowTracks(False);z.SetDoNotAllowVias(False);z.SetDoNotAllowPads(False)
        z.SetDoNotAllowFootprints(False);z.SetDoNotAllowZoneFills(False)
        z.Outline().BooleanAdd(rectangle(box));b.Add(z)
        condition="A.intersectsArea('"+area+"')"+''.join(" && A.NetName != '"+n+"'"for n in own)
        rule+='(rule '+json.dumps('P5R7 '+group+' socket foreign nets '+b.GetLayerName(layer))+'\n (condition '+json.dumps(condition)+')\n (constraint disallow track via)\n)\n'
oldname,oldd,_=paths('motion','P5R6')
(d/(name+'.kicad_dru')).write_text((oldd/(oldname+'.kicad_dru')).read_text().rstrip()+'\n'+rule)
b.GetTitleBlock().SetComment(1,'Actual socket housing rules; own-pin escapes reviewed separately; no inner signal tracks')
b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
sch=d/(name+'.kicad_sch')
sl=d/'schematic_layout.json'
if sl.exists():
    j=json.loads(sl.read_text());j.update(project=name,schematic_sha256=sha(sch));dump(sl,j)
for lib in d.rglob('*.kicad_sym'):
    text=lib.read_text().replace('MORI_Custom:WeAct_F4_64Pin_V11"','MORI_Custom:WeAct_F4_64Pin_V11_ECorrected_P5R7"');lib.write_text(text)
conn=d/'connectivity.json'
conn.write_text(conn.read_text().replace('MORI_Custom:WeAct_F4_64Pin_V11"','MORI_Custom:WeAct_F4_64Pin_V11_ECorrected_P5R7"').replace(oldname,name))
with (d/'assembly_bom.csv').open(encoding='utf-8-sig',newline='')as h:rows=list(csv.DictReader(h))
for row in rows:
    if row['ref']=='U100':
        row['footprint']='MORI_Custom:WeAct_F4_64Pin_V11_ECorrected_P5R7'
        row['note']='A=P1 B=P2 C=P3 D=P4 E=P5. Component side UP; all male pins DOWN from core underside. E pads shifted native X+2.54mm. Only E7 NRST is connected on carrier; other E pins NC on carrier. E8 is core3V3, not a carrier supply input. Candidate female sockets 61303021821x2 +61300821821; straight E male61300821121. Stack/mating/retention NOT_TESTED; see formal P5R7 handoff. Top SWD test access needs mechanical confirmation after changing from right-angle E header.'
with (d/'assembly_bom.csv').open('w',encoding='utf-8-sig',newline='')as h:
    w=csv.DictWriter(h,list(rows[0]));w.writeheader();w.writerows(rows)
dump(d/'layout_notes.json',{'revision':'P5R7-E','circuit_revision':'V1.2-H0.5-P5',
    'scope':'Correct E eight-hole array and routing for approved component-up/downward-pin core; R19 rotation and R9 3.25mm move clear local channels. Pin assignments and outline unchanged.',
    'mechanical_handoff':'../../handoff/mechanical_P5R7.json','review':'../../reviews/weact_E_J3_20260930/README.md',
    'physical_tests':'NOT_TESTED','manufacturing_release':False})
(d/'README.md').write_text('''# MORI motion P5R7 — WeAct 插合修正原型

WeAct 元件面朝上，A–E 全部排针从核心板背面向下；载板 A–D 孔位与所有针号/网络分配保持。E 的 8 个孔相对 P5R6 整体 X+2.54 mm，Y 不变；新版项目使用独立修正版封装。载板仍只连接 E7/NRST，E 其余孔未接入载板电路。无需另接复位飞线。

|孔|原生 X mm|原生 Y mm|核心板信号|载板连接|
|---|---:|---:|---|---|
|E1|34.93|19.28|GND|NC|
|E2|37.47|19.28|GND|NC|
|E3|34.93|21.82|PA10|NC|
|E4|37.47|21.82|PA14/SWCLK|NC|
|E5|34.93|24.36|PA9|NC|
|E6|37.47|24.36|PA13/SWDIO|NC|
|E7|34.93|26.90|NRST|NRST → D1.1|
|E8|37.47|26.90|3V3|NC|

排母候选为 Würth 61303021821×2、61300821821×1；E 向下直针候选为 61300821121。排母本体高8.5 mm、焊脚长3.1 mm来自厂家图；完整插合高度、接触插深与保持力未验证。核心板的原厂 STEP 含 E 弯针，不能只旋转整个模型就当作上述装配。机械需替换排针装配姿态，并复核核心板上方空间、上下焊脚、维护/插拔路径。优先采购未焊针版本或要求按确认方向装配；不要把已焊弯针版本当作直接插合件。

70×35 mm 板框和安装孔保持。R19 从 (33,16) mm、−90° 改为 (32,16.575) mm、0°；R9 保持方向，下移3.25 mm至 (45,17) mm，打开中部走线/换层通道；其余器件位置保持。E 排母的实际本体投影另设两面布线约束，只有 E7 自身的直向逃线通道；没有 GND/电源的通用豁免。相关复位、反馈、按键、状态和 IMU 信号局部重布；另按实际 A–D 排母投影调整保留的 S288 总线及采样信号，滤波元件、接口功能和供电拓扑保持；新线0.20 mm，新过孔0.80/0.30 mm。原 P5R6 和原设计规则完整保留；新增规则限制 E 和 A–D 排母下的非自身走线；自身引脚逃线另作逐条复核。

PROTOTYPE / 实物 NOT_TESTED。完整原生检查、局部走线审查、68针位置表及新裸板 STEP 见 [本次交接记录](../../reviews/weact_E_J3_20260930/README.md)。机械空间仍需按正确朝向重新集成验证，没有下单或生产释放。
''')
(d/(name+'.kicad_pro')).write_text((oldd/(oldname+'.kicad_pro')).read_text().replace(oldname,name).replace('V1.2-H0.5-P5R6','V1.2-H0.5-P5R7'))
checks('motion','released')

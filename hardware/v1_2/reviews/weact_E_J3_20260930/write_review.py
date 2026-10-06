# -*- coding: utf-8 -*-
"""Write the handoff narrative only after both native verifications pass."""
from pathlib import Path
import json

HERE=Path(__file__).resolve().parent
v={kind:json.loads((HERE/'reports'/kind/'verification.json').read_text())for kind in ['motion','rear']}
assert all(x['status']=='PASS' for x in v.values())
assert all(not x['ignored_checks'] for x in v.values())
text='''# P5R7：WeAct E 插合与后板 J3 修正

2026-10-01 发布，2026-09-30 开始核对。仅完成本次第 7 项硬件接口修正，状态为 **PROTOTYPE / 实物 NOT_TESTED**。当前组合是运动板 P5R7、后板 P5R7、电源板 P5R6、IMU P5R4。原 P5R6 工程及机械源文件未被本任务修改。

用户已确认：**WeAct 核心板元件面朝上，所有公排针从核心板背面向下；E 使用直针并直接插合，不再依赖复位飞线。** 确认记录见 [user_decisions.json](user_decisions.json)。

## 交付入口

- [运动板原生工程](../../kicad/MORI_motion_P5R7/MORI_motion_P5R7.kicad_pro) · [PCB](../../kicad/MORI_motion_P5R7/MORI_motion_P5R7.kicad_pcb) · [原理图](../../kicad/MORI_motion_P5R7/MORI_motion_P5R7.kicad_sch)
- [后板原生工程](../../kicad/MORI_rear_P5R7/MORI_rear_P5R7.kicad_pro) · [PCB](../../kicad/MORI_rear_P5R7/MORI_rear_P5R7.kicad_pcb) · [原理图](../../kicad/MORI_rear_P5R7/MORI_rear_P5R7.kicad_sch)
- [正式机械交接 JSON](../../handoff/mechanical_P5R7.json) · [68 针位置核对表](weact_68_pin_alignment.csv) · [新端口逐针坐标](connector_pinmap_P5R7.csv) · [接线增补](../../wiring_P5R7/README.md)
- [运动板检查](reports/motion/verification.json) · [后板检查](reports/rear/verification.json) · [厂家资料、文件哈希和访问日期](source_index.json)

## WeAct 改了什么

原机械候选把整块核心板翻到了元件面朝下。孔集合虽能重合，针号不匹配：厂家 P1.1/VB 会落到载板 B2/GND。该朝向不能使用。厂家外形图、原理图及 STEP 均已交叉核对；[核对脚本](check_weact_alignment.py)及[结果](weact_alignment_audit.json)保留。

载板 A–D 的原生孔位、针号和电气分配保持。E 八孔相对 P5R6 整体 **X +2.54 mm**、Y 不变；板框仍为 **70×35×1.6 mm**，安装孔保持。使用独立修正版封装，库文件、原理图与板内封装一致。

|E 针|原生 X mm|原生 Y mm|核心板信号|载板连接|
|---|---:|---:|---|---|
|1|34.93|19.28|GND|NC|
|2|37.47|19.28|GND|NC|
|3|34.93|21.82|PA10|NC|
|4|37.47|21.82|PA14 / SWCLK|NC|
|5|34.93|24.36|PA9|NC|
|6|37.47|24.36|PA13 / SWDIO|NC|
|7|34.93|26.90|NRST|NRST → D1.1|
|8|37.47|26.90|3V3|NC|

NC 指载板没有接该孔，核心板上对应功能仍存在。E8 不作为载板电源输入。68 针名义坐标与厂商 STEP 的最大残差约 0.00372 mm，是模型/标称坐标核对结果，不是实测装配精度。

R19 改为原生 (32,16.575) mm、0°，通过旋转与局部移动打开 E 周边通道。R9 保持方向，下移3.25 mm至 (45,17) mm，并重布 CAM_RX_BUF/CAM_RX 两段，打开中部通道；HEAD_BUS 的邻近长段移至 Y=14.55 mm，CLR_N 长段移至 Y=16.00 mm，并缩短 CAM_TX 的换层路径，为实际过孔及净距留空间。其余元器件位姿保持。相关 NRST、CLR、ARM 反馈、按键、充电状态 CHG_N 与 IMU 信号局部重布，原理图拓扑及 GPIO 分配不变。新增信号线为 0.20 mm、过孔为 0.80/0.30 mm；大电流回路、供电拓扑和 ADC 滤波元件保持。CHG_N 的原换层点挡住新的 SPI 通道，因此仅重排该状态信号的局部路径，充电控制和电气定义保持。按真实 A–D 长排母投影检查后，S288 总线、电池/轮/电流三路采样及充电状态的旧跨排母路径也纳入重排；相邻 FAULT_N 外部状态支线一并重排，为 S288 留出短而连续的上方通道，故障信号逻辑与引脚不变；三路原始采样线从 J7 到原滤波电阻重新布线，滤波电阻、电容及分压/采样定义保持。局部 3.3 V 过孔由 (10.7442,6.1468) 移至 (10.5,6.6) mm，0.20 mm 支线随之缩短，连接目标不变；新增一个 (12.5,8.5) mm 地缝合过孔，连接被新走线分隔的地铜。

原 KiCad 项目映射的 R13 禁止内层信号线，最终版仍遵守。内层试排被拒绝，历史 `inner_clr` 报告中的四项 R13 错误不属于最终交付。原规则保留，新增 E 及 A–D 排母本体投影约束；J7 的 3–7 号端子增加了各自向南短直线逃出的允许通道，实际最终走线为 3/5/7 号向南、4/6 号向北，完整本体的非自身网络限制仍然有效；只有 E7 自身可使用直向逃线通道。两面的非自身走线不能穿过 E 排母投影。抬高核心板下的载板走线仍属于既有模块承载架构，不应把它描述为全板所有器件投影下完全无铜。

## J3 改了什么

JST **B4B-PH-K-S(LF)(SN)** 配 **PHR-4 / SPH-002T-P0.5S** 保持。J3 改为 **B.Cu、180°**，孔排原生 Y +1.70 mm；1 号孔 (14.45,21.20) mm。原生顶视图从左到右为 **4、3、2、1**，线束必须按针号确认。后板仍为 **24×25×1.6 mm**，不是 26 mm 高。

|针|网络|对端|
|---|---|---|
|1|MASTER_RETURN|电源板 J19.1|
|2|GND|电源板 J19.2|
|3|LOOP_3V3|运动板 J8.1|
|4|CLR_N|运动板 J8.2|

三根信号在外层局部重布。按 JST 本体 9.9×4.5 mm 检查，不把 Fab 的 1 脚标记算成塑料外壳。J3 自身引脚只保留向外逃线；移走两个被新本体覆盖的冗余地缝合过孔，J3.2 通孔仍连接地平面。USB、CC、保护器件、开关和其他接口没有改动。

**旧 P5R6 板不能只翻面焊一个插座就当成 P5R7。** 新版编号孔位、网络落点和局部布线均已调整。

## 检查范围与结果

|检查|运动 P5R7|后板 P5R7|
|---|---:|---:|
|KiCad 10.0.6 ERC|0|0|
|KiCad 10.0.6 DRC，全严重度、全部走线错误|0|0|
|未连线|0|0|
|原理图 / PCB 一致性问题|0|0|
|忽略项|0|0|
|新增短碎线 / 回折等样式候选|0|0|

逐元件投影检查和逐线库存保留在各板 `reports` 中；这不是仅靠 DRC 的外观结论。电源、IMU 的旧检查报告作为未改源的历史证据，本次未重跑。ERC/DRC 不验证插合、振动、热、EMC、电池安全或平衡能力。

J3 对冻结的 `socket_candidate.blend` 做了连接器、插头、连续向下 12 mm 拔出路径和向上保守焊尾包络筛查，均无相交候选；详见 [几何结果](j3_geometry_screen.json)。该检查未包含正确朝向核心板的新 Z 堆叠、当前整机全量集成、真实弯线和手指操作，不能代替机械最终验收。

导出的 STEP 是带新孔位的**裸板**，另有明确标注的后板加 J3 参考模型。没有把缺失的全部器件模型假装成完整装配 STEP，没有导出制造文件或下单。

## 机械接收时必须复核

排母目录候选为 Würth **61303021821×2** 和 **61300821821×1**；E 直公针候选为 **61300821121×1**。厂家图明确排母本体高 8.5 mm、焊尾 3.1 mm；型号已识别，国内报价、供货和实物均未确认。A–D 随核心板供货的公针版本也待确认，不宣称采购 BOM 已闭合。

11.04 mm 仅为 8.5 mm 排母本体加 2.54 mm 公针塑壳的候选面间距。公母针接触插深、板厚/焊接/公差和保持力仍需验证。不要沿用旧翻面模型的 Z 坐标；正式交接的核心板 Z 变换特意留空。

1. 按元件面朝上重新集成核心板，单独调整各组排针；厂家 STEP 自带 E 弯针，不可只旋转整板替代直针装配。
2. 验证核心板上方 USB、BOOT/RESET 和元件净空，排母焊尾与载板背面器件/结构净空。
3. 复核 A–E 的逐针对应、实际接触插深、插拔路径和固定方式。
4. E 向下后，原顶部弯针 SWD 接法不能直接沿用；需保留可操作的机内 SWD / 复位维护访问。
5. 接收 J3 的 B 面和新孔坐标，复核其向下插拔及真实线束弯折空间。

物理急停/断电实施及已取消外露 SW1 的整机接口属于另一项未闭合事项；本次没有替它作完成声明。所有上电、温升、插合、振动试验均为 NOT_TESTED。

## 重跑检查

原生命令、工具输出和输入哈希分别保存在 `reports/motion/released/commands.json` 与 `reports/rear/released/commands.json`。从项目根运行：

```sh
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 hardware/v1_2/reviews/weact_E_J3_20260930/verify_motion.py
```

该命令复核已存原生报告的输入哈希，并重新检查拓扑、封装坐标和走线，导出审阅图与裸板 STEP。要重新执行 ERC/DRC，使用上述 `commands.json` 中记录的完整命令。历史试排脚本和 checkpoint 为诊断证据；最终入口为本页链接的 P5R7 原生工程及正式交接 JSON。
'''
(HERE/'README.md').write_text(text)
print('Wrote verified review narrative.')

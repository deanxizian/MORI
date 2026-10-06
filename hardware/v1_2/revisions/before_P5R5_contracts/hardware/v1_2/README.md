# MORI V1.2 硬件工程 · P5R4 契约

当前 **后接口、IMU为P5R4；运动、电源仍为P5R3**。全部为PROTOTYPE，实物NOT_TESTED；电路与GPIO仍沿用V1.2-H0.5-P5。原版本均保留。

本轮落实后两板审查：CC2先保护后输出、D3接地、D1/C1重排、IMU VDD到真实电源地、专用锡膏与轴标。[前后图面](layout_P5R4/index.html) · [修改说明](layout_P5R4/README.md) · [逐项审查](layout_P5R4/review_disposition.md) · [检查证据](layout_P5R4/reports/verification.json)。

| 当前原生工程 | 尺寸 / 铜层 | 本轮 |
|---|---|---|
| [运动承载板 P5R3](kicad/MORI_motion_P5R3/MORI_motion_P5R3.kicad_pro) | 70×35×1.6mm / 4 | 保留原检查与设计 |
| [IMU板 P5R4](kicad/MORI_imu_P5R4/MORI_imu_P5R4.kicad_pro) | 20×16×1.6mm / 2 | 去耦摆位/走线、Paste、轴标 |
| [电源板 P5R3](kicad/MORI_power_P5R3/MORI_power_P5R3.kicad_pro) | 80×55×1.6mm / 4 | 保留前轮审查修正 |
| [Type-C／开关板 P5R4](kicad/MORI_rear_P5R4/MORI_rear_P5R4.kicad_pro) | 24×25×1.6mm / 2 | ESD/TVS路径与局部摆位 |

P5R4两板重新填铜后的ERC/DRC/未连接/原理图差异均0，ERC/DRC无忽略检查和排除项。运动/电源P5R3的报告属于前轮检查，不冒充本次重新检查。所有板框、安装孔、固定连接器位置和针脚不变；rear D1/D3/C1与IMU C1/C2移动，记录在[真实摆位](layout_P5R4/placements.csv)和[机械交接](handoff/mechanical_P5R4.json)。没有修改机械模型或正式固件。

用户KiCad规则源保持不变；严格全部等价仍NOT_TESTED。后板CC2一个自由转角、IMU两个继承的短GND转角保留明确R14例外；本体出口投影逐项列出。不得用零DRC代替全部布线偏好、温升、EMC或装配验证。

**外接USB-PD/3S充电模块仍未选定。J2.5原始VBUS检测线仍缺源端限流，故障保护与外部模块耐压配合BLOCKED。** 后接口板不包含完整3S充电器。IMU 100µm钢网提案需贴片厂确认；没有制造释放、采购或下单。[上电计划及所缺设备](layout_P5R4/test_plan.md) · [软件边界](layout_P5R4/firmware_handoff.md)。

[主BOM](bom.csv) · [逐器件MPN](layout_P5R4/assembly_parts_with_mpn.csv) · [连接器针号](layout_P5R4/connector_pinmap.csv) · [版本化pinmap](interfaces/pinmap_V1.2-H0.5-P5R4.csv) · [版本化线束](interfaces/harness_V1.2-H0.5-P5R4.csv)。本轮未更新价格/库存或宣称预算闭合。

历史：[P5R3前两板审查修正](layout_P5R3/README.md) · [P5R2逐网复查](layout_P5R2/README.md) · [P5R1圈选修正](layout_P5R1/README.md) · [P5](layout_P5/README.md) · [P4](layout_P4/README.md)。原生PCB是布局真值，旧DSN/SES和一次性编辑脚本不能覆盖当前工程。

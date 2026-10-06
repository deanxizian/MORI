# MORI V1.2 硬件工程 · P5R3

当前四块原生PCB为 **V1.2-H0.5-P5R3 / PROTOTYPE / 实物 NOT_TESTED**。本轮核对用户P5R2审查包，修正电源采样、局部回流与功率换层，取消四板全局锡膏正扩张，并恢复后接口板5项检查、修正CC2过孔落点。

[前后对照与关键区](layout_P5R3/index.html) · [修改说明](layout_P5R3/README.md) · [逐项采纳／保留理由](layout_P5R3/review_disposition.md) · [完整检查报告](layout_P5R3/reports/verification.json)。

| 原生工程 | 尺寸 / 层数 |
|---|---|
| [运动承载板](kicad/MORI_motion_P5R3/MORI_motion_P5R3.kicad_pro) | 70×35×1.6mm / 4 |
| [IMU板](kicad/MORI_imu_P5R3/MORI_imu_P5R3.kicad_pro) | 20×16×1.6mm / 2 |
| [电源板](kicad/MORI_power_P5R3/MORI_power_P5R3.kicad_pro) | 80×55×1.6mm / 4 |
| [Type-C／电源开关板](kicad/MORI_rear_P5R3/MORI_rear_P5R3.kicad_pro) | 24×25×1.6mm / 2 |

原生 ERC / DRC / 未连接 / 原理图一致性均0，没有关闭的DRC检查或新增排除项。器件型号、电路拓扑、GPIO、板框、孔位、摆位与针序不变。运动与IMU走线不变，电源及后接口局部铜线修正详见[UUID差异清单](layout_P5R3/copper_changes.csv)。原P5R2保留。

用户KiCad规则47条完全等价仍NOT_TESTED；Paste设置是明确说明的偏离。IMU局部R14、U100架高模块和必要引脚出口等原有例外保留，不把零DRC当作全部布线偏好、温升或机械适配通过。

[主BOM](bom.csv) · [装配MPN](layout_P5R3/assembly_parts_with_mpn.csv) · [连接器针脚](layout_P5R3/connector_pinmap.csv) · [MCU pinmap](interfaces/pinmap_V1.2-H0.5-P5R3.csv) · [线束](interfaces/harness_V1.2-H0.5-P5R3.csv) · [机械交接](handoff/mechanical_P5R3.json)。本次不更新报价或库存结论。

电源架构仍按[既有电源树与接线](layout_P4/power_and_wiring.md)，后接口板不是完整3S充电器；电池／充电器／电源模块规格及价格等[未闭合项](layout_P4/实测与阻塞项.md)没有因本次修改自动解除。完整装配、发热、噪声和负载性能仍未实测。没有采购、制造下单或Gerber输出。

历史版：[P5R2全部网络复查](layout_P5R2/README.md) · [P5R1运动板圈选修正](layout_P5R1/README.md) · [P5](layout_P5/README.md) · [P4](layout_P4/README.md)。当前原生.kicad_pcb为布局真值，不要用旧DSN/SES或一次性编辑脚本覆盖。

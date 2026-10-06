# MORI V1.2 硬件工程 · P5R2

当前四块原生PCB均为 **V1.2-H0.5-P5R2 / PROTOTYPE / 实物 NOT_TESTED**。本次是全部网络和走线复查修正，电路、器件型号、GPIO、板框与安装接口不变。

[四板前后对照与逐网络查看](layout_P5R2/index.html) · [复查说明与明确例外](layout_P5R2/README.md) · [线宽及电流路径](layout_P5R2/width_review.md) · [完整检查报告](layout_P5R2/reports/verification.json)。

| 原生工程 | 尺寸 / 层数 |
|---|---|
| [运动承载板](kicad/MORI_motion_P5R2/MORI_motion_P5R2.kicad_pro) | 70×35×1.6mm / 4 |
| [IMU板](kicad/MORI_imu_P5R2/MORI_imu_P5R2.kicad_pro) | 20×16×1.6mm / 2 |
| [电源板](kicad/MORI_power_P5R2/MORI_power_P5R2.kicad_pro) | 80×55×1.6mm / 4 |
| [Type-C／电源开关板](kicad/MORI_rear_P5R2/MORI_rear_P5R2.kicad_pro) | 24×25×1.6mm / 2 |

原生 ERC / DRC / 未连接 / 原理图一致性均0，没有新增忽略项。用户KiCad规则47条完全等价仍NOT_TESTED；IMU局部R14、U100架高模块和必要引脚出口等例外明确保留，不把零DRC当作全部布线偏好、温升或机械适配通过。

[主BOM](bom.csv) · [装配MPN](layout_P5R2/assembly_parts_with_mpn.csv) · [连接器针脚](layout_P5R2/connector_pinmap.csv) · [MCU pinmap](interfaces/pinmap_V1.2-H0.5-P5R2.csv) · [线束](interfaces/harness_V1.2-H0.5-P5R2.csv) · [机械交接](handoff/mechanical_P5R2.json)。完整装配高度、插合净空、质量及温升未实测。本次不更新报价或库存结论。

电源架构仍按[既有电源树与接线](layout_P4/power_and_wiring.md)，后接口板不是完整3S充电器；电池/充电器/电源模块规格及价格等[未闭合项](layout_P4/实测与阻塞项.md)没有因布线复查自动解除。没有采购、制造下单或Gerber输出。

历史版：[P5](layout_P5/README.md) · [P5R1运动板圈选修正](layout_P5R1/README.md) · [P4](layout_P4/README.md)。当前最终原生.kicad_pcb是布局真值，不要用旧DSN/SES或一次性编辑脚本覆盖。

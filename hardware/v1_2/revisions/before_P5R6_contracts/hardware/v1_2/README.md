# MORI V1.2 硬件工程 · P5R5 契约

当前运动、电源为 **P5R5**；后接口、IMU保持 **P5R4**。全部PROTOTYPE，实物NOT_TESTED；电路与GPIO仍为V1.2-H0.5-P5。原工程保留，无制造释放。

[本轮前后对照](layout_P5R5/index.html) · [修改说明](layout_P5R5/README.md) · [逐项审查](layout_P5R5/review_disposition.md) · [实际检查](layout_P5R5/reports/verification.json) · [工程包](MORI_Motion_Power_P5R5_Reviewed_Projects.zip)。

| 当前原生工程 | 尺寸／层数 | 修改范围 |
|---|---|---|
| [运动 P5R5](kicad/MORI_motion_P5R5/MORI_motion_P5R5.kicad_pro) | 70×35×1.6mm／4 | 实际丝印、原理图T接点；铜线不变 |
| [电源 P5R5](kicad/MORI_power_P5R5/MORI_power_P5R5.kicad_pro) | 80×55×1.6mm／4 | 两路降压输入回路／反馈、局部相关走线、丝印与T接点 |
| [IMU P5R4](kicad/MORI_imu_P5R4/MORI_imu_P5R4.kicad_pro) | 20×16×1.6mm／2 | 保持前轮结果 |
| [Type-C／开关 P5R4](kicad/MORI_rear_P5R4/MORI_rear_P5R4.kicad_pro) | 24×25×1.6mm／2 | 保持前轮结果 |

两块修改板最终KiCad10.0.6的ERC／DRC／未连接／原理图差异均0，无忽略检查；P5R4两板沿用其前轮检查，源文件哈希未变。四板28组编号接口重新复核。板框、安装孔、固定连接器、器件型号和针脚不变。

降压输入电容正负端已显式连接到IC；FB长度15.05→6.28mm、9.16→6.86mm。两个隔离的In1 GND反馈返回路径是对用户R13的明确局部偏离；M5_EN两个严格0.5mm倒角例外保留。原生零DRC不代表全部规则或布线偏好等价通过。

[真实摆位](layout_P5R5/placements.csv) · [机械交接](handoff/mechanical_P5R5.json) · [主BOM](bom.csv) · [逐器件MPN](layout_P5R5/assembly_parts_with_mpn.csv) · [针号](layout_P5R5/connector_pinmap.csv) · [版本化pinmap](interfaces/pinmap_V1.2-H0.5-P5R5.csv) · [线束](interfaces/harness_V1.2-H0.5-P5R5.csv)。未改写机械或正式固件，完整装配仍BLOCKED，未更新采购价格／库存／预算。

**PD/3S外部模块未选定，后板J2.5 RAW检测线缺源端限流，温升/动态载流/开关稳定性/ESD仍未验证。** 孔铜与贴片钢网需厂家确认；现有万用表和限流电源不能替代示波器与测温工具。[实测计划](layout_P5R5/test_plan.md) · [空白记录](layout_P5R5/test_records.csv)。没有采购、制造订单、Gerber或钢网制造文件。

历史：[后接口／IMU P5R4](layout_P5R4/README.md) · [P5R3](layout_P5R3/README.md) · [P5R2](layout_P5R2/README.md) · [P5R1](layout_P5R1/README.md) · [P5](layout_P5/README.md)。原生PCB为布局真值，阶段编辑脚本不能覆盖当前工程。

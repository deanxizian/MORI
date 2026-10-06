# MORI V1.2 硬件工程 · P4

当前版本 **V1.2-H0.4-P4**：四块原生 KiCad 工程，包含后部 Type-C／物理电源开关板。信号板端改用 PH2.0，较大电流保留 XT30 和 XH2.50。GPIO及四执行器架构保持，电源增加Q90总开关并保留两路板载5V。

**PROTOTYPE；实机全部NOT_TESTED；采购与制造尚未释放。** 原生检查、当前哈希、逐器件走线复核分别有记录，不能用零DRC代替台架和完整机械验收。

| 原生工程 | 尺寸与层数 | 审阅资料 |
|---|---|---|
| [运动板](kicad/MORI_motion_P4/MORI_motion_P4.kicad_pro) | 70×35×1.6 mm，4层 | [PCB](kicad/MORI_motion_P4/MORI_motion_P4.kicad_pcb) · [原理图PDF](layout_P4/previews/MORI_motion_P4/schematic.pdf) |
| [IMU板](kicad/MORI_imu_P4/MORI_imu_P4.kicad_pro) | 20×16×1.6 mm，2层 | [PCB](kicad/MORI_imu_P4/MORI_imu_P4.kicad_pcb) · [原理图PDF](layout_P4/previews/MORI_imu_P4/schematic.pdf) |
| [电源板](kicad/MORI_power_P4/MORI_power_P4.kicad_pro) | 80×55×1.6 mm，2层 | [PCB](kicad/MORI_power_P4/MORI_power_P4.kicad_pcb) · [原理图PDF](layout_P4/previews/MORI_power_P4/schematic.pdf) |
| [后接口板](kicad/MORI_rear_P4/MORI_rear_P4.kicad_pro) | 24×25×1.6 mm，2层 | [PCB](kicad/MORI_rear_P4/MORI_rear_P4.kicad_pcb) · [原理图PDF](layout_P4/previews/MORI_rear_P4/schematic.pdf) |

[四板预览](layout_P4/previews/index.html) · [KiCad核验记录](layout_P4/reports/verification.json) · [逐器件走线审查](layout_P4/body_route_review/README.md)。四板ERC、DRC、未连接、原理图一致性均为0，忽略项为空。R14固定转角退让未全面落实，未宣称源47条规则全部合格。

[主BOM](bom.csv)已按原生位号重算；[装配MPN对应表](layout_P4/assembly_parts_with_mpn.csv)防止模块与PCB元件重复计价；[接插件目录](layout_P4/connector_catalog.csv)给出国内目录料号，价格/库存未全部确认。不要使用旧GH/SH板端购物表下单。

[电源树和接线](layout_P4/power_and_wiring.md) · [板端引脚](layout_P4/connector_pinmap.csv) · [MCU pinmap](interfaces/pinmap_V1.2-H0.4-P4.csv) · [线束表](interfaces/harness_V1.2-H0.4-P4.csv) · [机械交接](handoff/mechanical_P4.json)。后板24×25并非旧24×14占位已适配；PH插合8mm不含线弯。机械拥有的几何/接口文件未被本任务覆盖。

[新增实测及阻塞项](layout_P4/实测与阻塞项.md)列明电池、PD/充电、外接9V/6V、国内报价、结构安装及台架所需证据。后部板是充电接口，不是完整3S充电器。运行固件/设备协议验证仍由软件任务维护；没有刷机、采购或下单。

[本版电阻/过孔估算](layout_P4/calculations/interconnect_estimate.json)、[裸板质量情景](layout_P4/calculations/bare_board_mass.json)与[既有动力模型](calculations/engineering_model.py)均可复核。裸板不是完整装配质量，当前不可宣称已更新整机惯量或60分钟续航通过。

P2、S3、P3、P3R1保留为历史；前版入口已归档在revisions/before_P4_contracts/v1_2_README.md。当前最终原生.kicad_pcb是布局真值，旧DSN/SES及一次性修改脚本不得重新导入覆盖它。[复核方法](layout_P4/REPRODUCE.md)只读取/检查当前文件。

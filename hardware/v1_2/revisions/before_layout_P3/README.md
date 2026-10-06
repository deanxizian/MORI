# MORI V1.2 硬件工程 · S3原理图 / P2保留布局

2026-09-22新增 **V1.2-H0.3-S3**：[电源原理图工程](kicad/MORI_power_S3/MORI_power_S3.kicad_pro) · [12页阅读版](schematic_S3/previews/MORI_S3_Power_Schematic_Review.pdf) · [变更及计算/接线/测试](schematic_S3/README.md)。新增两路板载TPS54302 5V降压，MCU保留本地稳压，J6标为DNP。**本轮仅原理图：ERC 0、原生网表逐针一致；PCB按用户要求不动，新板框未冻结。S3与P2电源PCB尚未同步。** 运动板、IMU板及GPIO不变。

以下P2布局结果保留供追溯，不能用来证明新增S3降压电路的布局、温升或DRC。

2026-09-22。当前 PCB 为按用户 KiCad 仓库规则重新排布的 **P2**，原理图保留 **S2 功能块版**。三块板的本版 ERC、DRC、未连接、原理图一致性检查均为 0；P1 原板保留。先看 [P2 Layout 阅读版](layout_P2/previews/MORI_P2_Layout_Review.pdf) 和 [本次变更、规则例外与完整入口](layout_P2/README.md)。当前是 **PROTOTYPE / UNVALIDATED**；固定 0.5 mm 转角退让、扇出/测试点及钢网规则尚未完全闭合，完整 BOM、充电和整机装配门槛仍在，未制造放行。

主路线：**S288×2 + SCS0009×2、WeAct F412RET6 V1.1运动适配候选、微雪33700 OV3660交互板、ICM-42688-P身体IMU、微雪35079圆屏、成品3S候选**。两颗应用MCU；F413→F412的理由与软件代价见[ADR002](../../reports/decisions/ADR-HW-V1_2-002.md)。未删除第二头轴、相机、音频或反馈，不重复购买微雪板载音频和S288内置驱动。

## 原生工程与实际检查

使用KiCad CLI **10.0.6**。这三项均有可编辑的`.kicad_sch / .kicad_pcb / .kicad_pro`、本地符号/封装、实际铜线和装配子表。

原理图保留 **S2 人工编排的功能电路图**，修正过 S1 自动连线的绕行、折返和标注拥挤。运动板9个功能分区，电源板10个，IMU板2个；电源从左到右，供电在上、回流在下，比较器按两个功能画为三角符号。直接看 [P2 同版20页功能原理图](layout_P2/previews/MORI_P2_Schematic_Review.pdf)，或打开下表的原生工程。原 S2/P1 阅读版与核对记录仍保留。

**下表仅为 P2 的新检查结果**，没有沿用 P1 的通过记录。47 条源规则的映射、原工具无法等效表达的条目和实际补充几何偏差见 [P2 规则说明](layout_P2/README.md)；零 DRC 不代表所有源规则均符合。

| 原型板 | 板框mm | 原理图ERC | PCB DRC | 未连接/原理图差异 | 查看 |
|---|---|---:|---:|---:|---|
| 运动载板 | 70×35 | 0 | 0 | 0 / 0 | [原生工程](kicad/MORI_motion_P2/MORI_motion_P2.kicad_pro) · [板背面](layout_P2/previews/MORI_motion_P2/bottom.png) |
| 身体IMU板 | 20×16 | 0 | 0 | 0 / 0 | [原生工程](kicad/MORI_imu_P2/MORI_imu_P2.kicad_pro) · [板正面](layout_P2/previews/MORI_imu_P2/top.png) |
| 电源调理板 | 80×45 | 0 | 0 | 0 / 0 | [原生工程](kicad/MORI_power_P2/MORI_power_P2.kicad_pro) · [板背面](layout_P2/previews/MORI_power_P2/bottom.png) |

[P2真实检查汇总](layout_P2/reports/verification.json)记录29项 CAD/来源核对、输入哈希和规则边界；逐板目录保留 CLI argv、退出码、ERC/DRC JSON。没有增加单项忽略来清零，DRC忽略列表为空；ERC保留KiCad默认的四项关闭规则（单次全局标签、四路连接、SPICE模型、封装过滤），明列于报告。未进行SPICE验证。历史 [P1核验](reports/cad_validation.json)只对应P1。

电源板有反接/隔离、硬件锁存控制、放电电流/电压监测和轮/头两路模拟吸能，**它不是USB-C充电板**。其80×45mm板框与16mm高电解不符合原44×16×10mm电源预留，最新孔位/连接器见 [P2结构交接](handoff/mechanical_P2.json)，已读机械M1.5但未修改其文件。裸板STEP不等于完整装配模型；没有制造Gerber、下单或实物记录。

## 计算与接口

- [可读计算结果](reports/calculation_summary.md)：轻/中/重情景约0.85/1.14/1.55kg；56项延迟/饱和/反向损失条件试验；双轴头部负载、轮轴/轴承、回灌、分状态功耗与Wh续航。
- [动力脚本](calculations/engineering_model.py)、[电源容差/线宽脚本](calculations/power_integrity.py)、[完整结果](reports/engineering_model.json)。S288连续力矩未知，0.6Nm不作连续能力；2200mAh在18W平均假设下仅约55分钟，未承诺60分钟。
- [当前完整BOM](bom.csv)、[S3电源装配表](kicad/MORI_power_S3/assembly_bom.csv)、[价格门槛](reports/budget_gate.json)、[原厂来源](sources/index.json)。S3共83项，82项缺完整价格；206元仍仅为SCS两只的型号报价小计，修订/税运也待核。原[装配小料表](assembly_parts.csv)仅对应历史P1，不能用于S3装配。
- [器件真值](../../contracts/components.json)、[电气真值](../../contracts/electrical_interfaces.json)、[S3 pinmap](interfaces/pinmap_V1.2-H0.3-S3.csv)、[S3线束表](interfaces/harness_V1.2-H0.3-S3.csv)、[FFC逐针表](interfaces/display_ffc_review.csv)。MCU GPIO与DMA未因S3更改，新增项为电源输出端子。
- [电源树与状态](power_states.md)、[原理/接线/资源审查](reviews/engineering_review.md)、[上电至60分钟测试计划](test_plan.md)。所有实机项NOT_TESTED；已有仪器仅万用表、限流电源。

## 现在能并行做什么

[软件调试提示词](handoff/TASK3_SOFTWARE_P1.md)可直接交给现有软件任务，继续板型适配、编译、模拟和故障注入。[硬件与结构交接](handoff.md)给出板框、孔位、背面插头和热/线缆净空要求。本任务未覆盖机械或正式软件文件。

淘宝偏好已经记录。用户稍后补S288、33700、35079的链接与所选规格价格即可；[询价模板](procurement/淘宝询价模板.md)和[可填写表](procurement/quote_intake.csv)已备好，没有联系商家。电池/3S充电、稳压、功率器件和装配用料还需硬件及供应资料核验，不能仅凭三条链接把整个BOM改成“已确认”。

剩余事项逐项见[冲突表](reports/conflicts.csv)及[完成范围说明](reviews/closure_accountability.md)。它们包括电池/充电精确型号、国内完整成本、部分安装包络、机械重排、协议实机差异、连续力矩/波形/热与续航。预算按当前V1.2文档仍以1000元核算，未知成本未记零。

复现见[REPRODUCE](tools/REPRODUCE.md)。当前原理图检查运行`verify_S3.py`；S3契约由`publish_S3.py`和`build_reports.py`维护。不要运行`publish_P1.py`覆盖当前契约，也不要运行旧CAD全量生成器清空P1/P2铜线。历史验证脚本不证明S3电路。

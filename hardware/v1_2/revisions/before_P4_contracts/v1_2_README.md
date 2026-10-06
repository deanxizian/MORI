# MORI V1.2 硬件工程 · P3

> **2026-09-23 用户复核：布线方式 FAIL。** 已确认同层线路下穿器件，P3 未满足向外出线要求；原生零 DRC 不代表布局验收通过。本次审查未修改铜线，问题尚未修复。见[逐项审查](layout_P3/body_route_review/README.md)。


2026-09-23，当前 **V1.2-H0.3-P3**：三板重新布局与布线，电源板扩大到 **80×55 mm**，纳入 S3 两路 TPS54302 5 V 降压。运动板 70×35 mm、身体 IMU 板 20×16 mm；本轮 GPIO、针序、四执行器和双 MCU 架构未改变。

三板的本版原生 KiCad 10.0.6 **ERC、DRC、未连接、原理图差异均为 0**，DRC 忽略项为空。当前仍是 **PROTOTYPE / 实机 NOT_TESTED / 未制造放行**；源规则的固定转角、扇出/测试点和钢网等尚有未闭合项。

先看 [P3 正反面及装配预览](layout_P3/previews/index.html)、[布局变更与规则边界](layout_P3/README.md)和[真实核验结果](layout_P3/reports/verification.json)。

| 原生工程 | 板框 mm | 配套资料 |
|---|---|---|
| [运动载板 P3](kicad/MORI_motion_P3/MORI_motion_P3.kicad_pro) | 70×35 | [背面](layout_P3/previews/MORI_motion_P3/bottom.png) · [装配表](kicad/MORI_motion_P3/assembly_bom.csv) |
| [身体 IMU 板 P3](kicad/MORI_imu_P3/MORI_imu_P3.kicad_pro) | 20×16 | [正面](layout_P3/previews/MORI_imu_P3/top.png) · [装配表](kicad/MORI_imu_P3/assembly_bom.csv) |
| [电源板 P3](kicad/MORI_power_P3/MORI_power_P3.kicad_pro) | 80×55 | [正面](layout_P3/previews/MORI_power_P3/top.png) · [装配表](kicad/MORI_power_P3/assembly_bom.csv) |

所有工程均有可编辑原理图、原生 PCB、工程规则及本地符号/封装。原理图保持功能块布局。保存的 `.kicad_pcb` 是最终布线真值，DSN/SES 是过程快照，不能重导入覆盖局部修订。P2/S3 原件保留并核对了哈希。

## 当前接口、计算与验证

- [器件契约](../../contracts/components.json)、[电气契约](../../contracts/electrical_interfaces.json)、[P3 pinmap](interfaces/pinmap_V1.2-H0.3-P3.csv)、[P3 线束表](interfaces/harness_V1.2-H0.3-P3.csv)。接口与 S3 逐网逐针一致，本次不改正式固件。
- [P3 结构交接](handoff/mechanical_P3.json)给出真实板框、孔位、连接器旋转/面别及逐针位置。已读机械 M1.11；其 80×55 容量不等于 P3 完整装配通过。裸板 STEP 不包含插头、器件与线缆，机械契约保持由机械任务维护。新后部接口小板的电路属于另一项任务。
- [P3 裸板质量和铜线估算](layout_P3/reports/layout_power_estimate.json)、[可运行脚本](calculations/layout_P3_power.py)。原[动力与功耗模型](calculations/engineering_model.py)和[计算摘要](reports/calculation_summary.md)保留；新板估算尚不构成整机重心或 60 分钟续航验收。
- [主 BOM](bom.csv)、[价格门槛](reports/budget_gate.json)、[来源索引](sources/index.json)。83 行中 82 行缺完整价格，206 元仍只是型号报价小计，精确变体和税运待确认。PCB 扩板及装配未取得新报价，未知费用没有记零。
- [电源树与状态](power_states.md)、[S3 电源原理说明及计算](schematic_S3/README.md)、[测试计划](test_plan.md)。MCU 保留模块本地 3.3 V 稳压；电源板供两路 5 V。USB-C 充电、电池及外部轮/头稳压仍有采购/匹配门槛，不能将本板当成完整充电器。

主路线仍为 S288×2、SCS0009×2、WeAct F412RET6 V1.1 运动适配候选、微雪 CAM33700 OV3660、ICM-42688-P、微雪 LCD35079 及成品 3S 候选。F413→F412 的理由与软件代价见 [ADR002](../../reports/decisions/ADR-HW-V1_2-002.md)。S288 连续力矩未实测；未宣称站稳、60 分钟续航或总成本已达标。

当前可用仪器为万用表和限流电源，全部实机项 NOT_TESTED。用户没有已购器件。没有采购、下单 PCB、刷机或导出制造文件。

## 历史资料与复核

[S3 原理图阶段](schematic_S3/README.md)和[P2 布局阶段](layout_P2/README.md)保留供追溯，不作为 P3 的检查证据。旧 S3/P2 综合入口保存在 [修订快照](revisions/before_layout_P3/README.md)。历史[冲突表](reports/conflicts.csv)与[完成范围说明](reviews/closure_accountability.md)还含旧版状态，当前布局以 P3 报告为准；其中国内核价、电池/充电、实测等未闭合门槛仍有效。

按 [REPRODUCE](tools/REPRODUCE.md)复核 P3。发布硬件契约的入口为 `publish_P3.py`，表格由 `build_reports.py`投影；不能运行旧发布脚本覆盖 P3。此前的软件提示词只作历史接口说明，软件任务应读取当前版本化 pinmap 和电气契约。

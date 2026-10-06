# MORI V1.2 硬件基线 · V1.2-H0.1

更新日期：2026-09-22。已迁移主选、器件数据、电气契约、BOM、引脚与线束表，并完成首轮 G1/G2/G3 文档审查。状态 **PROTOTYPE / UNVALIDATED**；采购、上电和制造均未放行。

主选为 **S288×2 + SCS0009×2、STM32F413RGT6 运动主控、微雪33700交互板、ICM-42688-P身体IMU、微雪35079圆屏、成品3S电池候选**。STM32小板、IMU模块、电池、稳压/充电和总线接口器件尚未冻结。两颗应用MCU之外，微雪板内有CH32 I/O扩展控制器；不重复采购板载摄像头、麦克风、Codec、功放或S288内置驱动。

| 门槛 | 当前结论 | 已得到的证据 / 尚缺项 |
|---|---|---|
| G1 器件与包络 | BLOCKED | S288本体与质量、SCS旧版尺寸图、圆屏二维尺寸有原厂依据；CAM最高件包络、屏厚/净重、采购修订、电池/主控板未齐 |
| G2 国内完整成本 | BLOCKED | 30项中已记录SCS0009国内商家103元/个、有货的型号报价；采购修订/税运待核，其余主BOM缺价，总价未知。99.9元屏幕线索的品牌/SKU尚不能对应35079 |
| G3 关键接口 | BLOCKED | CAM资源/音频参考已读图，FFC主体信号已比对，S288时钟已复算；协议矛盾、实际电平、FFC方向、3S回灌仍未闭合 |
| HOST_TEST | PASS（限定） | 表格/版本/时钟检查，以及258组S288 CRC比较和6个坏帧反例实际运行；原厂C/Python的负角度/符号/量化差异已记录，不代表设备兼容通过 |
| BENCH / ROBOT | NOT_TESTED | 无实机电流、温升、平衡、视觉压力或续航记录 |
| V1.2 KiCad ERC / DRC | NOT_TESTED | KiCad CLI 10.0.6已核；新板尚未绘制，历史A0工程不是V1.2电路 |

预算按本次导入规格恢复 **≤1000元**，计划900元、余量100元。此前用户允许适度超预算的历史保留在ADR；旧海外换算/旧BOM不能代替新版国内报价。缺价不计零，也不宣称达标。

- [当前器件真值与缺失项](../../contracts/components.json)、[电气契约](../../contracts/electrical_interfaces.json)
- [完整BOM](bom.csv)、[预算结果](reports/budget_gate.json)、[来源表](sources/index.json)
- [引脚](interfaces/pinmap_V1.2-H0.1.csv)、[线束](interfaces/harness_V1.2-H0.1.csv)、[屏幕逐针表](interfaces/display_ffc_review.csv)
- [关键接口审查](reviews/interface_review.md)、[机械/软件交接](handoff.md)、[实测计划](test_plan.md)
- [电源树与状态](power_states.md)、[未闭合项](reports/conflicts.csv)、[迁移校验记录](reports/migration_validation.json)
- [未闭合原因与处理范围](reviews/closure_accountability.md)、[S288离线比对结果](reports/s288_reference_audit.json)
- [迁移决策](../../reports/decisions/ADR-HW-V1_2-001.md)、[计算结果](reports/interface_calculations.json)

可复现命令（项目根目录，Python 3标准库，无硬件I/O）：

```sh
python3 hardware/v1_2/tools/build_reports.py
python3 hardware/v1_2/calculations/interface_gate.py
python3 hardware/v1_2/calculations/audit_s288_reference.py
python3 hardware/v1_2/tools/validate_baseline.py
```

`contracts/components.json` 与 `contracts/electrical_interfaces.json` 是人工维护真值；CSV是投影。旧V1文件保留在 `hardware/v1/`，更早根目录内容为A0历史；不得从旧表给新器件接线。旧H0.3发布器已加版本保护。

用户原文件原样保存为 [MORI_SPEC_V1_2.md](../../MORI_SPEC_V1_2.md) 和 [硬件任务书](02_CODEX_HARDWARE.md)。所引用的 `AGENTS_MORI_TEMPLATE.md`、`04_HANDOFF_AND_ACCEPTANCE.md`、`REFERENCES.md` 和种子包未提供/未找到；本轮未冒称读取，不伪造原S01等来源编号。这不阻止已完成的基线迁移。

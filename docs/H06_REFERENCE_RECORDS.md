# H06 引用资料与状态边界

本页对应采购交接中引用的 **M1.54 历史容量研究**。它们没有进入主模型，不能作为 M1.55 完整线束、真实端接或带线闭壳的通过证明；正式 AWG28／PH002 与厂家 SH 尾线保持。

公开的[字段摘录](review_evidence/H06_reference_summary.json)由原报告提取，逐份记录来源路径与 SHA-256。[原始数值报告包](evidence/M1_54_H06_referenced_evidence.zip)包含 34 份未修改的报告、命令记录及入壳要求；[包清单](review_evidence/M1_55_archives.json)的 `h06-reference` 组列出每个成员与哈希。未包含完整研究脚本、二进制几何缓存或第三方原件，因此不宣称可重跑全部研究。

<a id="terminal"></a>
## 穿线容量研究

端子保护容量盒为 2.28 × 1.7 × 6.7 mm，属于未选定的几何探针。原报告在 `cam_terminal_feed/optimized_path_verify/review.json`。

四根参考线按 CAM_4 → CAM_3 → CAM_2 → CAM_1 逐根送入；检查使用机械零位及未采用的研究线径。`joined_independent_verification.json` 记录首根下段 4,168 个区间；前三根让位的独立报告分别记录 258、130、128 个区间，第三根另有 4 个 S 段抬升区间。

第四根端子路径由 `fourth_slack_enclosure/terminal_upper/review.json` 的 2,310 个上段区间和沿用的 `connected_neck_joined/rigid/review.json` 的 735 个下段区间组成，共 3,045 个。`fourth_slack_enclosure/review.json` 记录 440 个松线弯扫掠单元，`fourth_attached_continuous/review.json` 及 `fourth_independent_verification.json` 记录 4,168 个下段活动线区间。第三根暂放段的独立数值最小半径约 1.466 mm。这些几何检查没有批准具体线材，材料限制见下一节。

<a id="material"></a>
## 材料对照

`cam_terminal_feed/material_boundary/review.json` 保留了来源字段、每阶段半径及明确的 FAIL：Alpha 2841/7 的外径为 0.6096±0.0508 mm，记录的厂家弯曲要求为 10 倍外径，按最大外径需 R6.604 mm。研究路线约 R2.990／R1.466 mm，不能据此采用该材料。它是 AWG30，外径也低于现行 PH002 绝缘夹持范围；未替换正式 H06。

<a id="housing"></a>
## 入壳要求

包内 `cam_terminal_feed/housing_requirements.md` 保存完整交接，`material_boundary/receipt.json` 保存原始来源回执。用户已接受厂家压接、身体端暂不装 PHR-4 塑壳，装机后按原孔号入壳。

孔号和信号以[现行逐针接线表](../hardware/v1_2/wiring_P5R7/03_逐针接线表.csv)为准。压接后最大外形、保护方式、锁舌朝向、入壳运动、对插和完整带线闭壳仍未完成，不可下发裁线长度。

<a id="awg28"></a>
## 未采用的 AWG28 参考

`cam_AWG28_reference/independent_verification.json` 记录 Alpha ThermoThin 2628 的首根下段 1,314 个连续曲率区间和保守中心线 R4.0513 mm；没有覆盖其余三根全流程。最大外径 0.7366 mm 在 1 mm 出口中心距下仅留 0.2634 mm 表面间隙，低于 0.3 mm 目标，是余量不足，不能说实物已经相撞。

该参考需要 PH004；正式 PH002 与厂配 SH 尾线未变。整体仍为 **BLOCKED**。材料版本、厂配尾线、压接及物理装配待确认。

## 查看完整记录

从仓库根目录执行：

```sh
python tools/restore_m1_55_evidence.py --group h06-reference
```

恢复位置为 `mechanical/studies/harness_current_M1_54/` 下的两个研究目录。恢复器先检查全部目标；不同内容的现有文件不会被覆盖。无需依赖旧预览服务器或未发布的本地路径。

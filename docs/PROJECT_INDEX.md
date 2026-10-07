# 当前项目资料索引

资料基线为 M1.52／P5R7，整理日期 2026-10-07；工程仍为 PROTOTYPE / UNVALIDATED。

| 内容 | 当前入口 |
|---|---|
| PR 顺序与依赖 | [REVIEW_STACK](REVIEW_STACK.md) |
| 当前状态与未完成项 | [CURRENT_STATUS](CURRENT_STATUS.md) |
| 规格与规则 | [V1.2](../MORI_SPEC_V1_2.md) · [AGENTS](../AGENTS.md) |
| 机械唯一尺寸源 | [geometry.json](../config/geometry.json) · [机械接口](../contracts/mechanical_interfaces.json) |
| 硬件选型与电气契约 | [components](../contracts/components.json) · [electrical_interfaces](../contracts/electrical_interfaces.json) |
| 原生运动载板 | [MORI_motion_P5R7.zip](../hardware/v1_2/native_projects/MORI_motion_P5R7.zip) |
| 原生电源板 | [MORI_power_P5R6.zip](../hardware/v1_2/native_projects/MORI_power_P5R6.zip) |
| 原生 IMU 板 | [MORI_imu_P5R4.zip](../hardware/v1_2/native_projects/MORI_imu_P5R4.zip) |
| 原生后接口板 | [MORI_rear_P5R7.zip](../hardware/v1_2/native_projects/MORI_rear_P5R7.zip) |
| 正式机械交接 | [mechanical_P5R7](../hardware/v1_2/handoff/mechanical_P5R7.json) |
| 接线与 BOM | [wiring_P5R7](../hardware/v1_2/wiring_P5R7/README.md) · [bom.csv](../hardware/v1_2/bom.csv) |
| 模型、STL 与动画 | [机械说明](../mechanical/README.md) · [图册](../mechanical/index.html) · [STL](../mechanical/exports/) |
| 网页、后端与仿真 | [apps/console](../apps/console/) · [backend](../backend/) · [simulation](../simulation/) |
| 固件与验证工具 | [firmware](../firmware/) · [软件说明](../README_SOFTWARE_V1_2.md) · [tools](../tools/) |
| 历史与完整证据 | [历史索引](HISTORY.md) · [归档与恢复](GITHUB_ARCHIVE.md) |

原生 PCB 需先按 [解压说明](../hardware/v1_2/native_projects/README.md)恢复完整工程，原理图和设计规则仍可直接查看。

`config/project_baseline.json` 中早期 P3 字段保留原样，不能替代当前 P5R7 正式交接。历史软件仍有 F413 目标，与当前 F412RET6 硬件的差异没有在资料整理中解决。

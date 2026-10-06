# 项目资料索引

本页以 2026-10-06 的 M1.52／P5R7 为阅读入口。原目录保持，避免破坏脚本、KiCad 引用和历史证据。

## 规格与共享契约

| 文件 | 用途 |
|---|---|
| [V1.2 共同规格](../MORI_SPEC_V1_2.md) | 需求基线；四个执行器、真实头部相机、纯两轮主动平衡 |
| [项目协作规则](../AGENTS.md) | 工作包边界、用户确认和历次采用记录 |
| [当前状态](CURRENT_STATUS.md) | 已接收版本及尚未关闭的问题 |
| [几何参数](../config/geometry.json) | 当前机械唯一尺寸源 |
| [机械接口](../contracts/mechanical_interfaces.json) | 安装、空间与接口要求 |
| [硬件器件合同](../contracts/components.json) | 型号、数量、来源、未知字段和采购状态 |
| [电气接口](../contracts/electrical_interfaces.json) | 硬件任务维护的电气契约 |
| [协议入口](../contracts/README.md) | 软件协议与生成文件说明 |

`config/project_baseline.json` 保留早期硬件 P3 字段，尚未由原维护流程更新；不能覆盖当前 components 合同和 P5R7 正式交接。本次没有改写这份历史元数据。

## 机械

| 文件／目录 | 用途 |
|---|---|
| [mechanical/README.md](../mechanical/README.md) | 当前机械修订说明 |
| [mori_v1_2.blend](../mechanical/mori_v1_2.blend) | M1.52 主模型，Git LFS |
| [mori_electronics_detail.blend](../mechanical/mori_electronics_detail.blend) | 电子细模，Git LFS |
| [mori_assembly_animation.blend](../mechanical/mori_assembly_animation.blend) | 可编辑装配动画，Git LFS |
| [图册](../mechanical/index.html) · [零件页](../mechanical/parts.html) | 本地静态服务阅读 |
| [动画说明](../mechanical/animation/README.md) · [视频](../mechanical/animation/MORI_assembly.mp4) | 当前 M1.52-A1，视频为普通 Git 文件 |
| [当前 STL](../mechanical/exports/) · [壳体试配件](../mechanical/studies/prearrival_finish/body_split_adoption/fit_coupons/README.md) · [6806 试片](../mechanical/studies/prearrival_finish/neck_adoption/fit_coupons/index.html) | 试打参考，未制造放行 |
| [建模与校核脚本](../mechanical/scripts/) | 当前参数驱动构建及历史增量流程 |
| [厂家与重建资料](../mechanical/sources/) | 官方 CAD、尺寸、照片重建及来源等级 |
| [当前交付记录](../mechanical/studies/prearrival_finish/reaction_access_M1_51/delivery.json) | 本轮实际变更范围、文件哈希与检查边界 |
| [未完成事项原始记录](../mechanical/studies/prearrival_finish/work_status.json) | 包括未采用候选和阻塞项，持续工作记录 |
| [金属件设计](../mechanical/metal_design/) | 自制金属接口的工程资料，不等于加工放行 |

## 硬件

| 当前原生项目 | 版本 |
|---|---|
| [运动载板](../hardware/v1_2/kicad/MORI_motion_P5R7/) | P5R7 |
| [电源板](../hardware/v1_2/kicad/MORI_power_P5R6/) | P5R6 |
| [IMU 板](../hardware/v1_2/kicad/MORI_imu_P5R4/) | P5R4 |
| [后接口板](../hardware/v1_2/kicad/MORI_rear_P5R7/) | P5R7 |

[硬件总说明](../hardware/v1_2/README.md) · [正式机械交接](../hardware/v1_2/handoff/mechanical_P5R7.json) · [接线资料](../hardware/v1_2/wiring_P5R7/README.md) · [BOM](../hardware/v1_2/bom.csv) · [板级测试计划](../hardware/v1_2/test_plan.md)。

PH 孔、J10 及后续线束研究目录是独立候选／补充证据，不能仅按文件日期替换上述已接收板卡。硬件源文件本次原样归档。

## 软件与试验

[软件 V1.2 说明](../README_SOFTWARE_V1_2.md) · [网页源码](../apps/console/) · [后端](../backend/) · [运动固件](../firmware/motion/) · [交互固件](../firmware/interaction/) · [模拟与回放](../simulation/) · [工具脚本](../tools/)。

[原软件验收记录](../reports/v1_2/acceptance.md) · [实时系统说明](realtime_v1_2.md) · [动力学假设](dynamics_v1_2.md) · [调试手册](debug_manual_v1_2.md)。测试证据保留实际版本；软件与最新硬件的差异见 [当前状态](CURRENT_STATUS.md)。

## 采购、历史与下载

[按厂家采购清单](../mechanical/procurement/M1.52_按厂家采购清单_2026-10-06.md) · [历史索引](HISTORY.md) · [归档范围与大文件](GITHUB_ARCHIVE.md) · [第三方通知](../THIRD_PARTY_NOTICES.md)。

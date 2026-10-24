> 阶段采用记录，保留当时输入和检查范围；当前进度以 [CURRENT_STATUS](CURRENT_STATUS.md) 为准。

# M1.57 后壳 DC 试配孔座

2026-10-13，用户确认“采用，先按样品尺寸做试配孔座”。本地工作目录为 `/Users/dean/.codex/worktrees/archive-split/MORI`；没有提交 PR，也没有改变电气工程。

本版在后壳 `Body_Rear` 后侧中线增加 Ø8 mm 试孔与 Ø15 × 4 mm 一体孔座。基准是原壳面 Z130 mm，轴线向后上方约 19.024°，外侧座面内收 0.5 mm。结构尺寸与审阅候选一致，不新增打印件、开关孔或独立安装支架。

两件新增橙色对象是样品原有充电插座及螺母的容量参考，不是新选型，也不是精确厂商 CAD。原始样品 R41 与 R55 的网格一致，按原尺寸刚性移入；没有缩小尾部以伪造可穿孔结果。用户确认黑色件是充电插座、金属件是电源开关；照片显示外侧挡边与内侧螺母的安装关系，没有提供新的尺寸测量。

安装顺序：后壳拆下，取下插座螺母，从外向内穿入，在内侧锁紧，最后装后接口板。动画把插座与螺母作为已在后壳上就位的参考展示，不演示尚未验证的完整尾线穿孔。

## 尺寸和证据

| 项目 | 数值 | 证据范围 |
|---|---|---|
| 孔径／名义螺纹直径 | Ø8 mm | 样品试配值，ASSUMED；没有宣称打印余量合适 |
| 螺纹段 | 7 mm | 样品估算 |
| 安装面到尾端空间 | 25 mm | 容量模型，不是热缩管实测长度 |
| 螺母对边 | 约 10.5 mm | 既有用户近似测量；不认证螺母其他尺寸 |
| 孔座 | Ø15、厚 4 mm | 已批准设计值；PA12 强度 NOT_TESTED |

`config/geometry.json#/dc_inlet_trial` 是构造尺寸的唯一来源。[采用前记录](../mechanical/input_assets/dc_trial_M1_57/baseline.json)冻结 M1.56 网格指纹、位姿、候选和来源；[批准记录](../mechanical/input_assets/dc_trial_M1_57/approval.json)固定采用范围。候选网格仅用于独立比较，不是生成主模型的输入。

孔边布尔运算在 Float32 保存时出现微小退化面；生成器仅在 0.00001 mm 数值阈值内整理网格，并继续与未经整理的批准候选比较。这个数值不是打印公差，也没有扩大孔径或改动设计轮廓。

## 当前文件和检查

[完整主模型](../mechanical/mori_v1_2.blend) · [后壳 STL](../mechanical/exports/stl/Body_Rear.stl) · [当前图册](../mechanical/index.html#dc) · [装配动画](../mechanical/animation/index.html)

[逐件范围与孔座检查](../mechanical/reports/dc_inlet_validation.json)、[完整检查汇总](../mechanical/reports/validation.json)、[后壳装入路径](../mechanical/reports/body_split_validation.json)、[STL 回读](../mechanical/reports/export_manifest.json)和[交付一致性](../mechanical/reports/off_shelf_delivery.json)以各自记录的主模型 SHA 为准。本轮保存后检查为 **14 PASS、0 FAIL、8 BLOCKED、9 NOT_TESTED**；状态只代表列出的范围。

本轮已实际执行的命令（执行时尚沿用自动视频流程）：

```sh
python3 mechanical/scripts/run_off_shelf_deliverables.py --rebuild
```

执行日志和每一步命令保存于 `mechanical/reports/off_shelf_commands.json` 与 `mechanical/reports/off_shelf_run/`。运行环境沿用 Blender 5.2.2 LTS、内置 Python 和项目 `mechanical/scripts/vendor`；原始样品文件和新采用输入目前只在本地，未发布到 GitHub。

本轮回读结果：

- 相对 M1.56，只改 Body_Rear；其余 192 件原件网格和位姿保持，新增两件 ASSUMED 容量参考。
- 整理后的后壳与批准候选双向差体积约 0.00404 mm³；192 处 4 mm 座壁材料采样通过。
- 前、后壳各 275 个位置、220 mm 无软线移动路径通过；拆下后壳的 61 个工具容量位置通过。
- 130 个头部组合姿态未检出刚体相交；现有简化接插件仍使完整实物配合状态保持 BLOCKED。
- 20 个 STL 导出及 Blender 回读通过；只有 Body_Rear.stl 相对 M1.56 改变。
- 192 个动画物体网格和终态匹配主模型；22 步、2178 帧、24 fps、1280×720、90.75 秒 MP4 解码通过。
- 846 个受保护的硬件文件字节保持。

机械接口合同保留 M1.56 主条目，新增 `dc_inlet_trial_M1_57` 专项记录；主模型版本由 geometry.json 的 V1.2-M1.57 定义。

## 保留的限制

实际螺纹、孔径配合、尾线／热缩管／末端插头穿过 Ø8 孔、螺母完整手工具操作和 PA12 强度仍需试配。旧 Ø10 尾部是容量占位，其整体穿孔失败不能解释为实物插座无法安装。

本次不采用身体段 R2 线束；其 M1.56 研究保留独立。完整端到端线束、DC 电气接入、物理断电与互锁、UPS 并发供电、实际舵盘等仍未闭合。工程保持 PROTOTYPE / UNVALIDATED、`manufacturing_release=false`。

## 后续交付方式

用户随后明确：不用每次生成视频，先确认方案和模型。已将默认流程改为模型、检查、STL 和静态对比；`python3 mechanical/scripts/run_off_shelf_deliverables.py --rebuild` 不再生成动画或视频。确认模型后，如用户要求更新视频，才使用 `--with-animation`。本次 M1.57-A1 视频在这条指示到来前已经完成并验证，保留现有成品，不再重渲染。

# MORI 当前机械资料

当前快照：V1.2-M1.55；装配动画：M1.55-A1。已采用 C6 通道、CAM USB 朝右和批准的 R2 颈部装入修正。相对 M1.54，只有 Pitch_Yoke 实体及其 STL 改变，其余 200 件原生零件和全部硬件位姿保持；不增加打印件或紧固件。主模型、电子细模、预览和动画已同步，详见[M1.55 更新](../docs/M1_55_MODEL_UPDATE.md)。完整线束未采用，PROTOTYPE / UNVALIDATED。

- [主模型](mori_v1_2.blend)、[电子细模](mori_electronics_detail.blend)、[动画工程](mori_assembly_animation.blend)：Git LFS。
- [21 个 STL](exports/)：含机器人本体打印件及其他试配文件，未制造放行。
- [视频](animation/MORI_assembly.mp4) · [视频页](animation/index.html) · [静态图册](index.html)。
- [构建与检查脚本](scripts/) · [几何源](../config/geometry.json)。
- [按厂家采购表](procurement/M1.52_按厂家采购清单_2026-10-06.md) · [已下单记录](procurement/采购记录.md) · [本次发布说明](../docs/M1_55_MODEL_UPDATE.md)。
- [未采用线束研究摘要](studies/harness_M1_55_summary/index.html) · [到货前待补资料](../docs/PREARRIVAL_BLOCKERS.md)。

直接打开当前 Blender 文件无需恢复历史数据。重新运行建模脚本前，应按 [归档说明](../docs/GITHUB_ARCHIVE.md)恢复源模型和生成网格，并准备原记录的 Blender／CAD Python 依赖。单个历史比较还可能依赖额外归档文件，不能跳过缺失项后声称检查通过。

头部最终传动配件、完整线束与实物验证仍未闭合，见 [当前状态](../docs/CURRENT_STATUS.md)。R2 裸打印件装入通过不代表实际舵盘或带线初装通过。

当前构建完成后运行 `python3 mechanical/scripts/report.py`，输出 `mechanical/current_report.html`。该命令校验当前输入与构建证据；不会用 M1.43 的报告模板覆盖当前版本，也不覆盖保留的图册。缺失或过期证据会返回非零退出码。

完整重建前先运行 `python3 tools/restore_archive_assets.py --group mechanical-build-inputs --group native-pcbs`，以及归档说明列出的厂家源输入，再运行 `python3 tools/restore_m1_55_evidence.py --group approval` 恢复 R2 比较输入。Blender Python 需要与其 ABI 匹配的 `manifold3d`；脚本记录实际安装版本。金属件导出直接使用 OCP（`cadquery-ocp`，本轮为 7.8.1.1），通过 `MORI_CAD_PYTHON=/path/to/python` 指定；缺失依赖时明确失败。`run_all.py --core` 完成当前构建、几何检查、渲染、STL/STEP 导出和报告刷新。R2 检查另保护了本地未发布的硬件候选快照；公开克隆没有这些快照时，完整来源保护重放会失败，不能跳过后声称全部检查已重现，详见[本次证据边界](../docs/M1_55_MODEL_UPDATE.md)。

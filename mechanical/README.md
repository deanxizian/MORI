# MORI 当前机械资料

当前快照：V1.2-M1.52；装配动画：M1.52-A1。本轮审查清理了头前壳四个微小游离体，未改尺寸或硬件位置。动画保留原 M1.52-A1 演示；当前主模型与电子细模包含清理。仍为 PROTOTYPE / UNVALIDATED。

- [主模型](mori_v1_2.blend)、[电子细模](mori_electronics_detail.blend)、[动画工程](mori_assembly_animation.blend)：Git LFS。
- [21 个 STL](exports/)：含机器人本体打印件及其他试配文件，未制造放行。
- [视频](animation/MORI_assembly.mp4) · [视频页](animation/index.html) · [静态图册](index.html)。
- [构建与检查脚本](scripts/) · [几何源](../config/geometry.json)。
- [按厂家采购表](https://github.com/deanxizian/MORI/blob/48fe22aa75554c9d7bb237e2d2dcacca7f83dde1/mechanical/procurement/M1.52_%E6%8C%89%E5%8E%82%E5%AE%B6%E9%87%87%E8%B4%AD%E6%B8%85%E5%8D%95_2026-10-06.md)。

直接打开当前 Blender 文件无需恢复历史数据。重新运行建模脚本前，应按 [归档说明](../docs/GITHUB_ARCHIVE.md)恢复源模型和生成网格，并准备原记录的 Blender／CAD Python 依赖。单个历史比较还可能依赖额外归档文件，不能跳过缺失项后声称检查通过。

头部最终传动配件、完整线束、部分初装与实物验证仍未闭合，见 [当前状态](../docs/CURRENT_STATUS.md)。

当前构建完成后运行 `python3 mechanical/scripts/report.py`，输出 `mechanical/current_report.html`。该命令校验当前输入与构建证据；不会用 M1.43 的报告模板覆盖 M1.52，也不覆盖保留的图册。缺失或过期证据会返回非零退出码。

完整重建前先运行 `python3 tools/restore_archive_assets.py --group mechanical-build-inputs --group native-pcbs`，以及归档说明列出的厂家源输入。Blender Python 需要与其 ABI 匹配的 `manifold3d`；脚本记录实际安装版本。金属件导出直接使用 OCP（`cadquery-ocp`，本轮为 7.8.1.1），通过 `MORI_CAD_PYTHON=/path/to/python` 指定；缺失依赖时明确失败。`run_all.py --core` 会完成当前构建、几何检查、渲染、STL/STEP 导出和报告刷新；历史比较与 A0 报告不作为本流程的必需输入。

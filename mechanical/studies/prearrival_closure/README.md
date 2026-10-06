# 到货前复核（M1.43）

先看 [可视化审查页](index.html)、[装配工艺](ASSEMBLY_PROCESS.md)、[输入要求](INPUT_REQUIREMENTS.md)。完整工艺和线束仍为 BLOCKED；主模型与硬件源文件未改。

`engineering.py` 计算现有模型质量/惯量及头部、行驶工况；`assembly_preflight.py` 查分阶段工具/嵌件/插头；`rigid_assembly_paths.py` 查26组刚体路径；`sequence_dependencies.py` 查这些步骤能否组成真实装配顺序；`harness_routes.py` 只生成候选线束；`head_route_space.py` 只筛查服务环空间。`dual_body_sequence.py` 补充407个两件独立运动的装配位置；`receive_p5r7.py` 从只读原生板重建P5R7缓存；`p5r7_fit.py`、`p5r7_followthrough.py`、`p5r7_service.py` 校核独立接收候选。`body_sequence_animation.py`生成10秒补充Blender/MP4动画，完整整机动画已另行更新至V1.2-M1.44-A1，沿用主模型几何。各自同名JSON与log是证据。

`imu_feedthrough_candidate.blend` 是未采用且未通过的独立尝试，不得导出为当前制造件。`lcd_diagnostic.*` 是隐藏代理变换的诊断，确认主模型 LCD 没有该假象碰撞；不需要改 LCD。`neck_sections.svg.png` 为不完整的 QuickLook 缩略图，不用于交付；使用完整的 `neck_sections.png`。

重新生成审查页：`/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_closure/publish.py`。几何脚本需由 Blender 打开 `mechanical/mori_v1_2.blend` 后运行，实际命令与版本见 manifest.json。

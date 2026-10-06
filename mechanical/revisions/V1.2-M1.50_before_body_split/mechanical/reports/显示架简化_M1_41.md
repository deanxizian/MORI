# Display Frame 平直连接 · V1.2-M1.41

用户确认第二版平直 U 形候选。两侧固定耳和下横梁前面齐平（Y=33.5 mm），底边齐平（Z=208 mm）；去掉旧内侧回折竖片，并清除横梁上沿约 0.001 mm 的历史布尔运算残片。原侧耳上保留四个螺孔及螺母沉槽。

只改 Display_Frame 一个打印件。中央立柱、相机夹持座、三个 LCD 原厂安装轴线/倾斜承压面、屏幕和相机位姿、其他打印件及所有硬件保持。相对于 M1.40，新增材料 1577.601 mm³、去除 979.895 mm³，净增约 0.60 cm³。打印件仍 15 件，紧固件对象仍 129 个；没有新孔、额外走线孔或新零件。

当前外轮廓与确认候选的差量 0.000152 mm³。正式生成保留 M1.40 原 LCD 孔面，避免候选中重复切孔产生的微小碎面；原孔面区域差量 0.001219 mm³，网格清理沿用项目 0.0005 mm 容差。对 M1.40 逐件网格/位姿核对，只有 Display_Frame 改变。其前面、底边承接和旧薄片清除的实体探针通过，打印件保持单一连续实体。

完整检查结果：109 PASS / 0 FAIL / 19 NOT_TESTED / 16 BLOCKED。130 个组合头部姿态未检出干涉，保留低头 20°。三个 LCD 螺钉的承压面、装入与直杆工具路径，以及四个侧面螺母的装入路径通过。重复生成、非生成对象保留、当前预览与毫米 STL、装配动画几何一致性已检查。采购件尺寸不缩放，硬件源文件未修改。

Blender、打印候选 STL、零件预览、总装页面、可编辑装配动画与视频已同步。首轮 PA12；实物公差、螺纹/嵌件匹配、承载强度与动态性能仍未验证。本次几何修改没有解决此前舵盘/短轴等未定接口，也不构成制造放行。

- [当前主模型](../mori_v1_2.blend)
- [可编辑装配动画](../mori_assembly_animation.blend)
- [装配视频](../animation/MORI_assembly.mp4)
- [当前形状与对比](../studies/display_frame_transition/index.html)
- [改动范围及实体检查](display_frame_validation.json)
- [全部检查](validation.json)
- [同步交付检查](delivery_consistency.json)
- [实际命令与日志](display_frame_commands.json)

M1.40 快照：`mechanical/revisions/V1.2-M1.40_before_display_frame_flush/`。当前唯一尺寸源：`config/geometry.json`；本次参数入口：`display_frame_simplification`。

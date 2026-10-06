# MORI V1.2-M1.31

保留原来的直角安装座，只清除接角处旧几何叠加留下的窄条和弧形残料。安装座外形、座面、螺孔、嵌件和舵机位置保持，没有增加斜撑、零件或螺钉。 [本轮修改](reports/舵机座直角清理.md)

两只SCS0009按厂家尺寸图重建：修复安装耳悬空，纠正耳座高度，补齐输出端。固定支架改为连续底面和简单耳座，撤掉预估走线孔、斜切和线夹。 [本轮修改与精度范围](reports/小舵机与固定座.md)

走线已延后；舵盘配合和打印强度未验证。

[当前预览](index.html) · [电路板精度与来源](reports/电路板精细模型.md) · [PCB尺寸反馈](PCB_LAYOUT_FEEDBACK_M1_23.md)

- 总装：mori_v1_2.blend
- 逐位号编辑：mori_electronics_detail.blend
- 当前装配动画：mori_assembly_animation.blend；视频：animation/MORI_assembly.mp4；分步骤播放：animation/index.html。
- 共享尺寸：../config/geometry.json；接口：../contracts/mechanical_interfaces.json

重新生成模型与候选输出：

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python-exit-code 1 --python mechanical/scripts/build.py
/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python-exit-code 1 --python mechanical/scripts/validate.py
/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python-exit-code 1 --python mechanical/scripts/render.py
/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python-exit-code 1 --python mechanical/scripts/export.py
```

原生PCB更新后，先运行prepare_populated_pcbs.py inventory/export（KiCad Python），再运行convert_populated_pcbs.py和supplement_populated_pcbs.py（OCP Python），检查差异并重新验证。不得修改硬件原件以匹配机械旧孔。详细来源/已执行命令见reports/commands.json。

{'PASS': 79, 'FAIL': 0, 'NOT_TESTED': 17, 'BLOCKED': 18}；几何不等于制造放行。后接口开关、CAM完整装件、配对插头、排母和独立充电板仍待处理。各轮机械快照保留在revisions/。

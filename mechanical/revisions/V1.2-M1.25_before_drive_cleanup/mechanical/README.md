# MORI V1.2-M1.25

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

{'PASS': 73, 'FAIL': 0, 'NOT_TESTED': 14, 'BLOCKED': 17}；几何不等于制造放行。后接口开关、CAM完整装件、配对插头、排母和独立充电板仍待处理。M1.22快照完整保留在revisions/。

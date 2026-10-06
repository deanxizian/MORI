# MORI V1.2-M1.33

当前微雪模型：[来源、估算尺寸与安装冲突](reports/微雪部件模型.md)。相机结构适配待确认；模型未获制造放行。

两处Yaw舵机安装座的顶部承压面已围绕原孔位收齐为矩形。孔距、座面高度、舵机及五金位置保持；前侧保持规整直角柱，后侧连接臂保留在承压面下方。不增加打印件、螺钉或走线孔。 [当前修改](reports/舵机凸台居中.md)

M1.31清除的直角接角残料继续保持清除。当前M1.32另按确认方案将两处舵机座顶部轮廓以孔为中心收齐，并保留下方连接臂；此处不再宣称安装座整个外形与M1.30相同。孔位、舵机和直角接合形式保持。 [本轮修改](reports/舵机座直角清理.md)

两只SCS0009按厂家尺寸图重建：修复安装耳悬空，纠正耳座高度，补齐输出端。固定支架改为连续底面和简单耳座，撤掉预估走线孔、斜切和线夹。 [本轮修改与精度范围](reports/小舵机与固定座.md)

走线已延后；舵盘配合和打印强度未验证。

[当前预览](index.html) · [电路板精度与来源](reports/电路板精细模型.md) · [PCB尺寸反馈](PCB_LAYOUT_FEEDBACK_M1_23.md)

- 总装：mori_v1_2.blend
- 逐位号编辑：mori_electronics_detail.blend
- 上一版装配动画（V1.2-M1.32）：mori_assembly_animation.blend；本轮因相机安装干涉保留旧版。
- 共享尺寸：../config/geometry.json；接口：../contracts/mechanical_interfaces.json

重新生成模型与候选输出：

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python-exit-code 1 --python mechanical/scripts/build.py
/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python-exit-code 1 --python mechanical/scripts/validate.py
/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python-exit-code 1 --python mechanical/scripts/render.py
/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python-exit-code 1 --python mechanical/scripts/export.py
```

原生PCB更新后，先运行prepare_populated_pcbs.py inventory/export（KiCad Python），再运行convert_populated_pcbs.py和supplement_populated_pcbs.py（OCP Python），检查差异并重新验证。不得修改硬件原件以匹配机械旧孔。详细来源/已执行命令见reports/commands.json。

{'PASS': 81, 'FAIL': 2, 'NOT_TESTED': 18, 'BLOCKED': 17}；几何不等于制造放行。后接口开关、CAM实物复核、配对插头、排母和独立充电板仍待处理。各轮机械快照保留在revisions/。

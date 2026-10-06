# MORI 装配动画

MORI 装配动画 / V1.2-M1.23

当前场景：MORI_Assembly_Animation。空格播放，Shift+左方向键回到开头。
总长 54.00 秒，24 fps，共 1296 帧。
时间轴的 18 个中文标记同时切换对应相机。每个零件保留独立物体与关键帧。
在 Outliner 按步骤展开集合；选零件，在 Dope Sheet / Graph Editor 调整时间。
原始 MORI_V1_Assembly 场景保留真实总装与运动轴，可切回检查尺寸。

动画中的位移、台面预装、镜头切换仅作装配讲解。上壳附件在独立镜头预装后
切换到总装姿态，没有声称上壳可以穿过完整头部。所有帧的全程装配干涉、
工具/人手空间、软线束、紧固扭矩与真实零件公差仍未验证。
橙色表示未完整确认的部件；没有缩放采购件或改变候选 STL。

重新生成：

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 mechanical/mori_v1_2.blend --python mechanical/scripts/assembly_animation.py -- --width 1280 --render stills
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 mechanical/mori_assembly_animation.blend -S MORI_Assembly_Animation -a
```

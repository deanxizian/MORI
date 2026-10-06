# MORI 装配动画

MORI 装配动画 / V1.2-M1.43

当前场景：MORI_Assembly_Animation。空格播放，Shift+左方向键回到开头。
总长 63.50 秒，24 fps，共 1524 帧。
时间轴的 19 个中文标记同时切换对应相机。每个零件保留独立物体与关键帧。
在 Outliner 按步骤展开集合；选零件，在 Dope Sheet / Graph Editor 调整时间。
原始 MORI_V1_Assembly 场景保留真实总装与运动轴，可切回检查尺寸。

上壳附件先在台面预装，随后切换到装入起点；按已检查的取出路径逆向装入，
再安装固定桥、头部和车轮。其他位移、台面预装、镜头切换仅作装配讲解。全动画的逐帧装配干涉、
工具/人手空间、软线束、紧固扭矩与真实零件公差仍未验证。
橙色表示未完整确认的部件；没有缩放采购件或改变候选 STL。

降压器区分：第6步的外置模块是轮驱9V（D36V50F9）和头部6V（D24V22F6）。
第7步电源板上的U60/U70已集成运动5V和CAM 5V；没有另装两块外置5V模块。
依据为当前已接收的原生PCB与硬件BOM；WeAct E及后接口J3问题已交硬件任务，尚未同步新板。

重新生成：

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 mechanical/mori_v1_2.blend --python mechanical/scripts/assembly_animation.py -- --width 1280 --render stills
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 mechanical/mori_assembly_animation.blend -S MORI_Assembly_Animation -a
```

# MORI 装配动画

MORI 装配动画 / V1.2-M1.43-A2

当前场景：MORI_Assembly_Animation。空格播放，Shift+左方向键回到开头。
总长 76.00 秒，24 fps，共 1824 帧。
时间轴的 21 个中文标记同时切换对应相机。每个零件保留独立物体与关键帧。
在 Outliner 按步骤展开集合；选零件，在 Dope Sheet / Graph Editor 调整时间。
原始 MORI_V1_Assembly 场景保留真实总装与运动轴，可切回检查尺寸。

上壳附件先在台面预装，镜头切换至桥已放入壳内、两件分别支承的装入起点。
第9步：上壳倾15°、桥保持水平，共同下移，再向前移动14mm。
第10步：上壳保持抬高14mm不动；桥单独下降18mm，装入并锁两枚M3。
第11步：桥已固定，上壳沿15°／14mm联动轨迹回正落位，再锁框架螺钉。
三步名义路径依据407个组合位置的检查；保存后的关键帧另以半帧抽样实体复核。
双舵机先在离机座上锁紧；Pitch先在X+30mm处下放，再向左平移到位。
其他位移、台面预装与镜头切换仅作装配讲解。全动画的连续扫掠、人手／夹具、
完整软线束、紧固扭矩与真实零件公差仍未验证。头部舵盘／短轴仍未定型。
橙色表示未完整确认的部件；没有缩放采购件或改变候选 STL。

降压器区分：第6步的外置模块是轮驱9V（D36V50F9）和头部6V（D24V22F6）。
第7步电源板上的U60/U70已集成运动5V和CAM 5V；没有另装两块外置5V模块。
本视频保持M1.43主模型的几何及旧板来源。P5R7已正式收到并建立独立候选，
但E针与原厂孔的配套规格尚未确定，未并入主模型；不要据旧板动画接线或下单。

重新生成：

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 mechanical/mori_v1_2.blend --python mechanical/scripts/assembly_animation.py -- --width 1280 --render stills
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 mechanical/mori_assembly_animation.blend -S MORI_Assembly_Animation -a
```

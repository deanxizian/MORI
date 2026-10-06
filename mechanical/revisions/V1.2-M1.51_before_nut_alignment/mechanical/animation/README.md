# MORI 装配动画

MORI 装配动画 / V1.2-M1.51-A1

当前场景：MORI_Assembly_Animation。空格播放，Shift+左方向键回到开头。
总长 85.75 秒，24 fps，共 2058 帧。
时间轴的 22 个中文标记同时切换对应相机。每个零件保留独立物体与关键帧。
在 Outliner 按步骤展开集合；选零件，在 Dope Sheet / Graph Editor 调整时间。
原始 MORI_V1_Assembly 场景保留真实总装与运动轴，可切回检查尺寸。

身体改为前后两片外壳。承重桥在身体外壳未装时单独下放、前移并锁紧。
前壳喇叭和后壳接口板在台面分别预装；内部总成完成后，前壳沿-Y、后壳沿+Y合入。
底部两组一体插舌定位，四枚原框架螺钉经底部工具孔锁紧；旧拼缝螺钉和嵌件取消。
每片模块含附件的名义平移路径各检查275个位置；保存后的动画另以半帧抽样。
完整软线长度、变形和带线合壳仍未完成，动画未把静态导线示意当作装配证明。
双舵机先在离机座上锁紧；Pitch先在X+30mm处下放，再向左平移到位。
C压板先从侧面套到转动座，随驱动座一起下放。随后转动座转60°，
从上方锁两枚M3×8后回正，再安装俯仰头部。固定压板不随Yaw转动。
M1.49采用6806ZZ轴承（30×42×7mm）；压板配对孔位为X±26.2mm，
外径60.4mm。颈部11条局部导线空间检查不代表完整线束已完成。
拆卸需先移除俯仰头部，松开压板和反力连接后上提，不是整头快拆。
其他位移、台面预装与镜头切换仅作装配讲解。全动画的连续扫掠、人手／夹具、
完整软线束、紧固扭矩与真实零件公差仍未验证。头部舵盘／短轴仍未定型。
橙色表示未完整确认的部件；没有缩放采购件或改变候选 STL。

降压器区分：第6步的外置模块是轮驱9V（D36V50F9）和头部6V（D24V22F6）。
第7步电源板上的U60/U70已集成运动5V和CAM 5V；没有另装两块外置5V模块。
本视频采用V1.2-M1.51主模型，运动基板与后接口板已更新为P5R7；电源P5R6、IMU P5R4。
CAM相机排线入口朝上，屏幕排线入口朝板外；两处依据官方照片修正。
槽口/触点仅为示意，真实插深、补强片和接触面仍未确认；完整线束尚未应用。
WeAct元件面朝上、排针朝下；先放三组排母，再插入核心板与E直排针候选。
E排针与原厂STEP孔径资料矛盾仍为BLOCKED，11.04mm是候选叠层，不能据动画确认实物配合或下单。

重新生成：

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 mechanical/mori_v1_2.blend --python mechanical/scripts/assembly_animation.py -- --width 1280 --render stills
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 mechanical/mori_assembly_animation.blend -S MORI_Assembly_Animation -a
```

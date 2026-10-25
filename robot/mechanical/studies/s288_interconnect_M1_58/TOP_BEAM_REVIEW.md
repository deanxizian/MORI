# 上梁出线候选

2026-10-13，用户明确“上臂”指横跨两台电机的顶部横梁。本页是独立比较，未应用主模型或 STL。

先前方案沿用下方插口/下绕，仅对该路线提出端壁槽，没有充分比较上梁。check_top_beam.py 补查上口到上口路线：三根名义各190mm，OD用户约1mm；0/0.5/1外伸试值×6几何线位配对共18组通过。所选P1增粗半径0.6/0.7两组通过，并非全部增粗外伸组合通过。此前上口P0增粗0.7碰自身舵机的失败保留在candidate_check.json。

## 局部切削

两处8×9.9mm试验槽，中心(X,Y)为(+2.7,+22.45)/(-2.7,-22.45)，Z63.4..66.6；R1边角。槽沿现有横梁前后边缘开放，避免把真实插头通过未知小闭孔作为装配前提。只改Drive_Bridge，原下部端壁/轴承座/固定轴线/底盖不变。移除469.933765902mm³，增加0、区域外删除0，改前改后均1件连续实体。移除量比原端壁方案765.848375508mm³少38.64%，不能据此推断强度。

初始8×5闭孔名义结果保留为check_top_beam_closed_holes.py/top_beam_closed_holes_check.json；它未验证实际插头穿孔。最终边缘开放槽的结果是top_beam_check.json，当前脚本来源散列记录在其中。

## 路径与装入

尾弯仍采用试验中心半径5mm（各线3/5/7），1mm压接直尾、2mm弯后短尾均ASSUMED。上升与转向半径3mm、上方蛇形圆弧3.5mm；U04三个平面Z69.2/70.6/72。有限24面多边形管、约0.2mm圆弧采样，没有连续间隙或线材疲劳证明。所选U04对UPS/Load_Frame min_gap检索封顶3mm，返回3表示>=3，不是精确3。

左下口U03短段延至Y35.5；9个OD1名义样本与本体/U04均无相交。它不是完整到载板的线，实际端点、针序与厂家接头仍需完整核对。本研究不修改硬件设计或发送硬件对话指令。

check_top_beam_sequence.py：电机/底盖先保持安装位，顶梁从上方下移20mm，线圈同时下移/展开。41位置中各U04的解析长度均190mm；原厂电机、原螺钉、轴承/金属件真实尺寸保持。原2软垫接触及4极小轴承交叠低于既有项目阈值仍单列，非实物资格。4枚底盖螺钉各69位置、前后壳各275位置对U04及短U03未相交。人工持线/台面临时支撑/真实插头/完整190mm U03未验证，完整柔性装配BLOCKED。20mm起始位置是有限几何检查起点，不代表整套台面摆放已经验证。

余线固定、真实弯折和源模型与实物一致性、全部线束并存、PA12强度均未完成。main_adoption=false，manufacturing_release=false。不更新视频。

## 复现

实际命令和失败保留在commands.json及日志。Blender5.2.2 LTS、Python3.13.13、numpy2.3.4、manifold3d3.5.3。

```sh
python3 mechanical/studies/s288_interconnect_M1_58/run_stage.py top_beam_open_edge check_top_beam.py --main
python3 mechanical/studies/s288_interconnect_M1_58/run_stage.py top_beam_wired_sequence check_top_beam_sequence.py --main
python3 mechanical/studies/s288_interconnect_M1_58/run_stage.py top_beam_static_views render_top_beam.py --main
python3 mechanical/studies/s288_interconnect_M1_58/publish_top_beam.py
```

top_beam_UNADOPTED.blend只含局部打印件、原厂电机/UPS、承重板及名义线段，不是最新完整总装。用于显示的原厂S288外形也尚未替换主模型的旧简化模型。

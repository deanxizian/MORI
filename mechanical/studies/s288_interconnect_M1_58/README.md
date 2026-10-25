# 轮舵机串接线与驱动上座出口候选

**最新补查是[内部串接收纳](inside_review.html)：原上梁、底盖不改，U04 三芯各 190 mm 收入前后对角空腔；18 组名义路径和局部装入通过。** 详见 [INSIDE_REVIEW.md](INSIDE_REVIEW.md)。下文保留原端壁开槽研究作对照，上梁开槽和端壁开槽均未采用。内部方案仍需真实线材固定、防夹及完整 U03，不能作为全线束放行。

2026-10-13，主模型 M1.58，**未采用**。只有 Drive_Bridge 两处候选底部开放槽发生实体变化；主模型、20 STL、电子细模及视频等 26 文件 SHA 保持不变。原厂 S288 仍作为独立未采用参考。

## 来源与假设

- 电机来自上一轮原厂 STEP 来源及不缩放的同轴安装变换；保留六正闭合壳减内边界的实体策略，两个开放源表面未参与体积检查。
- 用户导线段约 190 mm，不含两端插头；三芯、单芯绝缘外径约 1 mm。没有误差或压接到导线段端点的精确基准，不能当作裁线尺寸。
- 电机插口基准和 2 mm 行距沿用上一轮目录/外包框容量模型。塑壳外伸 0/0.5/1 mm、压接直尾 1 mm 是假设，不是测量；用户只描述插头几乎全部藏入舵机。
- 下口串接候选每根名义中心线恰为 190 mm。尾弯采用中心半径 5 mm、各线半径 3/5/7 mm；外部竖向过渡半径 4 mm，底部蛇形圆弧 3.5 mm。三根底部中心线高度 32.5/33.9/35.3 mm，几何配对比较六种，不赋予真实电气针号。
- Circle/straight 长度用解析值，quartic 比较族用 96 点 Gauss 数值积分；形状用于原路线的四种插口比较，选定下口候选只用直线和圆弧。圆弧点距约 0.2 mm，管截面 24 段；这是有限多边形实体检查，不是连续间隙或耐弯证明。

## 检查范围与保留失败

原下绕路径碰到端壁和腹部内壁：route_check_before_escape.json 和 initial_collision_locations.json 留存。半圆顶的早期槽使上口增粗线位碰顶，记录在 escape_parameters_semicircle.json / route_check_semicircle.json；最终改为短 R1 顶角、平直顶部的槽。

最终槽宽 8 mm，前后中心 X+2.7/-2.7，Y 壁切削跨度 24.7..27.4 / -27.4..-24.7，Z41.9..61.2。槽从底盖拼缝开放；槽上方端壁至内顶面保留 2.3 mm，原顶板 3 mm 保留。删除量约 765.85 mm³，仅在声明区域内，无增加量；改前改后均一闭合实体。轴承和紧固件切削区间隙结果为 >=10 mm（检索封顶10），不声称精确大于10。

下口-下口 18 个组合（3 个外伸试值 x6配对）名义 OD1 无体积相交；选定原名义配对增粗半径0.6/0.7也未相交。选定网格 min_gap 封顶1 mm检查，零件最小约0.500003、线间约0.4；仅当前离散网格。源本机插口处未知的装配接触不能被当成精确压接出口。

**保留上口失败**：候选主检查里的 nominal_installed_status 为 FAIL，因为其中同时包含9个上口半径0.7的增粗短段，其中一个在假设0外伸时碰自己的电机约0.43 mm³。随后 upper_nominal_check.json 单独检查OD1名义短段，9/9无相交。不能把这个补查说成原增粗检查通过，也不能把所有线束说成通过。

四种上下口的较早完整路线比较里，下口组合通过，其他三种仍碰身体壳；保留 route_check.json。选用下口机械候选，是有限布局选择；真实端子对应仍按厂家线束与硬件针表复核，未改针位。

## 装配与未完成项

开放槽允许底盖未合上时侧放已带插头导线；随后 wired_sequence_check.json 检查了名义替代顺序：底盖/电机/串接线先保持装入位，上座及其上软垫从上方下移50mm，101个位置通过；四螺钉各69位置、前后壳各275位置均未与U04相交。旧“未来余线冻结在装入位、底盖从下方上移”的51位置路线FAIL，保留9个碰撞位置。替代路径有2条已知上软垫接触、4处终点轴承交叠约0.000022mm³，分别保留NOT_TESTED/低于项目既有0.01mm³阈值，没有当作制造配合通过。

人手夹持、台面临时支撑、余线实际固定和全部柔性线束仍未验证。底部余线还未设计固定，完整带线拆装 **BLOCKED**。真实插头详细外形、压接支撑直尾、静态弯曲半径、精确线长、完整U03端点、全部线束并存仍 BLOCKED / NOT_TESTED。不能据静态路线放行供应商裁线。

完整机械载荷、PA12槽壁强度和源模型与实发修订一致性待实物。candidate_check.json中的保护清单保持26个文件不变。hardware文件和合同未编辑；没有向硬件对话发送指令。本候选未更新视频。

## 复现

实际命令与日志在 commands.json。Blender5.2.2 LTS，Python3.13.13，numpy2.3.4，manifold3d3.5.3。

```sh
python3 mechanical/studies/s288_interconnect_M1_58/run_stage.py export_context export_context.py --main
python3 mechanical/studies/s288_interconnect_M1_58/run_stage.py candidate_full_check check_candidate.py --main
python3 mechanical/studies/s288_interconnect_M1_58/run_stage.py upper_nominal check_upper_nominal.py --main
python3 mechanical/studies/s288_interconnect_M1_58/run_stage.py render_candidate render_candidate.py --main
python3 mechanical/studies/s288_interconnect_M1_58/run_stage.py wired_sequence_fixed_reference_lists check_wired_sequence.py --main
python3 mechanical/studies/s288_interconnect_M1_58/run_stage.py static_sequence render_sequence.py
python3 mechanical/studies/s288_interconnect_M1_58/publish.py
```

初始脚本导入本地 context 失败，工具输出留存 initial_import_failure.log；增加明确脚本路径后成功。命令日志的历史脚本散列不可冒充当前帮助模块版本；first/semicircle 文件保留对应早期几何。当前候选检查源散列见 candidate_check.json/upper_nominal_check.json。

wire_exits_UNADOPTED.blend 仅包含局部驱动上座、底盖、原厂电机和名义线路，是审阅文件；不是完整主模型或可直接制造的总装。

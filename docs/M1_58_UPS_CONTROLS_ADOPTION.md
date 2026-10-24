> 阶段采用记录，保留当时输入和检查范围；当前进度以 [CURRENT_STATUS](CURRENT_STATUS.md) 为准。

# M1.58：采用上充电、下开关

2026-10-13，用户明确确认“采用上充电、下开关”。主模型、电子细模、静态图和 STL 已更新；本轮不生成视频，不提交 PR。

## 实际改动

- 上方原 DC 试配孔座保持：Ø8 孔、4 mm 座厚、原位置和法线。
- 下方原 Type-C 轴高约 108.92 mm 改为 UPS 原配开关，沿用样品 Ø12 试孔、Ø20×4 mm 一体座。两者沿机身后侧中线排列。
- 封闭旧矩形孔；删除旧接口板、USB 插座、两个固定座、两枚螺钉和两枚嵌件。仅 Body_Rear 打印件改变。
- 188 个保留件网格和位姿不变；增加两个开关／螺母样品参考体，195 件变为 191 件（含维护托架）。导出 15 件本体件、1 件维护底座及 4 件试片；场景另有四块未导出的软垫参考。

尺寸只从 geometry.json#/ups_rear_controls 生成。批准候选的独立网格只供验证，不用作建模源。没有更改原厂 CAM、WeAct 或 UPS 板上的 USB 接口。

## 保存与检查

主模型 SHA256：`47f3e83da47a9c3a49dc785395a660fe65d138a2148423f6e9625a8602507d54`。

- 保存后的模型对照：PASS；相对批准后壳的布尔对称体积差 0.00031706 mm³，为数值网格差异，不是加工公差。
- 两个孔座各 192 个材料探针、各 61 个工具位置：PASS。上方 DC 局部几何保留、单连通实体和允许区域外改动检查：PASS。
- 前后壳分别 275 个刚性平移样本：PASS；前壳／车轮等按报告保留。不包含柔性引线。
- 当前刚性件、11 个插头容量和 130 个头部组合姿态：PASS；新增开关到 UPS 最小名义间隙 1.851 mm。连续运动和真实装件未资格化。
- 20 个 STL 均导出并回读；电子细模 833 个独立参考物体与主模型坐标匹配。9 张静态图来自保存主模型。
- 本轮统一验证：14 PASS、0 FAIL、8 BLOCKED、9 NOT_TESTED；只代表记录中的检查。

实际命令和日志：[执行清单](../mechanical/reports/ups_controls_M1_58/commands.json)。构建环境 Blender 5.2.2 LTS d13f752e3b9c、Python 3.13.13、manifold3d 3.5.3。运行 `python3 mechanical/scripts/run_off_shelf_deliverables.py --rebuild`，控件净距检查已纳入默认流水线。本轮收尾同步机械合同的 UPS-R1 接收元数据后，完整重跑，保留生成时的实际输入哈希。

[完整主模型](../mechanical/mori_v1_2.blend) · [后壳 STL](../mechanical/exports/stl/Body_Rear.stl) · [静态图册](../mechanical/index.html#controls_rear) · [范围对照](../mechanical/reports/ups_controls_validation.json) · [间隙](../mechanical/reports/ups_controls_clearances.json) · [采用凭据](../mechanical/input_assets/ups_controls_M1_58/approval.json)

## 样品与电气边界

开关及螺母引用样品 R36、核对 R55 沿用同一局部网格，按 1:1 变换，标为 PLACEHOLDER / ASSUMED。螺母对边约 13.5 mm 为用户近似测量；Ø12 是样品试孔选择，不是实测螺纹。DC 螺母约 10.5 mm 同理。杆长、尾部、法兰和螺母厚度仍估算。名义杆孔零间隙并不证明实物可装；完整尾线穿孔、PA12 配合与强度、手部操作仍 NOT_TESTED / BLOCKED。

硬件对话已收到“仅一块自制驱动／载板”的授权交接并发布 UPS-R1。它更新了合同和接线需求；原生新电路／PCB 尚未完成。机械侧保留 P5R7 载板作布局参考，未改硬件源。供电并发、满电回灌、默认禁能及真实断电功能按硬件报告继续处理。

## 版本保留

修改前完整 M1.57 保存在 `mechanical/revisions/V1.2-M1.57_before_UPS_controls/mechanical/mori_v1_2.blend`，原尺寸和接口快照在 input_assets/ups_controls_M1_58。原候选仍可查看，页面已标为 M1.58 采用。

M1.57-A1 视频与动画工程字节保持。视频 SHA256：`ce6b603b91edac33d7d6bcda3f0352e2aa10eb90e21f4156a8c1962cb2369ac5`。旧视频仍含接口板，不作为本版装配指导。后续按需更新，不自动重做。

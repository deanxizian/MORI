# CAM 身体至颈部连续路线容量研究（未采用）

基于 M1.57，后续 M1.58 控件采用不改变本目录检查来源。原主模型已保存为 `mechanical/revisions/V1.2-M1.57_before_UPS_controls/mechanical/mori_v1_2.blend`，其 SHA256 为 c36f2878690225eaa1af02e234537e32acd5bfa937476e694784ef46934473cb。几何参数快照位于 `mechanical/input_assets/ups_controls_M1_58/geometry_M1_57.json`。不应在新参数下重跑本目录然后沿用旧版报告。

旧身体段连接旧颈部曲线时，在偏航端点可错开约 4.331 mm。本候选把二者接成位置及切线连续曲线，25 个偏航角（-60°..60°、间隔 5°）分别求解相同名义弧长，并检查 10 个俯仰角（-20°..25°）的实体。

证据分两种容量，不能混读：

- `current_keys_check.json`：原身体 OD1.5 / 颈部 OD1.13 混合包络 FAIL，18 个交叉线距失败记录保留。不是实体线径已经在连接处变细，也未增加接头。
- `uniform_capacity_check.json`：全段统一 OD1.13 的独立容量 PASS，250 个有限姿态、线间下界约 0.390 mm、实体下界约 0.361 mm、局部曲率半径下界约 6.028 mm。没有选定真实导线，不能取代线材、端子和厂家数据。

`body_neck_capacity_UNADOPTED.blend` 与三张 route 图片仅展示候选，未进入正式主模型/STL/装配动画。曲线止于 Z200 的数学截点，还没有接到 CAM 板。相邻偏航键之间的连续运动、固定点、上部尾线、完整线束及带线安装均未完成。名义弧长不是成品裁线长度。当前身体端沿用旧 P5R7 J5 布局参考；硬件 UPS-R1 的 J_CAM_LINK 位置尚未冻结。

数学筛选与失败过程保留在 initial_math_inspection、length_family_check 和 shared_turn_R1/R2/R3 报告中，最终控制参数由 R3 报告追溯。`initial_math_inspection.json` 是较早实现的诊断，脚本后续有修改，其历史源哈希不应与最新脚本强行匹配。数值残差是浮点计算结果，不是加工精度或物理线长控制能力。

软件环境：Blender 5.2.2 LTS / Python 3.13.13、manifold3d3.5.3、独立 SciPy1.16.2。实际命令为 Blender `-b [M1.57 source] --python-exit-code 1 --python <script>`；脚本依次包括 route_family、check_length_family、search_shared_turn、verify_current、verify_uniform_capacity 和 preview_review。预览 manifest 记录保存文件、来源和图像哈希。完整线材选择和上端路线未获资格，不采购、不裁线、不制造放行。

# MORI P5R4 · 后接口板与 IMU 审查修改

用户提供的 `MORI_Rear_IMU_P5R2_Review_Bundle(1).zip` 已逐项核对。采纳 CC 保护路径、TVS 支路、IMU 去耦和专用锡膏开口建议，在已完成 P5R3 的基础上另存 **rear / imu P5R4**；运动板和电源板继续使用 P5R3。原 P5R2、P5R3 保留。

**PROTOTYPE / 实物 NOT_TESTED / 不释放制造。** 外接 USB-PD／3S 充电模块仍未选定（用户于 2026-09-24 确认）。J2.5 原始 VBUS 检测线的源端限流尚未增加，这一短路保护问题仍为 BLOCKED，不能把本轮修改当作完整充电设计已闭合。

[原生图面前后对照](index.html) · [逐项审查处理](review_disposition.md) · [真实检查报告](reports/verification.json) · [上电与实测计划](test_plan.md) · [机械交接](../handoff/mechanical_P5R4.json)

| 本轮工程 | 板框 mm / 铜层 | 实施内容 |
|---|---|---|
| [后接口板 KiCad](../kicad/MORI_rear_P5R4/MORI_rear_P5R4.kicad_pro) | 24×25×1.6 / 2 | D3 接地和 CC2 先到保护焊盘再输出；D1 移位旋转；C1 和局部走线重排 |
| [IMU KiCad](../kicad/MORI_imu_P5R4/MORI_imu_P5R4.kicad_pro) | 20×16×1.6 / 2 | C1/C2 与真实 GND6 回流；U1 专用 Paste；传感器轴向丝印 |

KiCad **10.0.6** 实际重新填铜并执行原生检查；两板 **ERC 0、DRC 0、未连接 0、原理图差异 0**。恢复 `single_global_label`、`four_way_junction`、`simulation_model_issue`、`footprint_filter` 四项 ERC 为 warning 后再次检查，两板均无忽略检查和排除项。前后项目的电气焊盘网络、铜焊盘尺寸、孔径、原理图网表和自定义 DRC 规则文件已比较；详见 `reports/verification.json` 和 `reports/*/check_commands.json`。本版未改变器件 MPN、数量或 GPIO。

## 改动和可复核的数值

后板 D3 从 (14.3,10.0) 移至 (14.3,9.5)。CC2 在 B.Cu 先抵达 D3.1，再到 (13.25,10.7) 输出过孔；另做了同网络铜形状检查，输出过孔与输入段最小铜间隙为 0.7 mm，输入输出只在 D3.1 焊盘汇接。这个条件并非普通 DRC 能证明。[CC2 独立检查](reports/rear/CC2_flowthrough.json)。

D3 地过孔改到 (15.95,10.7)，与地焊盘中心直线距离由约 4.37 mm 减为 **1.34 mm**。D2 保留 (8,10) 过孔、约 1.91 mm 距离，增加明确的 0.3 mm 接地短线；固定开关的通孔焊盘限制了更近的常规尺寸过孔位置。两处过孔均检查了填铜的实际连接区域，**没有宣称形成最短 USB 外壳高频回路或通过 ESD**。[填铜连接证据](reports/rear/ground_return_regions.json)。

D1 从右上区域移至 (3.9,17.7)，旋转至 180°；C1 移至 (4.3,22.3)。D1 接在主路径第二个换层节点之后，支路约 **2.13 mm / 0.6 mm 宽**，不再从 J2 附近向上绕到旧 D1。受固定开关、孔位和另一面元件限制，未把它描述为紧贴 F1 输出的理想最短布局。输入主路径仍为 **0.6 mm、两颗 1.0/0.45 mm 过孔**，中心线路径约 **29.67 mm**；C1 的 0.3 mm 支路不承担 J2 的主负载。整个后板总走线反而从约 162.50 增到 176.02 mm，主要用于局部保护拓扑和避开本体，不能称全板普遍变短。

按 35 μm 铜厚、20 μm 孔铜、1.6 mm 板厚的假设，主路径 1 A 时约 **26.3 mV / 26.3 mW**（铜温 20°C 场景），70°C 场景约 31.5 mV。未计 F1、插座、线束、回流铜；温度是输入假设，**不是温升预测或载流额定**。脚本另列 15/25 μm 孔铜敏感性。[计算结果](reports/rear/input_DC_model.json)。未因“单颗过孔”直接判不合格，也没有盲加并联阵列。

IMU C1 移至 (12.5,11.7) 并旋转，C2 移至 (12.5,14.25) 并旋转。U1.8→C1.1 显式铜线约 **1.58 mm**；C1.2→U1.6 约 **3.92 mm**，在芯片外侧连接真实电源地。C3、MISO 近源 33Ω、CS 上拉保留。旧版通过地铜和过孔也连通；旧图的路径统计 `null` 只表示显式端点图不能求出完整路径，不代表断地。芯片下双面禁铜/禁孔区域保留，无新增中心散热焊盘。

U1 铜焊盘保持 0.475×0.250 mm；本版专用 Paste 为每个线性尺寸的 **90%：0.4275×0.225 mm**（部分焊盘旋转）。KiCad 实際每边比例语义下采用 `solder_paste_margin_ratio=-0.05`，绝对偏移 0；不是误设 -0.10。已从原生有效开口和 F.Paste 图双重检查。依照已读取的 TDK AN-000393 **v2.4**，暂提 **100 μm** 钢网：最小宽厚比 2.25，保守矩形释放面积比约 0.737。铜焊盘和 Mask 未改。90% 线性缩放为明确的工程解释（81% 面积），钢网厚度、公差、锡膏和实际脱模必须由贴片厂确认，状态仍 BLOCKED；未输出制造钢网。[计算与逐焊盘结果](reports/imu/stencil_design.json)。

## 布线要求和局部例外

继续使用用户 `/Users/dean/Documents/KiCad/Rules/pcb-rules.json`，47 条中 44 条启用，源哈希记录在检查报告。[规则快照](pcb-rules-source.json)。双面 BODY/NETBODY 区保留并随移动元件更新；没有为 DRC 清零批量删除区域或屏蔽检查。U1 专用 Paste 是有装配依据的局部设置。

本轮未发现无关网络穿过被检查元件本体的候选。原生 Fab 投影可能包含引脚/连接器外壳，自己的引脚向外逃线另列在每板 `body_review_final.json` 中，并不等于绝对零投影交叉。严格 R14 的 0.5 mm 倒角仍有三处明确例外：

- rear CC2 / F.Cu / (13.25,8.5)：完整倒角侵入相邻器件/铜线净空，保留一个明确转角；它不是 S 形抖动。
- IMU GND / F.Cu / (11.62,8.85) 和 (11.62,9.85)：继承的 LGA 引脚外侧短接，短边仅 0.4575 mm；不能在原通道内完成 0.5 mm setback，保留实际 FAIL 记录。

不把这些几何例外改写为规则全通过。PCB 热、EMC、用户图面认可、完整插合装配仍未验证。

## 接口、固件与机械交接

IMU J1 与 motion P5R3 J4 同号 1–8；rear J3.1/.2→power P5R3 J19.1/.2，J3.3/.4→motion P5R3 J8.1/.2，均按原生焊盘号复核。[逐针验证](reports/interface_pairs.json) · [针表](connector_pinmap.csv) · [线束](harness.json)。图的背面显示未镜像，制作对插线束必须按针号和插接面复核。

U1.9 的 FSYNC/INT2 仍接地，**正式固件不得将 INT2 配置为推挽输出**。新 X/Y/+Z 丝印描述传感器在板顶视图的轴系（+X 向右、+Y 向上、+Z 出元件面）；不是“板轴已经等于机身轴”。刚性倒装时需要机械拥有者给出板到机身变换，并做静态重力方向标定。见[软硬件交接](firmware_handoff.md)。

外形、安装孔、USB/开关/连接器和 U1 本体位置不变；[全部真实摆位](placements.csv)与[机械交接](../handoff/mechanical_P5R4.json)记录五个移动器件。没有覆盖机械模型，旧裸板 STEP 不能显示本版元件，也不作为完整装配证据；完整高度、质量、线缆弯曲仍保留未知。

## 复现

在 MORI 根目录，以 KiCad 自带 Python 执行：

```sh
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
"$KPY" hardware/v1_2/tools/check_review_P5R4.py check
"$KPY" hardware/v1_2/tools/check_review_P5R4.py audit
"$KPY" hardware/v1_2/tools/evidence_P5R4.py
"$KPY" hardware/v1_2/tools/export_P5R4.py
"$KPY" hardware/v1_2/tools/publish_review_P5R4.py
```

最后一条无 `--publish` 时仅验证并生成交接，不推进当前接口引用；任何校验失败即停止。前后工程原件是布局真值，按坐标/UUID 的试验编辑脚本是历史事务，不是幂等生成器，不应随意重跑来覆盖已检查工程。全部实际原生命令、退出码和输入哈希在 `reports/*/check_commands.json`；本轮失败的布局试验仅留在本地事务记录，不属于最终检查报告。

没有采购、制板或钢网下单；没有 Gerber 输出。报价、供应、成品电池与外部充电器等原有未闭合项不会因本次修改自动通过。

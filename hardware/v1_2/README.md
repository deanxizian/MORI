# MORI V1.2 硬件工程 · P5R7 契约

**2026-10-01 插合增补：**原厂 STEP 自带 E 弯针也与模型孔边相交。实物孔规格未知，61300821121 与 WeAct 的兼容性为 **BLOCKED**；[证据与厂家确认清单](reviews/weact_E_J3_20260930/E_pin_hole_addendum_20261001/README.md)。P5R7 原生工程未改。

当前运动板、后接口板为 **P5R7**；电源板为 **P5R6**，IMU 为 **P5R4**。状态为 PROTOTYPE / 实物 NOT_TESTED。P5R7 修正 WeAct E 插合与后板 J3，电路功能及 GPIO 分配保持。

[本次修改与检查](reviews/weact_E_J3_20260930/README.md) · [当前端口和接线 CSV](wiring_P5R7/README.md) · [正式机械交接](handoff/mechanical_P5R7.json) · [发布校核](reviews/weact_E_J3_20260930/publication_audit.json)

| 当前原生工程 | 尺寸 / 铜层数 | P5R7 范围 |
|---|---|---|
| [运动 P5R7](kicad/MORI_motion_P5R7/MORI_motion_P5R7.kicad_pro) | 70×35×1.6 mm / 4 | 元件面朝上、排针向下；E 八孔 X+2.54 mm；R19/R9 移位及相关线路重布 |
| [电源 P5R6](kicad/MORI_power_P5R6/MORI_power_P5R6.kicad_pro) | 80×55×1.6 mm / 4 | 保留原生工程 |
| [IMU P5R4](kicad/MORI_imu_P5R4/MORI_imu_P5R4.kicad_pro) | 20×16×1.6 mm / 2 | 保留原生工程 |
| [后接口 P5R7](kicad/MORI_rear_P5R7/MORI_rear_P5R7.kicad_pro) | 24×25×1.6 mm / 2 | J3 移至 B 面、180°、孔排 Y+1.70 mm；局部重布 |

两块 P5R7 的 KiCad 10.0.6 原生 ERC、DRC、未连接和原理图一致性问题均为 0，忽略项为空；器件本体投影及新增走线样式另有检查。运动板没有内层信号线。电源与 IMU 未修改，本次沿用其历史检查证据，未声称重新验证电气或实机性能。

WeAct 按用户确认的正确朝向交接，A–D 编号及连接保持，E7 接 NRST，其余 E 孔在载板为 NC。排母和 E 直针已有厂家目录候选，但报价、实物插深、保持力与完整堆叠未验证。核心板的新 Z 坐标有意留空，机械须复核上方元件、USB、维护访问、排母焊尾和插拔空间。

后板 J3 从顶视图看左到右为 4、3、2、1，按针号接线。对冻结机械候选的名义插座/插头/拔出路径筛查通过；当前完整装配和真实线束弯折仍待验证。旧 P5R6 不可仅翻焊插座就视为新版。

[当前连接器坐标](reviews/weact_E_J3_20260930/connector_pinmap_P5R7.csv) · [版本化 pinmap](interfaces/pinmap_V1.2-H0.5-P5R7.csv) · [版本化线束](interfaces/harness_V1.2-H0.5-P5R7.csv) · [主 BOM](bom.csv)

外部 PD/3S 充电模块尚未选定，RAW 检测源端保护仍 BLOCKED；整机已取消外露 SW1，原生开关电路与物理断电/急停实施仍需另行闭合。本次未完成该功能调整。热、纹波、动态负载、EMC、充电及实物装配均未验证。没有采购、制造订单或制造文件输出。

历史入口：[P5R6 图层与布局](layout_P5R6/index.html) · [P5R6 接线工作簿](wiring_P5R6/README.md) · [P5R6／线宽复审](reviews/P5R6_and_width_external_20260925/README.md) · [原 P5R6 四板工程包](MORI_FourBoards_P5R6_Reviewed_Projects.zip) · [板级测试计划](layout_P5R6/test_plan.md)。这些历史文件保留原版本；不作为 P5R7 的装配朝向依据。

既有未决项仍保留：电源板两条 In1 安静地对源 R13 的偏离、后板 CC2 严格倒角 FAIL 和 IMU 原短引出例外。零 DRC 不代表所有布线偏好、工艺或电气性能通过。原生板为布局真值，历史编辑脚本不得覆盖当前工程。

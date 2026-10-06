# MORI P2 · PCB 重排审阅版

2026-09-22，V1.2-H0.2-P2。三块板已重新布局、布线、覆铜，并通过本版原生 KiCad 10.0.6 的 ERC、DRC、未连接和原理图一致性检查。**电气 CAD 检查 PASS；完整项目规则符合性仍有明确例外，制造未放行，实机 NOT_TESTED。**

先看 [三板 Layout 阅读版](previews/MORI_P2_Layout_Review.pdf) 或 [可切换正反面/装配图的预览](previews/index.html)。[20 页功能原理图](previews/MORI_P2_Schematic_Review.pdf)直接截取本版 KiCad 矢量输出；保留 S2 功能块编排，未恢复之前绕行拥挤的原理图。

| 本版工程 | 板框 mm | ERC | DRC | 未连接 | 原理图差异 | 铜层 / 标称铜厚 |
|---|---|---:|---:|---:|---:|---|
| [运动板](../kicad/MORI_motion_P2/MORI_motion_P2.kicad_pro) | 70×35 | 0 | 0 | 0 | 0 | 2 / 35 μm |
| [身体 IMU 板](../kicad/MORI_imu_P2/MORI_imu_P2.kicad_pro) | 20×16 | 0 | 0 | 0 | 0 | 2 / 35 μm |
| [电源调理板](../kicad/MORI_power_P2/MORI_power_P2.kicad_pro) | 80×45 | 0 | 0 | 0 | 0 | 2 / 70 μm |

三板厚度均以 1.6 mm 设计，ENIG 为打样目标，尚无板厂报价或实板铜厚证明。2 层选择针对低速载板：DVP、屏幕 QSPI、USB 和 RF 保留在购买模块内；本板承担 TTL/UART、SPI、GPIO、模拟量和电源。地覆铜不能等同连续参考平面，SPI 线缆、UART 边沿和回流仍需台架检查；不能据此声称 EMC 或信号完整性已验证。

## 实际改动

- **运动板**：保留 WeAct 模块完整区域及插针，逻辑缓冲、锁存/复位、供电隔离和滤波移至背面分区；保持外部连接器针序。TI DCU0008A 封装按厂家焊盘图改为 0.85×0.30 mm，原通用 VSSOP 焊盘不再沿用。
- **IMU 板**：ICM-42688-P 按 TDK 封装/装配资料修正为 0.475×0.25 mm 焊盘；顶面敏感区和背面器件下方设置禁铜/禁走线/禁过孔，信号从周边向外引出。安装孔和轴向没有擅自改变。
- **电源板**：输入反接与分流器、轮电源、头电源、监测与两组吸能比较器按功能分区。分流器大电流从外侧进入/离开，内侧单独引出到 R3/R4；电池主通路 2 mm、轮电源主通路 1.5 mm、头电源主通路 1 mm，0.2 mm 支路只用于取样/比较器等小电流。电池换层使用两只并联 1.0/0.45 mm 过孔；大电流不经过运动板。
- 为螺钉区域、接插件本体、穿孔焊脚和模块堆叠安排避让；修复四辐条热焊盘、急角和孤立地连接。新增实际板名/版本丝印和连接器位号；仅裁剪与开窗冲突的丝印，电容圆形轮廓与极性保留。

原理图元件身份、数值、引脚 UUID 和各网络的 ref/pin 成员与 P1/S2 相同；封装标识和板上位置变化有记录。四执行器方案、摄像头、双 MCU、电源域和固件接口没有在本轮改写。P1 原生 PCB/工程保留，S2 原图以之前已记录的 SHA256 核对。

## 你的 KiCad 项目规则

规则来自 [deanxizian/KiCad](https://github.com/deanxizian/KiCad/tree/f756532aa67112a9d437c18e8ca00ac8fba2c9b4/Rules)，提交 `f756532a`；只读引用，47 条中 44 条启用。完整参数保留在 [源规则快照](pcb-rules-source.json)，各板目录有 `rule_mapping.json`、真实 `.kicad_dru`、全局约束和网络类。VCC/GND 映射到 MORI 实际网络；本机没有 P24V，未把它硬套到 3S 电池。

间距对象对、线宽、过孔/孔距、四辐条热焊盘、最小 60° 夹角、阻焊/焊膏和丝印规则已落地。没有新增单项豁免，DRC 的 ignored_checks 为空。实际负例测试证明 R01、R05–R09、R15–R16、R27、R39、R40 会触发违规，结果见 [规则命中测试](reports/rule_probe/verification.json)；那块测试板故意违规，不能制造。

**以下不属于“已全部符合规则”，不能用零 DRC 掩盖：**

| 条目 | 当前证据与状态 | 完成制造前的工作 |
|---|---|---|
| R14 固定 0.499999 mm 转角退让 | `FAIL`：补充几何检查识别到运动/IMU/电源分别 84/22/58 个 H–斜线–V 候选转角，均不是固定 0.5 mm。KiCad 最小夹角检查不能替代该约束。 | 若严格要求所有此类转角一致，需继续局部重排/布线；目前未擅自批准例外。 |
| R11/R12 拓扑/优先级、R35–R37 扇出 | 自动路径优化加关键路径人工布线；未证明与原工具 Shortest/OutOnly 完全等效。164 只过孔均未落在原 0.0254 mm 全局网格的容差内；其中扇出过孔还需分类审核。R33 无 BGA，R34 无 LCC，ICM 是 LGA。 | 需要补充路径/扇出审核或按该网格再排；没有把工具差异标成 PASS。 |
| R30/R31/R45/R46 测试点 | [探测位置表](probe_map.csv)是现有接口焊盘，不是符合直径/网格/覆盖要求的专用针床测试点。 | 确定测试夹具覆盖后增加对应测试点；目前仅支持人工板级调试。 |
| R19 焊膏扩展 +0.05 mm | 保留你的源规则；与 TDK AN000393 建议的约 90% 开口存在冲突，TI 小封装钢网也需单独复核。 | 钢网前明确封装级开口例外/厚度；本轮不导出钢网。 |

R24/R28/R38 在源规则中关闭，未伪称启用。额外保留独立板厂约束（例如 0.25 mm 环宽），不冒充原项目规则。旧原理图的 4 项 KiCad 默认关闭 ERC 项（单次全局标签、四路连接、SPICE 模型、封装过滤）列在逐板报告中；未新增 ERC 排除，未进行 SPICE 验证。

## 原厂与实际核验

TI DCU0008A 焊盘依据 [SN74LVC2G125 数据手册](https://www.ti.com/lit/ds/symlink/sn74lvc2g125.pdf)封装页；ICM 焊盘、禁布与装配建议依据 [TDK ICM-42688-P 原厂页面](https://www.invensense.tdk.com/en-us/products/consumer/icm-42688-p)所列 DS-000347 v1.9 和 AN-000393 v2.4。本地原件为 [ICM 手册](../sources/parts/TDK_ICM42688P_DS000347_v1p9.pdf)及 [TDK 装配指南](../sources/parts/TDK_AN000393_v2p4.pdf)，访问日期 2026-09-22。厂商尺寸不是实物测量。

[本版核验汇总](reports/verification.json)包含原生报告、输入哈希、P1/S2 保留核对、网表比较及补充几何检查。逐板 `reports/MORI_*_P2/` 保留 CLI argv/退出码和实际 ERC/DRC JSON。三板共 1262 段铜线、164 只过孔；通过的是电气 CAD 检查，未测试载流、纹波、温升、机械应力、平衡或续航。

板端铜线的假设与估算见 [P2 铜线计算](reports/copper_estimate.json)，由 [脚本](../calculations/layout_P2_power.py)产生；这不是板厂载流额定值。外部稳压器、吸能电阻、3S 电池/USB-C 充电模块仍沿用原采购/台架门槛，本轮没有补造国内现价或型号确认。

## 机械和装配边界

[P2 机械交接](../handoff/mechanical_P2.json)从本版原生 PCB 提取板框、孔位、每个接插件的位置/旋转/面别和焊盘坐标；机械合同已读至 M1.5，但未覆盖机械任务的文件。特别是电源板 J3、J7、J8、J10、J13 的位置不能继续用 P1 坐标。

- 电源板 80×45 mm 加 16 mm 高电解，仍不适配 44×16×10 mm 的旧电源分配；最新简化框架未完成该板及稳压模块的安装。
- 运动板底面 J6/J8 的插头/拔插空间、WeAct 全堆叠高度、IMU 的 GH 对插高度未闭合。现有 2 个 IMU 安装孔也没有满足 TDK“至少 3 个固定点”的建议，需机械处理。
- 每板 `previews/MORI_*_P2/placement_native.csv` 是 KiCad 原生放置坐标；背面图已经镜像。手工交接 JSON 使用 PCB +X 向右、+Y 向下、F 面 +Z，机器人安装变换由机械任务定义。
- `../mechanical/MORI_*_P2_BARE_BOARD.step` 只有裸板/孔。KiCad 通用封装 3D 外观也不构成购买型号的完整安装包络，不能用于宣称整机无干涉。

当前是本地 **PROTOTYPE REVIEW**。没有采购、下单、提交或推送，没有导出制造 Gerber/钻孔。应先解决上表的规则和装配门槛，再准备下单数据。

## 复核入口

在项目根目录分别执行 `python3 hardware/v1_2/tools/run_layout_P2.py motion check`，将 `motion` 换为 `imu`、`power` 可检查另两块板。然后使用 KiCad Python 执行 `hardware/v1_2/tools/verify_P2.py`。

`export_P2.py <board>` 从现有板重新导出阅读图、坐标和裸板 STEP；`export_readable_review.py P2` 用 bundled Python 重新导出功能原理图。`package_layout_P2.py` 只生成带状态说明的本地阅读包。

**保存的 `.kicad_pcb` 是最终铜线真值。** `layout_P2.py prepare/import`、`refine_P2.py` 和各阶段路由修补脚本是构建过程工具，会清除/重建或修改走线；DSN/SES 不含后续全部手工修正，日常检查不要重导入。不要运行 P1 的全量生成器或用旧 S2/P1 检查报告证明 P2。

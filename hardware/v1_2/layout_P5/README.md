# MORI P5 全新布局与布线

本次四块 PCB 已从零铜线重新摆位和布线，P4 源工程保留。电路、器件型号和逐针网络不变；没有沿用 P4 的走线或过孔 UUID。状态为 **PROTOTYPE / 实物 NOT_TESTED**。

先打开 [逐层查看页面](index.html)，或直接打开下列原生 KiCad 工程。PNG/SVG 是原生 PCB 导出；底层视图已镜像。

| 电路板 | 板框 / 厚度 mm | 层数 | ERC / DRC / 未连接 / 一致性问题 | 原生工程 |
|---|---|---:|---|---|
| 运动承载板 | 70×35×1.6 | 4 | 0 / 0 / 0 / 0 | [MORI_motion_P5](../kicad/MORI_motion_P5/MORI_motion_P5.kicad_pro) |
| IMU 板 | 20×16×1.6 | 2 | 0 / 0 / 0 / 0 | [MORI_imu_P5](../kicad/MORI_imu_P5/MORI_imu_P5.kicad_pro) |
| 电源板 | 80×55×1.6 | 4 | 0 / 0 / 0 / 0 | [MORI_power_P5](../kicad/MORI_power_P5/MORI_power_P5.kicad_pro) |
| Type-C / 电源开关接口板 | 24×25×1.6 | 2 | 0 / 0 / 0 / 0 | [MORI_rear_P5](../kicad/MORI_rear_P5/MORI_rear_P5.kicad_pro) |

KiCad **10.0.6** 实际运行 ERC、DRC、全走线错误、一致性和重新填充检查。命令、返回码及输入文件 SHA-256 位于每板 `reports/MORI_*_P5/check_commands.json`。没有增加 DRC 忽略项。

这次的主要变化：重新分配功能区和连接器朝向；运动板的逻辑器件放在载板背面，按引脚朝外逃线；两组 5V 降压保持就近分区；采样电阻、电容重新对齐；最后逐段去掉短 V 形折返和多余偏移。旧版与新版的逐针网络、零继承铜线及位置差异见 [重建核对](reports/zero_copper_and_pinmap_verification.json)。

**电源板改为四层**：外层主电流/信号，内部两层 GND。二层试版的局部地铜分成多个不相通区域，因此增加公共回流平面。内层没有信号走线；电感和降压芯片的限定投影继续留空。名义铜厚70/35/35/70μm，总厚仍1.6mm；板厂叠层、报价及实物温升未确认。

169个器件均有本体投影检查记录，双面不相关网络下穿候选为0。**这不等于所有器件投影内完全没有铜线**：架高主控模块U100、连接器端子、LGA焊盘和径向电容引脚有明确局部情况。完整记录见 [布线验收与例外](routing_acceptance.md)，不能用DRC为这些情况自动背书。

主电流连接另做了宽度过滤后的真实铜形状连通检查，避免将0.2mm采样线当负载线；结果 [PASS](reports/MORI_power_P5/load_path_audit.json)。此项不证明载流温升、过孔镀铜或制动瞬态通过。

交接文件： [连接器逐针表](connector_pinmap.csv) · [全部器件坐标/朝向](placements.csv) · [带型号的装配表](assembly_parts_with_mpn.csv) · [线束](harness.json) · [机械交接](../handoff/mechanical_P5.json) · [检查总表](reports/verification.json)。

机械交接保留未知项：完整插合高度、弯线空间、实装质量仍未测。电源板前+16/后-3mm是设计限制；后接口24×25mm及插头外伸仍需机械处理。STEP只导出裸板，不冒充完整装配。没有修改机械模型或机械契约。

本次没有重新确认价格/库存。四层电源打样报价、完整成品电池/外部充电方案、插接装配与台架验证仍是制造释放的阻塞项。机械新选扬声器与旧声学BOM的同步单独记入接口冲突，没有在布线任务里静默换件。没有导出Gerber或下单。

复核入口：使用KiCad自带Python运行 `hardware/v1_2/tools/run_layout_P5.py <motion|imu|power|rear> check`。它仅运行检查。其他带摆件/布线动作的脚本是有顺序的工程记录，不要无差别批量重放。

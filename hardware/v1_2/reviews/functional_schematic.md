# 功能电路图 · S2

2026-09-22。S1 的自动连线虽保持网表一致，但绕线和折返过多，图纸不便阅读。S2 将运动板和电源板的电路改为人工指定布局及正交连线；身体 IMU 保留简洁的 SPI / 去耦电路并调整边界。**S2 是图纸表达修订，P1/P2 是 PCB 布局版本，两者不能混用。**

[20 页矢量阅读版](../previews/MORI_S2_Schematic_Review.pdf)按功能块分页，可直接放大；内容从 KiCad 原生 PDF 裁取，未另画一套电路。KiCad 中仍可编辑整张原理图。跨块及部分共享控制信号使用短网标；实际供电符号旁的名称保持原 `/NET` 网络，不新增电源或逻辑器件。

| 图纸 | 原生文件 | 阅读顺序 |
|---|---|---|
| 运动载板 | [原理图](../kicad/MORI_motion_P1/MORI_motion_P1.kicad_sch) · [工程](../kicad/MORI_motion_P1/MORI_motion_P1.kicad_pro) | 01 MCU/GPIO；02 轮驱 TTL；03 头部 TTL；04 物理使能/ARM 锁存；05 发送使能；06 IMU；07 双电源域 UART；08 ADC 滤波；09 5V 输入/按钮/安装。 |
| 电源调理板 | [原理图](../kicad/MORI_power_P1/MORI_power_P1.kicad_sch) · [工程](../kicad/MORI_power_P1/MORI_power_P1.kicad_pro) | 01 电池反接保护及分流器；02 Kelvin 电流采样；03 轮电源；04 头电源；05 外置稳压器输入；06 轮吸能/过压；07 头吸能/过压；08 电压分压；09 插入联锁/VBUS 感知；10 供电边界/安装。 |
| 身体 IMU | [原理图](../kicad/MORI_imu_P1/MORI_imu_P1.kicad_sch) · [工程](../kicad/MORI_imu_P1/MORI_imu_P1.kicad_pro) | SPI 接口到传感器按信号顺序展开，上方供电，下方地，右侧去耦。 |

S2 主要修正：电源输入和输出方向统一；PMOS 反接保护镜像到正确的视觉流向；分压/滤波支路向下；双比较器分开画三角；逻辑使能及串口以短局部路径连接；拉开位号/数值；避免页脚压住电路。蓝色框只表示功能分区，不是器件。

P1 的三个 PCB 保持逐字节不变。器件位号、参数、封装、资料链接、符号与引脚 UUID、完整具名网表保持不变。真实 KiCad 10.0.6 ERC、P1 DRC、未连接及原理图/PCB 差异均为 0，没有新增忽略。详见 [CAD 检查](../reports/cad_validation.json)、[25 项图纸一致性复核](../reports/functional_schematic/verification.json)及 [S2 六份原理图复核](../reports/readability_S2/verification.json)。PDF 的来源哈希和逐页索引见 [导出记录](../reports/readability_S2/export.json)。

旧图分别保存在 `revisions/netlabels_before_functional_20260922/` 和 `revisions/before_readability_S2_20260922/`，不再作为当前查看入口。P2 的原理图也同步了 S2 画法，但 P2 PCB 仍是未完成检查的布局草稿；不能用 P1 的 DRC 通过结果声称 P2 已可制造。原型状态、采购、充电、装配及全部实机验证门槛没有因排图而消失。

## 维护

`tools/readable_schematic.py`定义人工安排的电路；`tools/functional_schematic.py`负责原生符号及输出，默认更新三份 P1 原理图，也可显式传入三个 P2 名称。绘图脚本不写 PCB、项目设置或共享契约。完整 CAD 生成器调用同一排图入口，避免重新生成时回到 S1。

只改图纸时不要运行会清空 PCB 布线的 `native_cad.py`。按 `tools/REPRODUCE.md`运行当前检查，再运行 `tools/export_readable_review.py`生成阅读版。阅读版脚本需要 bundled Python 中的 pypdf / reportlab；图纸本体只需要标准 Python 和本机 KiCad。

如果 KiCad 窗口仍载着旧图，请重新打开磁盘工程，避免把未重载的旧窗口保存覆盖 S2 文件。

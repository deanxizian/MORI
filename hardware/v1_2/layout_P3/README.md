# MORI P3 · 三板重新布局与布线

> **2026-09-23 用户复核：布线方式 FAIL。** 已确认同层线路下穿器件，P3 未满足向外出线要求；原生零 DRC 不代表布局验收通过。本次审查未修改铜线，问题尚未修复。见[逐项审查](body_route_review/README.md)。


2026-09-23，**V1.2-H0.3-P3 / PROTOTYPE / 实机 NOT_TESTED**。运动、身体 IMU 和电源板已重新布局、布线、覆铜。电源板按用户授权扩为 **80×55 mm**，纳入 S3 的两路 TPS54302 5 V 降压。P2/S3 原工程保留。

[可切换板卡、正反面及装配图的预览](previews/index.html) · [真实核验结果](reports/verification.json) · [机械交接](../handoff/mechanical_P3.json)

## 当前原生工程

| 工程 | 板框 mm | ERC | DRC | 未连接 | 原理图差异 | 层数 / 标称铜厚 |
|---|---|---:|---:|---:|---:|---|
| [运动载板](../kicad/MORI_motion_P3/MORI_motion_P3.kicad_pro) | 70×35 | 0 | 0 | 0 | 0 | 2 / 35 μm |
| [身体 IMU 板](../kicad/MORI_imu_P3/MORI_imu_P3.kicad_pro) | 20×16 | 0 | 0 | 0 | 0 | 2 / 35 μm |
| [电源板](../kicad/MORI_power_P3/MORI_power_P3.kicad_pro) | 80×55 | 0 | 0 | 0 | 0 | 2 / 70 μm |

三板均以 1.6 mm 板厚设计，ENIG 为打样目标，铜厚、实际板厚及成本待供应商确认。原生 KiCad **10.0.6** 实际检查包含全部 PCB 警告、所有走线错误、重新覆铜及原理图一致性；各板 DRC `ignored_checks`、单项排除均为空。ERC 保留原有四项默认关闭检查：单次全局标签、四路连接、SPICE 模型、封装过滤，详情在原始报告；未进行 SPICE 验证。

核验脚本另检查原生输入 SHA256、导出图对应的 PCB 哈希、实际 Edge.Cuts、逐网 ref/pin 成员、器件身份/数值/引脚 UUID 及 P2/S3 原件。**32 项 CAD/来源检查 PASS**。这不代表完整源规则、整机装配或台架验证通过。

## 本次布置和走线

- **运动板**：保留 WeAct 插接区域和外部接口针序，重新组织背面逻辑、锁存、串口及滤波组。比较旋转与位置后安排器件朝向，使信号优先从引脚向器件外侧引出，再进入通道。小逻辑器件的局部 GND/电源回流保留必要的本体下方连接；这是缩短回流/去耦的局部例外，不能说所有铜线都避开了本体。
- **IMU 板**：保留 20×16 mm 板框及两孔接口；重新安排 ICM-42688-P 周边引线、去耦与换层。敏感器件本体的禁布区域保留。新布局需重新进入 M1.11 的板下安装与轴向变换复核。
- **电源板**：两路 TPS54302 与各自输入、开关、电感、输出和反馈组分区布置；轮/头功率开关、吸能比较器和采样分开。旋转功率开关，移动门极电阻组、采样分压组及局部去耦，腾出走线通道；删掉重复短支线，合并可直走的折返，并准确对齐过孔中心。高电流主干采用 2 / 1.5 / 1 mm 等宽度，小电流采样/控制支路采用 0.2 mm，不能把采样线宽当成主干额定值。
- 电池 BAT_MON 换层保留两只并联 1.0/0.45 mm 过孔；电机电流不经过 MCU 载板。修复热焊盘辐条、同网急角、地连接和丝印开窗冲突。每板有 P3 PROTOTYPE 标识及连接器位号；电源端子与电解极性可见。

电源 **L60/L70 的 SRP7050TA 焊盘已纠正**：厂家图中的 2.5 mm 是中间间隔，外侧总跨距为 8.4 mm；采用单焊盘 2.95×3.5 mm、中心 ±2.725 mm。依据 [Bourns 原厂数据手册](https://www.bourns.com/docs/product-datasheets/srp7050ta.pdf)，[本地原件](../sources/parts/Bourns_SRP7050TA.pdf)记录于来源索引；这是厂家尺寸，不是实测。

运动/IMU 电路与 P2 相同，电源电路与 S3 相同；本版更改封装、板上布置和铜线，未更改 GPIO 或四执行器/双 MCU 架构。原理图继续采用功能块编排，未恢复网标矩阵式画法。J6 仍为 DNP，不作为同时并联的外部 5 V 电源入口。

2 层选择针对模块载板：DVP、显示 QSPI、USB 差分和 RF 留在购买模块上；三板承担电源、低速控制、UART、SPI 与模拟监测。覆铜不等于连续参考平面；开关回路、SPI 回流、纹波和温升仍需台架检查。

## 用户 KiCad 规则：已落地部分与未闭合部分

只读引用 [deanxizian/KiCad 的 Rules](https://github.com/deanxizian/KiCad/tree/f756532aa67112a9d437c18e8ca00ac8fba2c9b4/Rules)，提交 `f756532a`，47 条中 44 条启用。[源快照](pcb-rules-source.json) SHA256 为 `5d49d0134ca8c32acc41736591db9e839c347a40a2baa061d32c9ce64a7c25b0`。逐板 `rule_mapping.json` 和 `.kicad_dru` 保留参数、网络角色及适用性；没有把 P24V 规则套到 3S 电池。

实际实现包含对象对间距、线宽、过孔/孔距、四辐条热焊盘、最小 60° 夹角、丝印、阻焊/焊膏设置。电源项目继承的五项默认关闭 PCB 检查也已启用，新增暴露的过孔对心问题已修复，没有靠忽略清零。

| 尚未闭合条目 | 当前证据 / 状态 | 后续要求 |
|---|---|---|
| R14 固定 0.499999 mm 转角退让 | **FAIL**：运动/IMU/电源识别到 72/12/93 个 H–斜线–V 候选，其中 70/11/92 个不为该固定值。检测是几何筛查，不等同每段斜线的设计意图。 | 如严格执行固定退让，需继续逐段调整，并处理细间距逃线例外；未批准例外。 |
| R11/R12 拓扑及 R35–R37 扇出 | **NOT_TESTED**：原工具 Shortest/OutOnly 的完整等效性未证明；206 只过孔中 201 只不在原 0.0254 mm 全局网格容差内。这是全过孔筛查，未将全部归类为扇出。 | 分类复核扇出/网格及关键路径，不能由零 DRC 代替。 |
| R30/R31/R45/R46 测试点 | **BLOCKED**：[探测表](probe_map.csv)主要使用接口焊盘，不是符合针床尺寸、网格、覆盖率的专用测试点设计。 | 明确夹具和覆盖；现版支持人工板级调试。 |
| R19 焊膏 +0.05 mm | **BLOCKED**：源规则与 TDK AN000393 约 90% 开口建议存在冲突。 | 明确封装级钢网开口/厚度，复核 TI 小封装；未导出钢网。 |

R24/R28/R38 在源中关闭；保留的独立 0.25 mm 过孔环宽约束不冒充已启用的 R24。**完整源规则符合性仍为 BLOCKED，制造未放行。**

## 结构交接与电气验证边界

[机械交接 JSON](../handoff/mechanical_P3.json)从本版原生 PCB 提取板框、孔位、连接器位置/旋转/面别和逐针坐标，读取机械合同 **M1.11**，未覆盖机械拥有的 `geometry.json` 或 `mechanical_interfaces.json`。

- 电源孔心为 (3,3)、(3,52)、(77,3)、(77,52) mm。坐标为 PCB 左上原点、+X 向右、+Y 向下，装机变换交机械任务。M1.11 已采纳 80×55 的容量，但尚未验证这块完整 P3 装配；+16/-3 mm 高度限制不含对插插头，不能直接当成 P3 已装入证明。
- WeAct 堆叠、运动板背面 J6/J8、IMU 对插高度、电源插头/线缆弯曲和拆装路径仍待复核。IMU 现有两孔不满足 TDK 至少三个固定点的建议，需要机械处理。
- M1.11 新的后部接口小板及独立功能按钮移除属于另一项电气接口变更；本次三板重排保留原针序，没有将那块第四板或新线束混入 P3 已完成范围。
- 各板 `previews/…/placement_native.csv` 是 KiCad 原生坐标。背面预览已镜像；不要再镜像一次。`../mechanical/MORI_*_P3_BARE_BOARD.step` 只有裸板与孔，**不是完整装配模型**。

[铜线及裸板质量估算](reports/layout_power_estimate.json)由[可运行脚本](../calculations/layout_P3_power.py)产生。电源面积比 80×45 增加 22.22%；在所列材料/覆铜假设下，裸板增加约 2.43–2.93 g。50 mm 铜线和并联过孔 DC 估算仅供比较，不是连续载流、温升或整机重心实测。未补造 PCB 报价。

所有上电、电流、纹波、回灌、温升、机械应力、平衡及 60 分钟续航项目仍为 **NOT_TESTED**，遵循[现有测试计划](../test_plan.md)。外部电机/舵机稳压、成品 3S 电池与 USB-C 充电仍有原采购/资料门槛；这块电源板不等于已完成的 USB-C 充电器。

## 复核与文件真值

在项目根目录执行：

```sh
python3 hardware/v1_2/tools/run_layout_P3.py motion check
python3 hardware/v1_2/tools/run_layout_P3.py imu check
python3 hardware/v1_2/tools/run_layout_P3.py power check
python3 hardware/v1_2/tools/export_P3.py motion
python3 hardware/v1_2/tools/export_P3.py imu
python3 hardware/v1_2/tools/export_P3.py power
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 hardware/v1_2/tools/verify_P3.py
python3 hardware/v1_2/calculations/layout_P3_power.py
```

实际命令、时间、退出码和输入哈希在 `reports/MORI_*_P3/check_commands.json`；原始 JSON/日志同目录。保存的 **`.kicad_pcb` 是最终铜线真值**。DSN/SES 及各阶段布线脚本不包含一条完整幂等重建链，不能重导入覆盖最终 PCB。旧版生成/发布脚本也不能覆盖当前契约。

没有采购、下单、提交/推送或实物试验；没有导出制造 Gerber、钻孔或钢网文件。

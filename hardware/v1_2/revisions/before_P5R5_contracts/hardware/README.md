<!-- MORI_V1_2_CURRENT_ENTRY -->
**当前硬件契约：V1.2-H0.5-P5R4 / PROTOTYPE。** [工程入口](v1_2/README.md) · [后接口／IMU审查对照](v1_2/layout_P5R4/index.html) · [逐项处理](v1_2/layout_P5R4/review_disposition.md)。

后接口与IMU更新为P5R4，运动与电源保留P5R3。本轮改善CC保护、TVS支路与IMU去耦、专用Paste和轴标；两板实际ERC/DRC/未连接/原理图差异均0，无忽略检查。板框/孔位/固定连接器/针脚不变，移动器件已交接。外接PD/3S模块未选定、J2.5 RAW源端限流缺失及钢网确认仍BLOCKED；实物NOT_TESTED。布线局部例外见报告，不能称全部规则通过。以下A0仅为历史。
<!-- MORI_V1_2_CURRENT_ENTRY_END -->

# MORI 硬件开发工程 · Rev A0.4

**当前继续设计的增量在 [A0.5](revisions/A0.5/README.md)。** A0.4档案保留供追溯。A0.5修复了基线固件的LEDC初始化遗漏，新增舵机断电隔离，并提供独立尺寸校核模型和试打件；实际使用与验证应结合A0.5说明。软件合并读取 [A0.5增量通知](handoff/A0.5_硬件增量通知.md)。

**已建立可继续实施的模块样机工程；尚未通过实物验证，不能下单生产承载板。** 机械基准来自现有 `../params.json`、`../reports/derived.json`，原 Blender / STL / 参数没有被硬件任务改写。内部占位不能直接当成采购接口。

先打开 [软件并行任务提示词](handoff/软件调试任务提示词.md)，交接版 **HW-SW-0.4**；基线固件和接线随快照提供。软件任务在 `software/` 工作，硬件任务拥有 `hardware/`，避免同时修改同一文件。

## 一套主路线

|用途|具体选择|当前结论|
|---|---|---|
|主控|ESP32-S3-DevKitC-1-N8R8 v1.1|单主控；先外置台架，现有主控占位不适配|
|轮电机×2|Pololu **4863**，25D MP12V、20.4086667:1、48 CPR|2S降额运行、限流；可买台架一对，整机性能待辨识|
|编码器电平|SN74LVC14AD，3.3V供电|编码器需5V，A/B经此转换后进PCNT；禁止5V直入GPIO|
|双驱动|Pololu2130 DRV8833|修改nSLEEP默认状态及0.39Ω限流，必须实测|
|IMU / 电流|Adafruit4438 LSM6DSOX / Adafruit904 INA219|刚性机身IMU；电流是电机母线量，不是相电流|
|头部|DFRobot SER0037 270°位置舵机|行程覆盖210°需求；安装耳、花键和脉宽待验|
|屏幕|Waveshare19192 GC9A01 240²|台架主选，有效Ø32.4；不满足Ø60目标，遮罩变更未批准/实施|
|电池|ANSMANN2447-0105，2S1P、7.2V3.35Ah|候选39×71×18；原40×70×20预留仍不适配，暂缓采购|
|电源|逻辑Pololu2831 D24V10F5；头部2858 D24V22F5|分支5V；电机直接用受保护2S母线|
|充电|独立8.4V CC/CV；CH-L7412SM 1.2A作为待匹配候选|必须获得电池充电电流/均衡说明后才购买或使用；没有内置充电板|

预算按海外目录价与明确标注的美元预留合计：最小平衡验证约 **US$407.24**；完整互动样机含一次性费用约 **US$459.08**。这是规划数，含尚未放行采购的候选，不含运费、关税、工具，不代表用户接受了预算。详情见 [BOM](bom.csv)。

计算质量约 **1.010 kg**，质量不确定范围约0.81–1.21kg；0.3m/s需60.31rpm。6.6V、65%输出限制、慢20%电机与0.85皮带效率假设下，每轮可用约0.0381N·m；标称质量8°瞬时恢复筛选约0.026N·m。恢复时加速、惯量变化和延迟仍可能耗尽余量，因此这些数值不证明能自平衡。

## 查看与复现

- [尺寸冲突与机械变更单](mechanical_change_requests.md)、[实际接口JSON](mechanical_interfaces.json)、[填写后的选型尺寸表](dimensions/selection_size_checklist.csv)
- [架构和实时资源](architecture.md)、[电机计算和选择](motor_selection.md)、[屏幕与IMU取舍](display_imu_selection.md)、[供电预算](power_budget.md)
- [引脚](pinmap.csv)、[完整接线](wiring.csv)、[安全条件](safety.md)、[A–H测试计划](test_plan.md)
- [KiCad原生工程说明](kicad/README.md)、[固件操作与构建](firmware/README.md)
- [来源及真实性说明](sources.md)、[验证状态](reports/verification.md)

模块验证进入承载板布线的条件：电池/充电/回灌规格闭环、A–F实测通过、头和轮传动实物定型、实测质量/重心、已验证的GPIO与安装坐标、零机械干涉。进入自由平衡必须另过G；PCB ERC/DRC不能替代它。

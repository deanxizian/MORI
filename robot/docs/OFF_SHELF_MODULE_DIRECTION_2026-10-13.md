> 阶段采用记录，保留当时输入和检查范围；当前进度以 [CURRENT_STATUS](CURRENT_STATUS.md) 为准。

# 成品模块方向确认 · 2026-10-13

状态：**用户已批准，机械主模型已更新为 M1.56；电气适配和完整线束未完成。** 本轮未提交 PR，原生硬件工程与合同保持只读。

## 已确认并采用

- 最终控制器保留 WeAct STM32F412，不迁入样品车树莓派。
- 使用 Waveshare UPS Module 3S，接受 DC 圆口充电；按用户要求直接使用样品项目原厂 CAD。
- DFRobot SEN0693／BMI323 未焊排针，使用板载小插座。
- S288 两轮使用 UPS BAT 电池电压输出；SCS0009 两头部舵机通过微雪 6 V Buck 降压。
- WeAct＋载板整组居中，IMU 和 Buck 放两侧；旧自制电源板不再作为机械占位。
- UPS 采用无托盘直固：后移 12 mm，四座并入 Load_Frame，四枚 M3×25 穿栓和四枚 M3 螺母。移除 Battery_Tray 和原侧锁五金。

主控组 14 件刚性旋转 90°，载板中心 X0／Y−6、降低 1 mm；BMI323 X−30／Y0，Buck X30／Y0。没有新增独立打印支架，本体打印件 16→15。UPS 维修需打开前后身体壳、托住组件，再拆螺栓螺母。短工具轴向进入和名义取出检查通过，完整扳手摆动／手部与带线操作未验证。

当前[主模型与图册](../mechanical/index.html)、[采用记录](M1_56_OFF_SHELF_ADOPTION.md)、[动画](../mechanical/animation/index.html)已经同步。原先的[直固候选](../mechanical/studies/off_shelf_modules_20261013/controller_center/ups_mount_review/direct_index.html)作为批准来源保留；可拆托盘、上层旧位置与旧“尚未应用”候选页面仅是历史研究，不代表当前状态。

## 精度与接口边界

UPS 原厂简化 CAD 为 60×93×23.1 mm，完整电芯／绝缘与端口装件待复核。BMI323 保留原小插座曲面。6 V Buck 暂借官方同系列 7.2 V CAD，其实际装件一致性为 ASSUMED，模型标橙色。原厂来源及哈希见[记录](../mechanical/sources/off_shelf_20261013/source_receipt.json)。

当前实体检查覆盖确认的固定与装配范围，不构成完整电气、柔性线束或实物资格。后接口板仍保留历史几何，DC 入口与安全链未定型。BMI323 小插座 I²C 与旧载板 IMU SPI 口需要重新适配。

原 11 处插头容量研究只覆盖名义包络。新增 WeAct USB 检查发现旧 J5 向左出线会挡 USB：拆前壳后，小型 10×4.5×16 mm 假设 USB 插头包络可进入；J5 右转只在小包络下可避让，大包络仍不通过。没有采用完整新线束或选定实际 USB 线。[当前检查记录](../mechanical/reports/off_shelf_usb_capacity.json)

随后以已保存的 M1.56 重算 J5：修正右转弧段多边形绕向并断言实体非空、连通，R6／起始直段1 mm／后直段12 mm 的四线容量通过；小 USB 尾壳拔出41个位置、固定桥垂直装入61个位置通过。[图文记录与来源](../mechanical/studies/off_shelf_modules_20261013/dc_interface_M1_56/index.html#signal)。

DC 安装尺寸按用户指示从可行性验证车复用。R41 与最新 R55 完整参考模型中的插座／螺母网格一致；沿用 Ø8 试孔、7 mm 螺纹段、25 mm 尾部占位，只有螺母 AF 约10.5 mm 属于用户近似测量。后壳 X0／Z130 的局部候选空间和无软线拆壳路径通过；但原占位体前后端均大于试孔，不能证明真实插座装入，实际安装为 BLOCKED。未把该候选写入正式模型、STL 或动画，也未重复请求测量。详见[充电口候选](../mechanical/studies/off_shelf_modules_20261013/dc_interface_M1_56/index.html#dc)。

## 电源定型约束

“十二伏”对应约 9–12.6 V 的 3S 电池电压，不是稳压 12 V。微雪文档将 BAT / XH 输出标为 **2 A**，与 5 V / 5 A 输出分开。两只 S288 按厂家最大线电流算术合计 1.68 A；再加头部 Buck 的输入电流，不能直接判为够用。[UPS 官方说明](https://www.waveshare.com/wiki/UPS_Module_3S)，[宇树官方参数](https://www.unitree.com/DigitalServo/)。

独立核算见 [power_budget.json](../mechanical/studies/off_shelf_modules_20261013/power_budget.json)：在 12.6 V、理想无损转换下，以旧 SCS0009 文档每只 6 V / 0.4 A 额定参考，与两轮最大线电流同时出现的情形估算，共 2.061 A；每只 1 A 堵转参考则为 2.632 A。头部旧文档尚未与到货 SC-0090-C001 修订完全匹配，这些是定容情形，不是整机实测。此 UPS 不能据现有资料直接作为不限同时负载的成品方案放行。

需要继续核定 BAT 支路载流、精确舵机版本/并发工况、Buck 持续电流与温升、低电压压降、满电制动回灌，以及执行器物理断电/充电互锁。不能通过省略这些功能或绕开电池保护使布局成立。若需更换 UPS 或调整已确认结构，应先提供具体方案供用户确认。

硬件适配清单保存在[本地研究记录](../mechanical/studies/off_shelf_modules_20261013/hardware_requirements.md)，没有向其他对话发送，也不构成新电气合同或制造发布。

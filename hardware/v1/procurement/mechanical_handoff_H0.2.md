# H0.2 国内选型机械交接

本次更新供应商公开包络及采购状态；没有改机械分配尺寸/现有模型。所有实际测量为NOT_TESTED。H0.1惯量结果不代表新件。

|器件|采购型号|供应商尺寸mm|供应商净质量g|下一步|
|---|---|---|---|---|
|wheel_foc|DFRobot FIT1034 / 2804 BLDC+AS5600|{"diameter": 34.5, "length": 19.5, "shaft_diameter": 8, "hollow_bore_range": [5.4, 6.5]}|未知|BLOCKED: FIT1034 Ø34.5/8mm轴不兼容现Ø25/4mm；连续轮端扭矩、皮带减速比及低压电源未冻结。|
|foc_driver_each|DFRobot DRI0058 / SimpleFOCmini|{"pcb_xy": [26, 21.5], "assembled_z": null}|未知|BLOCKED: 两板26×21.5，高度及端子净空待核；供电/控制路线未通过。|
|yaw_servo|DFRobot SER0046 — 9g 270度金属带模拟值反馈舵机|{"vendor_nominal_xyz": [22.9, 12.2, 32.5], "including_mounting_ears": null}|12|BLOCKED: SER0046名义22.9×12.2×32.5，含耳/舵盘图仍缺；不可套用FT90M-FB孔位。|
|pitch_servo|DFRobot SER0046 — 9g 270度金属带模拟值反馈舵机|{"vendor_nominal_xyz": [22.9, 12.2, 32.5], "including_mounting_ears": null}|12|BLOCKED: SER0046名义高度32.5超过原24×12×22预留；组合角度与有限线缆回环需重算。|
|body_imu|DFRobot SEN0250 / Gravity BMI160 6轴IMU|{"pcb_xy": [22, 27], "assembled_z": null}|未知|BLOCKED: SEN0250 PCB22×27，不可直接替换原26×18预留；连接器/INT接线净空未知。|
|display|Spotpear 0201213 / 1.28inch-LCD-Module / GC9A01|{"active_diameter": 32.4, "glass_diameter": 37.5, "pcb_xy": [40.4, 37.5], "assembled_z": null}|未知|BLOCKED: 真实显示Ø32.4，PCB40.4×37.5；原模型Ø58显示占位必须改，不能缩放硬件。|
|camera|Spotpear 0204002 / OV5640-Camera-Board-(A)|{"pcb_xy": [35.7, 23.9], "lens_and_connector_z": null}|未知|BLOCKED: OV5640-A板35.7×23.9；原14×8×10不再适用；镜头/排针高度和布置待确认。|
|battery|亚博智能 7.4V 2S 2000mAh 高倍率电池（官方选项）|{"x": 37, "y": 67, "z": 22}|115|BLOCKED: 亚博包37×67×22/115g；厚度已用满原22mm预留，需减振、线缆出线和拔插空间。|
|speaker|DFRobot FIT0825 / 1W扬声器（带音腔）|{"x": 35, "y": 20, "z": 3.5, "dimension_tolerance": 0.2, "wire_length": 150}|未知|BLOCKED: FIT0825 35×20×3.5侧发声带声腔，需改矩形固定和声道。|

孔距、固定耳、连接器总高没有资料就留null；模型预留不是厂商实物尺寸。新增/变更件的安装孔先不定。其余板框建议沿用原交接作为占位，未通过即不冻结PCB板框。

没有切换成三电机。两轮+两头部舵机仍四执行器，两颗ESP32-S3-WROOM-1-N16R8仍为双主控。FOC3PWM驱动不包含第三颗主控；其闭环资源必须重新审核。

原始机械210°要求来自旧传动；当前V1 yaw±60°/pitch−20..25°的舵机轴到关节比仍要明确。不能看到商品标题270°就结束限位校核。

公开价格/供货证据见[BOM核验](BOM_国内采购核验.md)。电气契约的procurement_update只发布候选变更，不授权用旧pinmap接线。

补充筛选计算见[calculation_checks.json](calculation_checks.json)：2S低压直接带DRI0058不合格；300g·cm仅为约0.0294N·m，连续能力未知。现x=40.5mm低位皮带轮平面按理想球壳筛选向下半径空间约7.75mm，不能直接换成半径19.1mm的60齿GT2轮来获得3:1减速；实际带侧切壳网格仍待碰撞检查。

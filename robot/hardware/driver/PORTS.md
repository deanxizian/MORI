# R108P 接插件与端口

本表为未制造的 R108P 候选，完整针位见 [connector_pins_R108P.csv](connector_pins_R108P.csv)。原 BT 表的 91 个针位已逐项与 R108P 原生板的焊盘网络、BOM 型号和封装核对，结果见[原生针位复查](publication/connector_readback.json)。这不是物理对插或电流能力验证，也没有晋升 IF-C1-R4 正式合同。

| 位号 / 用途 | 板端完整型号 / 立创料号 | 接口及信号 |
|---|---|---|
| J401 轮舵机串接链 | JST S3B-PH-K-S(LF)(SN) / C157929 | PH 2.0 mm 侧出 3P；1=DATA，2=WHEEL_VM，3=GND；受控 UPS 电池电压，非固定 12 V |
| J402 头部两舵机 | HCTL HC-5264-3AW / C2845826 | 5264 2.5 mm 侧出 3P；1=GND，2=HEAD_VM（6 V 候选），3=DATA；线束 Y 分支到 yaw/pitch |
| J501 CAM UART | JST SM04B-SRSS-TB(LF)(SN) / C160404 | SH 1.0 mm 侧出 4P；1=CAM RX44，2=CAM TX43，3=CAM_3V3_REF，4=GND；第三针为电平参考，不是主供电 |
| J502 身体 IMU | JST SM05B-SRSS-TB(LF)(SN) / C136657 | SH 1.0 mm 侧出 5P；1=空，2=SDA，3=SCL，4=GND，5=MOTION_3V3 |
| J701 UPS 电源与监测 | JST B6B-XH-A(LF)(SN) / C144397 | XH 2.5 mm 顶插 6P；1=UPS 5V，2=5V 回流 GND，3=SDA，4=SCL，5=BAT 回流 GND，6=UPS BAT；两条电源地线分别保留 |
| J702 CAM BAT | JST S2B-PH-K-S(LF)(SN) / C173752 | PH 2.0 mm 侧出 2P；1=CAM_BAT_OUT（约 3.87 V 候选），2=GND；禁止接 UPS 5V 或 3S 电池 |
| J101、J102 核心板 A–D | XKB X6521FV-2x15-C85D32 / C2883988 | 两个 2×15、2.54 mm、8.5 mm 高排母；针位详见 CSV |
| J105 核心板 E | HCTL PM254-2-04-Z-8.5 / C2897405 | 2×4、2.54 mm、8.5 mm 高排母；WeAct 元件朝上、排针向下；针序不可套用镜像通用排母 |

配对线壳、端子、候选线规与设备端不确定项见[线束表](harness/README.md)。设备端 CAM BAT 壳型号、实际压接/插合、线长与整机走线尚未完成；轮链通过电流和温升未验证。J701 顶部拔插与核心板堆叠的完整操作空间仍待机械复核。针号必须按厂家端面图和 1 脚标记辨认，不能以照片左右代替。

这里保留原核价料号，不声称 2026-10-25 已重新确认现价或库存。

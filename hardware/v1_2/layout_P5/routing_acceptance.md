# P5 布线验收与例外

原生检查 PASS；逐组件双面本体检查没有发现不相关网络下穿。完整47条源规则与布线外观的最终验收没有被自动标为PASS。

来源：`/Users/dean/Documents/KiCad/Rules/pcb-rules.json`；GitHub `deanxizian/KiCad`，记录提交`f756532aa67112a9d437c18e8ca00ac8fba2c9b4`。快照SHA-256：`5d49d0134ca8c32acc41736591db9e839c347a40a2baa061d32c9ce64a7c25b0`。47条中44条启用。

## 实际检查边界

线宽、间距、孔径、物理via/pad间距、四辐条热焊盘、最小交汇角和可表达的对象范围由项目原生规则执行；R13限制内层不得走信号。R14编辑倒角、R33–37扇出/布线策略及夹具/装配条件不能仅靠DRC证明，映射见 [逐条源规则](source_rule_matrix.md)。

本体规则同时作用于F/B两面，电源/GND没有全局豁免。先扣除真实焊盘和逐针向外通道，本体核心禁止走线；不相关网络即使经过通道也被禁止。填充地平面与信号线分开检查。此几何检查使用原生封装Fab图形和0.025mm采样，仍需结合厂商完整装配包络复核。

## 局部情况逐项登记

U100保持原有架高可拆模块架构；载板内的器件/线位于它的投影内。模块完整投影和实际安装净空不同，但没有实物插座高度，不能宣称这个机械间隙已合格。要彻底取消U100投影下的全部器件/走线，需更改承载架构或板框；本次未擅自改变模块。

下表为每个例外的精确位号和网络；逐线UUID、坐标和估算投影内长度见 [机器可读记录](reports/body_escape_exceptions.json)。普通SMD器件不授予按电源/GND网名分类的豁免。

| 板 | 位号 | 网络 | 说明 |
|---|---|---|---|
| MORI_motion_P5 | J1 | +5V_MOTION | 自身焊盘/端子到外沿的限定出口；不允许不相关网络借道 |
| MORI_motion_P5 | J2 | S288_BUS | 自身焊盘/端子到外沿的限定出口；不允许不相关网络借道 |
| MORI_motion_P5 | J3 | HEAD_BUS | 自身焊盘/端子到外沿的限定出口；不允许不相关网络借道 |
| MORI_motion_P5 | J4 | IMU_CS, IMU_DRDY, IMU_MISO, IMU_MOSI, IMU_SCK | 自身焊盘/端子到外沿的限定出口；不允许不相关网络借道 |
| MORI_motion_P5 | J5 | CAM_3V3, CAM_RX, CAM_TX | 自身焊盘/端子到外沿的限定出口；不允许不相关网络借道 |
| MORI_motion_P5 | J6 | USER_KEY_N | 自身焊盘/端子到外沿的限定出口；不允许不相关网络借道 |
| MORI_motion_P5 | J7 | ARM_Q, BAT_ADC_IN, CHG_N, CURRENT_ADC_IN, FAULT_N, WHEEL_ADC_IN | 自身焊盘/端子到外沿的限定出口；不允许不相关网络借道 |
| MORI_motion_P5 | J8 | CLR_N, LOOP_3V3 | 自身焊盘/端子到外沿的限定出口；不允许不相关网络借道 |
| MORI_motion_P5 | U100 | +3V3, +5V_MOTION, ARM_CLK, ARM_FEEDBACK, ARM_Q, ARM_Q_N, BAT_ADC, BAT_ADC_IN, CAM_3V3, CAM_RX, CAM_RX_BUF, CAM_TX, CHG_N, CLR_N, CURRENT_ADC, CURRENT_ADC_IN, FAULT_N, GND, HEAD_BUS, HEAD_OE_N, HEAD_OE_REQ_N, HEAD_RX, HEAD_TX, HEAD_TX_BUF, IMU_CS, IMU_CS_M, IMU_DRDY, IMU_MISO, IMU_MOSI, IMU_MOSI_M, IMU_SCK, IMU_SCK_M, LINK_RX, LINK_TX, LOOP_3V3, NRST, S288_BUS, S288_OE_N, S288_OE_REQ_N, S288_RX, S288_TX, S288_TX_BUF, USER_KEY_N, WHEEL_ADC, WHEEL_ADC_IN | 架高模块承载架构，安装净空未验证 |
| MORI_imu_P5 | J1 | +3V3, CS_N, DRDY, MISO, MOSI, SCK | 自身焊盘/端子到外沿的限定出口；不允许不相关网络借道 |
| MORI_imu_P5 | U1 | +3V3, CS_N, DRDY, GND, MISO_IC, MOSI, SCK | 自身焊盘/端子到外沿的限定出口；不允许不相关网络借道 |
| MORI_power_P5 | C10 | GND, W_VM | 自身焊盘/端子到外沿的限定出口；不允许不相关网络借道 |
| MORI_power_P5 | C30 | GND, H_VM | 自身焊盘/端子到外沿的限定出口；不允许不相关网络借道 |
| MORI_power_P5 | D40 | H_BRAKE_GATE | 自身焊盘/端子到外沿的限定出口；不允许不相关网络借道 |
| MORI_power_P5 | J1 | GND, PACK_FUSED | 自身焊盘/端子到外沿的限定出口；不允许不相关网络借道 |
| MORI_power_P5 | J10 | +3V3, ARM_Q, BAT_ADC, CHG_N, CURRENT_ADC, FAULT_N, WHEEL_ADC | 自身焊盘/端子到外沿的限定出口；不允许不相关网络借道 |
| MORI_power_P5 | J11 | W_DUMP_D, W_VM | 自身焊盘/端子到外沿的限定出口；不允许不相关网络借道 |
| MORI_power_P5 | J12 | H_DUMP_D, H_VM | 自身焊盘/端子到外沿的限定出口；不允许不相关网络借道 |
| MORI_power_P5 | J13 | GND, W_BUS | 自身焊盘/端子到外沿的限定出口；不允许不相关网络借道 |
| MORI_power_P5 | J14 | GND, H_BUS | 自身焊盘/端子到外沿的限定出口；不允许不相关网络借道 |
| MORI_power_P5 | J15 | CHG_N, GND | 自身焊盘/端子到外沿的限定出口；不允许不相关网络借道 |
| MORI_power_P5 | J16 | GND, VBUS_CHARGE | 自身焊盘/端子到外沿的限定出口；不允许不相关网络借道 |
| MORI_power_P5 | J17 | +5V_MOTION | 自身焊盘/端子到外沿的限定出口；不允许不相关网络借道 |
| MORI_power_P5 | J18 | +5V_CAM, GND | 自身焊盘/端子到外沿的限定出口；不允许不相关网络借道 |
| MORI_power_P5 | J19 | GND, MASTER_RETURN | 自身焊盘/端子到外沿的限定出口；不允许不相关网络借道 |
| MORI_power_P5 | J2 | BAT_MON, GND | 自身焊盘/端子到外沿的限定出口；不允许不相关网络借道 |
| MORI_power_P5 | J3 | W9_IN | 自身焊盘/端子到外沿的限定出口；不允许不相关网络借道 |
| MORI_power_P5 | J4 | BAT_MON, GND | 自身焊盘/端子到外沿的限定出口；不允许不相关网络借道 |
| MORI_power_P5 | J5 | GND, H6_IN | 自身焊盘/端子到外沿的限定出口；不允许不相关网络借道 |
| MORI_power_P5 | J6 | BAT_MON, GND | 自身焊盘/端子到外沿的限定出口；不允许不相关网络借道 |
| MORI_power_P5 | J7 | GND, W_BUS, W_VM | 自身焊盘/端子到外沿的限定出口；不允许不相关网络借道 |
| MORI_power_P5 | J8 | W_BUS, W_VM | 自身焊盘/端子到外沿的限定出口；不允许不相关网络借道 |
| MORI_power_P5 | J9 | GND, H_BUS, H_VM | 自身焊盘/端子到外沿的限定出口；不允许不相关网络借道 |
| MORI_power_P5 | JP60 | M5_EN | 自身焊盘/端子到外沿的限定出口；不允许不相关网络借道 |
| MORI_power_P5 | JP70 | C5_EN, GND | 自身焊盘/端子到外沿的限定出口；不允许不相关网络借道 |
| MORI_rear_P5 | D2 | CC1 | 自身焊盘/端子到外沿的限定出口；不允许不相关网络借道 |
| MORI_rear_P5 | D3 | CC2 | 自身焊盘/端子到外沿的限定出口；不允许不相关网络借道 |
| MORI_rear_P5 | J2 | CC1, CC2, VBUS_FUSED, VBUS_RAW | 自身焊盘/端子到外沿的限定出口；不允许不相关网络借道 |
| MORI_rear_P5 | J3 | CLR_N, LOOP_3V3, MASTER_RETURN | 自身焊盘/端子到外沿的限定出口；不允许不相关网络借道 |

## 转角与平滑性

重新对齐采样RC、移动EN过孔、拉直W_SENSE通道、重新处理CLR_N端子入口，并用KiCad逐次检查整段简化。机械固定接口或紧邻去耦的局部走线不得仅为直线外观而破坏返回路径。

针对R14，已将可行的独立直角改为0.499999mm倒角。检测范围为自由90°拐角；不把焊盘落点、过孔落点和真实支路交汇混作普通拐角。它也不能证明所有长对角线都等价于源编辑器的倒角设置。

仍保留IMU U1右侧/GND的两处紧凑引出拐角，坐标(11.62,8.85)、(11.62,9.85)mm。局部直段只有0.4575mm；按精确0.499999mm切角会进入LGA本体/焊盘出口，扩大地回路也与紧邻引出的目的冲突。因此精确R14符合性保留为FAIL/局部例外，**没有修改源R14数值或以DRC=0抹去它**。相关记录为 `reports/MORI_imu_P5/R14_corner_review.json` 和 `imu_ground_first.json`。

## 热焊盘与回流

后接口USB1的四个SH屏蔽壳焊脚为直接地铜连接，明确覆盖源R25热焊盘连接方式；目的为本地屏蔽/ESD回流，焊接热工艺和ESD仍NOT_TESTED。精确覆盖规则在该原生项目中，未使用隐藏错误列表。

运动板U100的C2/C4/C6/D5/D6地脚及C1供电脚使用指定平面/相邻同网针脚连接，外层局部退让铜皮，避免额外的残缺热连接；仍保留所连接平面的四辐条规则。电源JP70.2的附加顶层铜皮退让，实际由通孔连接B/In1/In2地铜；四辐条要求没有降低。

## 结论范围

P5是已完成布线并通过原生检查的可编辑原型。完整源规则等价性、用户外观验收、完整机械插合、载流/温升/EMC/电池/动态平衡/续航均不能由上述检查推定通过；无生产/采购释放。

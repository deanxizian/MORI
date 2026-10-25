# 硬件

当前成品为 **成品模块 + 一块自制驱动/载板**。原自制电源、IMU、后接口板已退出设计方向。

| 部分 | 当前选择/入口 |
|---|---|
| 自制驱动/载板 | [C3 R98I](driver/README.md)，45 项未连接，不可制造 |
| 主控 | WeAct STM32F412RET6 64Pin V1.1 |
| UPS | 微雪 UPS Module 3S，原配 DC 口与总开关 |
| IMU | DFRobot BMI323 / SEN0693，使用板载小插座 |
| 头部 | 微雪 CAM33700 / OV3660、1.85inch Touch LCD Module / LCD35079 |
| 舵机 | S288 ×2、SCS0009 SC-0090-C001 ×2 |
| 音频 | CAM 板载音频 + SP3040 喇叭 |

[采购记录](../mechanical/procurement/采购记录.md)记录已买状态和当时价格；[当前板 BOM](driver/bom_candidate.csv)是尚未发布制造的开发候选；[线束表](driver/harness/README.md)未给裁切长度。

正式共享合同仍为 [IF-C1-R4](../contracts/components.json)，C3 R98I 还未晋升合同。主模型是 M1.58，旧载板/外置 Buck 尚未替换。旧多板数据收在 [机械构建参考](../mechanical/input_assets/pcb_reference/README.md)，不是当前采购列表。

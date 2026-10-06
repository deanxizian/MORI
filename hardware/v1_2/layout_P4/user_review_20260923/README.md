# P4 用户圈选复核与整改

状态：**FAIL**。保留 `before/` 原生项目快照和 `baseline.json` 哈希。

已确认前次附加审查漏掉最短拓扑、抖动、短折返与完整引脚逃线。对面铜层和连接器自身网络不能自动放行；这属于工程要求未满足，并非只等待用户审美确认。

圈选涉及 ARM_CLK、LINK_RX、5V_MOTION／FAULT_N 和 ARM_Q。坐标与失效项见 `review.json`，原生走线与焊盘记录见 `motion_geometry_before.json`。整改进行中；尚不声称已全部修复。

# MORI 双 MCU 接口 V1-H0.1（候选协议，可先做主机测试）

正式固件由任务 3 维护。本文定义通信边界，不新增运行固件。运动 MCU 永远独立处理机身 IMU、轮反馈、限幅和本机故障；交互 MCU 只能发有期限的导航/头部目标。传输为 460800 baud、8N1、全双工 UART，3.3V 两个独立电源域经带断电隔离的电平转换；两域共地、共电池，并非完全独立冗余。

固定头部 30 字节，负载 0–96 字节，末尾 CRC 2 字节；多字节字段统一 little-endian。CRC 覆盖 magic 到负载尾端，CRC-16/CCITT-FALSE，poly 0x1021、init 0xFFFF、refin/refout=false、xorout=0；`123456789` 检查值 0x29B1，在线字节 B1 29。

| 偏移 | 字节 | 字段 |
|---|---:|---|
| 0 | 2 | magic A5 5A |
| 2 | 1 | version=1 |
| 3 | 1 | message_type |
| 4 | 2 | payload_length ≤96 |
| 6 | 8 | sender_boot_nonce（每次启动随机新值） |
| 14 | 4 | seq 单调增加；即将回绕前建立新会话 |
| 18 | 8 | sender_monotonic_us（不是墙上时间） |
| 26 | 2 | requested_lease_ms；最大300 |
| 28 | 2 | flags；未知位拒绝 |
| 30 | N | payload |
| 30+N | 2 | CRC |

类型：0x01 HELLO、0x02 HEARTBEAT、0x10 SET_GOAL、0x11 STOP_MOTION、0x12 SET_HEAD、0x20 STATE、0x21 FAULT。所有运动类负载首先带 `destination_motion_boot_nonce:uint64`，随后才是目标；旧运动 MCU 会话的命令不得在重启后生效。SET_GOAL 余下字段为 `velocity_mm_s:int16, yaw_rate_mrad_s:int16, observation_age_at_send_ms:uint16, goal_id:uint32`。SI 转换在解析边界进行，内部 m/s、rad/s。SET_HEAD 为 `yaw_mrad:int16,pitch_mrad:int16,max_rate_mrad_s:uint16,goal_id:uint32`，机械范围见共享契约。未定义的长度拒收，不能容忍自动截断。

HEARTBEAT 每50ms；连续200ms没有有效同会话心跳则导航目标归零。SET_GOAL 到期时间取本机接收时刻加 `min(lease,300ms)`，与心跳失联时限取先到者。CRC错、版本错、长度错、重复/倒退seq、不同boot_nonce、未知flags、未知类型、ACK、诊断包，均不得续租。HELLO不解除物理锁存，不恢复旧目标；交互重启后先握手，再接受新的明确目标。运动 MCU 重启一律禁用输出，需本地解锁。

视觉目标需观测新鲜度≤250ms。两机未做时间同步时，不直接相减各自时间戳：使用交互给出的发送时观测年龄，叠加已测最坏队列/传输延迟；延迟上界未知则拒绝依赖视觉的移动目标。上电可做时间同步估计偏移与误差；误差必须计入年龄。摄像头或推理堵塞时不得反复发送“新时间戳、旧画面”。初始导航速度≤0.10m/s、单次目标路段≤0.30m；这个限制不直接裁剪平衡控制器的瞬时修正速度。

接收缓冲有固定上限，先检长度再分配。过载只保留完整且最新的合法目标，诊断日志限流；运动控制任务不得等待串口队列、网络、图像、文件写入。CRC只是链路差错检测，不是身份认证。

状态机必须区别：

- `BALANCING + STOP_MOTION`：目标速度归零，机身健康时继续本地平衡，头部减速到安全姿态。
- `DISARMED / DOCKED_MAINTENANCE`：执行器断能，必须托架支撑；对话按钮不能触发未支撑的运动 MCU 复位。
- `FAULT_LATCHED`：IMU过期、驱动关键故障、过流/过温、不可恢复倾倒等，硬件禁止执行器并锁存。清故障不自动解锁。
- `INTERACTION_OFF/RESET`：运动轨继续供电，链路隔离防反向供电；失联只取消导航。共电池压降仍可能同时击穿两域，不能宣传安全冗余。

协议主机测试必须覆盖所有帧切分边界、随机噪声/CRC破坏、超长负载、重复包、两端重启、序号回绕、洪泛、阻塞发送、超时竞态、旧会话重放、维护禁止和功能按钮。此处只给协议，正式实现和测试放任务 3 目录。

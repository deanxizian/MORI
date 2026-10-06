# MORI/2 软件契约 1.0

`command_spec.json` 是命令目录、参数类型、数值范围、权限、最长有效期的唯一软件定义。
`protocol.py` / `protocol.ts` 严格校验，`generate.py` 生成 JSON Schema 与嵌入式命令编号/数值校验；
`test_vectors.json` 在 Python 与 TS 跑同一批有效/无效样本。C 的数值子集另外做交叉 CRC 与属性测试。
机械值以 `mechanical_interfaces.json` 与 `../config/geometry.json` 为准，本目录软件协议不重定义孔位/器件尺寸。

## 命令与仲裁

一个消息只包含以下字段，额外/缺少字段、NaN/Inf、布尔冒充数字、范围溢出均拒绝。
原始 JSON 最大 4096 UTF-8 字节；后端额外拒绝重复 JSON 键、截断、非法 Unicode/递归对象。

```json
{"protocol":"MORI/2","device_id":"mori-sim-01","session_id":"从状态取得","command_id":"每个意图唯一ID","client_id":"配对返回ID","source":"console","permissions":["control"],"type":"SET_VELOCITY","params":{"v_m_s":0.1,"yaw_rad_s":0},"sequence":1,"sent_at_ms":100,"basis_device_ms":100,"valid_for_ms":300}
```

上例 ID 说明是占位文字，实际 ID 必须 `[a-zA-Z0-9_-]{1,64}`；不要照抄它发送。
`sent_at_ms` 只用于发送端日志，不用于跨机器时钟相减。`basis_device_ms` 必须回显最近状态的设备单调时钟；
设备按 `now - basis` 检查期限。因此旧状态不会因为网络重发获得新的300ms。
采集帧另带 frame_id、captured_ms、processed_ms、采集时头角/机身姿态；返回结果须匹配本机帧登记表。

命令目录含读取、显式解锁/人工维护、正常停止、故障禁驱、SI 速度、有限位移/转角、双轴头部、
表情、相机三模式、选目标、跟随/巡游/主动动作、取消、持久记忆 CRUD/导出/开关、音量、会话、按钮和唤醒配置。
详细参数和枚举以目录为准。ACK 表达明确结果状态，不等同动作完成：
ACCEPTED → RUNNING → COMPLETED / CANCELLED / EXPIRED / FAULT；格式/权限/门禁失败为 REJECTED。
有限动作的终态也发布在遥测事件中，控制台据此更新日志。

- 凭证权限在服务端决定；请求中的 permissions 只是所需权限，不能提升自己权限。
- 取得控制权须明确操作者看护；活跃租约由一个客户端持有，另一个会收到 CONTROL_OWNED。
- UI 前台每100ms续租，设备期限最多300ms；pointerup/cancel、blur、hidden、App inactive、断线停止续租。
- 断线撤销非零目标，健康平衡保持；重连不重放动作、不自动取得控制权或解锁。
- STOP_MOTION、FAULT_STOP 具有更高优先级，可用较旧序号停止，但仍需有效会话/权限/期限。
- 相同 command_id 不再次执行、也不续租；不同客户端撞 ID 被拒绝。每会话每客户端 sequence 单调。
- 交互/相机配置/记忆的认证独立于运动租约。头部、轮移动、解锁和自主模式必须持有运动租约。
- CANCEL 只取消当前匹配的动作，拒绝无匹配 ID；更换运动目标取消原目标。复位换 session 并禁驱。
- 模型/VLM/记忆内容是数据，没有 shell、原始 PWM、参数修改或公开相机工具。

## 两 MCU 二进制子契约

`wire.c/h` 与 `wire.py`：小端，`A5 5A | version=2:u8 | kind:u8 | payload_len:u16 |
sequence:u32 | MCU_boot_session:u64 | command_id:u64 | payload | CRC32:u32`。
CRC32 覆盖此前全部字节（IEEE/与 zlib.crc32 一致），最大 payload128、总帧158字节；不完整帧50ms丢弃。
版本/长度/零会话/零序号/零ID/CRC错误丢弃且计数。这里是本地电气损坏检测，**不是身份认证**。

运动子集 payload 固定前缀：`basis_device_ms:u64 + valid_for_ms:u16`，后接参数。
无参：READ_STATUS/HEARTBEAT/STOP_MOTION/RELEASE_CONTROL/FAULT_STOP；最后一个使用通用本地故障码。
布尔1字节且必须为1：CLAIM_CONTROL(监督确认)、ARM(本地确认)、DISARM/ACK_FAULT/ENTER_MAINTENANCE(支撑确认)。
两 float32 SI：SET_VELOCITY(v,yaw_rate)、HEAD_TARGET(yaw,pitch)。不支持的类型/长度明确 REJECTED。
网络端的人类原因/维护细节不会被任意透传为执行器字节。C 接收器把 legacy `MC_MOVE.b` 看作差动PWM，
故在未提供经过测量的 yaw-rate 控制器前拒绝非零 rad/s 请求，绝不按原增益直连。

`mori_v1` 已有可注入时间的解析/租约/禁驱/两轴轨迹测试；串口引脚、波特率、隔离、安全线、
完整状态回包与硬件四执行器 adapter 尚受 V1 硬件契约阻挡，默认固件不初始化任何候选 GPIO。
这不是可直接连接任意主控的接口承诺。上层自主状态机在同协议模拟器完整执行，实机门为 BLOCKED。

## 旧协议

MORI/1 和 HW-SW-0.4/0.5 台架 CSV 继续由 `software/tools/` 支持，原始日志不重标为 V1。
旧候选 GPIO、符号、979.616 counts/rev、母线阈值仅属于显式 A0.5 bench profile。
两协议不自动互转，不自动发 arm、confirm_signs、gains、ack。更改见软件接口变更单。

# MORI/1串口协议与工具

当前固件版本SW-0.4，接口HW-SW-0.4，线协议仍为MORI/1。USB前拔整个J12逻辑降压线束并保留J14供编码器，禁止同时外接逻辑5V；USB模式禁Wi-Fi。

仅本地UART0（保留GPIO43/44），115200 8N1。USB原生19/20未改用。所有命令都须由用户明确输入；工具只会额外发只读`info`握手。没有端口扫描、自动烧录、自动重连、命令重试或无线入口。打开某些USB-UART设备可能因主机驱动产生复位，软件不主动切换DTR/RTS，仍须实测；复位必须保持驱动禁用。

请求为`@非零uint32 命令\n`；保留无前缀旧文本请求（回应ID=0）。每条最多119个ASCII字符，不接受控制字符、NaN/Inf、十六进制浮点、溢出/下溢、多余字段。CR/LF结束一行。超长/非法输入整行丢弃到行结束，250 ms未收完标TRUNCATED；截断后的尾部不能被解释为新命令。严重断流后先结束残行，再发送新请求。参数合法不代表状态允许。

| 请求 | 范围 / 条件 |
|---|---|
| info / status | 只读；info同时发HEADER、固件/IDF/接口版本、image SHA、编译安全门、矩阵/符号、统计步长 |
| calibrate | 当前健康且禁用；1024个不同时间戳的静止直立样本，约2.46秒 |
| arm bench | READY、功率级已核验、健康、≥6.8V、俯仰<3°、角速<0.15rad/s |
| duty L R | 各[-0.12,0.12]，仅BENCH；不能延长arm时固定deadline |
| confirm_signs | 未出力且未FAULT；axes编译核验门须通过；本次boot显式确认 |
| gains kp kd kv ki | (0,10]、(0,2]、[0,1]、[0,0.2]；只允许未出力，默认全0；不是推荐参数 |
| arm balance | READY、功率级/平衡/轴核验门、signs及非零合格增益全部满足 |
| move v yaw_duty | v∈[-0.3,0.3]m/s；yaw_duty∈[-0.1,0.1]，不是角速度；低电只允许零目标 |
| stop | 运动目标归零；健康BALANCE继续平衡；BENCH立即撤销输出并回READY |
| disarm | 驱动禁用；有支撑才主动安排；不能清除FAULT |
| ack | 人工故障确认；健康且姿态允许后仅回DISARMED，清除校准和方向确认；不解锁 |
| head deg | [-50,50]°；head验证门开启且健康；默认拒绝并无PWM |

处理后返回`ACK 123 MORI/1 reason=OK state=READY fault=0`或`REJECT 123 MORI/1 reason=GATE state=READY fault=0`。ACK代表受理时的软件状态，不保证电机已经运动或未来帧健康。解析拒绝没有状态字段；无法信任请求ID的损坏/截断行返回ID=0。队列过载或线缆失效可能丢失回应，计数会报告；超时是结果UNKNOWN，绝不自动重试。SPSC容量8，满队列触发锁存QUEUE并清退原队列，旧队列内的ack不能重启。故障时stop可ACK但不清FAULT；disarm会REJECT且保持禁用。

`REJECT`原因：SYNTAX字段/字符错误；RANGE超范围；NONFINITE非有限值；OVERFLOW数值或行溢出；TRUNCATED残行超时；QUEUE_FULL队列过载；STATE状态/前置健康不允许；GATE核验开关关闭；FAULT故障锁存；CONFIG配置错误。故障编号0–11保留，新增12 QUEUE、13 CONFIG；`python3 software/tools/mori_cli.py fault 编号`可展开含义。

## 记录与回放

`HEADER MORI/1 ...`定义CSV列，`DATA ...`仅含对应数据。工具保存CSV、`.raw.jsonl`原始收发、`.meta.json`版本/哈希/设备信息/分位数/丢弃计数。每行带主机UTC及monotonic纳秒；device_us为设备自启动单调时钟。两者未作时钟同步，不可直接相减当单向延迟。

`send`先校验所有参数再开端口；会先发info，然后按顺序发送**用户给出的**每个`--command`，遇REJECT或超时就停止。用于200ms台架窗口时，在一次调用里显式给出两条命令：

```sh
python3 software/tools/mori_cli.py send --port "$MORI_PORT" --output software/reports/DEVICE_single_L.csv --command 'arm bench' --command 'duty 0.03 0'
```

工具不会补发arm、confirm_signs、gains或ack。固件安全门未通过时上述请求被拒绝。不要用断开串口或无线stop代替急停。健康时500ms无move/stop会撤销运动目标但继续本地平衡。工具退出不自动disarm，避免将无支撑机器人关闭而倾倒。

模拟源共用固件状态机、协议结构、遥测序列化和可注入HAL；时间开销为人为输入。`simulate`文件名必须含`SIMULATED`，元数据source同样标识。`replay`只读文件，严格验证schema/有限数/哈希，绝不打开串口或把CSV变回命令；支持基线20列CSV（标LEGACY_UNVERIFIED，缺失指标NOT_TESTED）。模拟设备保持默认全部安全门关闭，不自动解锁。

SW-0.4的INFO报告`requirements=HW-SW-0.4 snapshot=HW-SW-0.4 origin=HW-SW-0.3 wheel_counts_per_turn=979.616 wheel_m_per_count=0.000304661523`。origin只追溯初始工作副本，不代表当前比例。采集器将这些字段写入device_metadata，回放保留原值，不用当前固件参数重算历史速度；旧SW-0.3记录的1204.44不改名、不重标。新记录单独使用SIMULATED_hw04前缀。

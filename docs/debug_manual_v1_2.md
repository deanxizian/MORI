# V1.2 调试与故障说明

当前仅主机/模拟可执行；下表所有上电、旋转、热、平衡和续航项均 NOT_TESTED。STM32镜像仍禁驱，物理端口/按钮/功率安全链未释放。不要将旧ESP32刷写命令、GPIO、PWM脉宽/增益、2S阈值用于1.2。

网页 `STOP_MOTION`：取消主动位移/巡游/跟随，健康时继续平衡。失联/300ms租约到期同义；失去互联网不保持最后非零目标。`DISARM`需可靠支撑，`FAULT_STOP`/硬件禁驱可能使机器人倒下。低电量是提前支撑请求；无法保证自行站稳、回托架或自动回充。故障不自动重启上力。视觉sleep仅闭眼。

## 可离线执行

按根目录README启动 → 用一次性码绑定SIMULATED → 取得控制权 → 明确解锁模拟 → 前进100mm → 停止 → 在视觉页选择目标并模拟跟随 → 触发多人/丢失检查停止 → 维护页模拟严重故障 → 确认支撑并人工清故障，再次显式解锁才允许模拟运动。没有实物地址或API主密钥参与。

`bash tools/test-motion-v1_2.sh` 检查S288坏帧/位翻转/截断/符号/齿比/回绕/超时、SCS大端/错误/映射、IMU旋转与SI、租约、STOP/禁驱/故障锁存、输入NaN、持续饱和和控制超时。`bash tools/test-s288-reference.sh`是官方C对照的合成报文，不能称为实机golden vectors。离线S288回放见README，输出保留capture_monotonic_us；不同主控的时间不能直接相减。

## 实物递进记录（各级未授权/未满足前置条件不得执行）

| 级别 | 前置条件 | 命令/操作 | 观测量与通过阈值 | 停止条件 | 当前 |
|---|---|---|---|---|---|
| 0 断电 | 硬件签字的线序/实物版本/电源与极性；外部支撑 | 文档核对、断电导通/绝缘；无运动命令 | 四执行器、独立轮承载路径；3S不接CAM BAT；FFC接触面一致；电源额定按硬件记录 | 任何未知针脚、电平/极性冲突 | NOT_TESTED |
| 1 限流且禁驱 | 托架、物理急停、额定限流电源；限流值由硬件设定 | 仅状态读取；不发ARM/位置/速度/力矩 | 复位/下载/掉电输出禁止；3S/6V/5V各支路在签字容差内；无倒灌 | 支路越限、发热、异味、意外使能 | NOT_TESTED |
| 2 单模块 | 每次只接一个模块，执行器功率禁止 | ICM WHO=0x47/六面静态/手动倾斜；相机屏音频分别测试；S288单ID只读探测由合格PHY发送 | 原始数据/轴向/帧时间正确；位错误、重复ID=0；记录示波器6Mbps实际误差；不把协议估计扭矩作负载力矩 | 电平不符/CRC错误/时戳异常/排线升温 | NOT_TESTED |
| 3 悬空单轮 | 轮保护罩、限流、已签字停止与禁驱行为；候选低出力参数经台架批准 | 显式本地解锁一次有界试验；V1.2指令适配器尚BLOCKED，不提供可误发的裸包 | 极低已批准torque/speed，固定期限；方向/反馈/齿比一次换算；电流/电压/温度记录 | 非预期旋转、通信超时、任一限制触发 | NOT_TESTED |
| 4 双轮/回灌/急停 | 单轮通过、实际回灌钳位/保护/仪器及外部支撑 | 重复有界启停、断通信、按物理急停、复位；分别核mode0/零扭矩/KpKd0/timeout | 任何尖峰不能越执行器上限；左右年龄/偏差和禁驱延迟符合签字预算；无自动重启 | 保护不动作、钳位过热、负压/过压、未知锁定行为 | NOT_TESTED |
| 5 台架辨识 | 真实轮径/质量/重心/头姿/轴符号与时钟已测 | 有界激励，离线拟合驱动、齿隙、时延与参数；不逐帧LLM | 拟合误差、裕量、增益来源/版本；负载温升和总线年龄有实测最大值 | 发散、持续饱和、限流/热保护接近 | NOT_TESTED |
| 6 防摔保护平衡 | 安全链通过、参数评审、吊绳/保护框和人工看护 | 近直立显式ARM，STOP撤销目标，受控轻扰动；不从倒地自动起身 | 姿态、轮输出、恢复时间、最大时延/饱和均满足签字指标 | 倾角或电源/反馈失效即禁驱，允许由保护承接 | NOT_TESTED |
| 7 清场低速 | 第6级通过，无楼梯/门槛/人群；人体能立即物理禁驱 | 先手动≤0.10m/s/单段≤0.30m，再头跟踪，再跟随/有限巡游；逐项解锁 | 300ms租约、250ms观测起点；遮挡/多人/头反馈失效停止；测轮滑/漂移 | 目标不确定、观察过期、场地不再清空、网络故障 | NOT_TESTED |
| 8 60分钟混合工况 | 各模式/热/电池验证通过，满电和充电方式已核 | 真实连续60min平衡+双眼+跟踪；累计移动≥10min、语音≥10min、每分钟小头动 | 真实电流/电压/温度/累计能量/最差时延；不使用仿真时钟顶替续航 | 低电支撑请求、保护触发、热/时延越限 | NOT_TESTED |

## 方向、反馈与参数

M=(右,前,上)，C=(M.Y,-M.X,M.Z)。身体正前倾=机械−X/控制+y；头抬脸=机械+X/控制−y。先验证六面和手动前倾，记录IMU安装矩阵；电机正输出应使各轮接地点向前推动车身，左右镜像分别确认，不复制符号。轮前进用于追赶向前倾倒的质心，姿态PD公共输出应对正前倾给正向纠偏；速度环通过倾角参考调节，初始可能先反向让机身倾斜，不能据单一瞬间误判。

S288 rotor累计角与13bit输出绝对角单列。丢帧间隔过大或跳变时累计位置无效，不自动接续猜圈数。SCS位置是原始计数，标定后才能称yaw/pitch实测角；raw速度/负载单位未核不转换成Nm。联合region缺失时真实头目标拒绝。抬头重力负载下不默认松扭矩。

新3S保护阈值目前null。调参文件不得从夹具复制physical_verified=true，不得以删安全门通过测试。功能按钮普通短按会话、双击停止；维护长按需要支撑确认与维护状态，不能把内部BOOT算成已安装外部用户按钮。

## 故障定位

| 反馈 | 解释 / 恢复 |
|---|---|
| REJECTED / PHYSICAL_GATES_NOT_VERIFIED | 真实能力未释放；保持模拟，不能通过改网页布尔绕过 |
| EXPIRED / NO_LEASE / CONTROL_OWNED | 数据陈旧/无控制权/另一客户端占用；先读新状态再显式取得控制权，不重发旧动作 |
| IMU / WHEEL / SEVERE_TILT / POWER / CONTROL_TIMEOUT / SATURATION | 严重故障锁存；先可靠支撑，排查物理原因，再人工ACK和重新检查；不会自动ARM |
| 目标/头反馈丢失 | 取消跟随并归零位移；检查采集ID/年龄/头角/置信度后重新确认目标 |
| 未提供唤醒模型/云密钥 | 用按钮/网页mock开发；不把字符串设置称为模型完成 |

## 每次实验记录模板

```text
run_id/date/operator:
evidence_level: BENCH | ROBOT
result: PASS | FAIL | NOT_TESTED | BLOCKED | NOT_APPLICABLE
hardware_revision/serials/PCB/FFC/cabling:
spec/electrical/mechanical revision + hashes:
firmware ELF/bin/parameters hashes + toolchain:
support confirmation and physical inhibit evidence:
command_id/session/source/command/limits/deadline:
clock source / DRDY / frame ID / original capture timestamp:
voltage min/max incl regeneration, signed current, temperatures:
IMU/wheel/head validity + age/skew; compute and full-frame max/p50/p95/p99:
CRC/timeout/retry/log-drop counts:
observed motion/thermal/duration; instrument/video/raw log paths:
stop reason/fault/ACK/re-arm chronology:
reviewer / allowed next step / unresolved risks:
```

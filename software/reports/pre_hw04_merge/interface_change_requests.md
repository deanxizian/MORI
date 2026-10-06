# 软件接口变更单 SW-0.3（对 HW-SW-0.2，2026-09-21）

所有改动仅在 software/；候选模块台架接口，PROTOTYPE / UNVALIDATED。硬件任务合并前须审阅。所有实物验证 NOT_TESTED。本任务未修改硬件目录与机械定义；上游快照由并行硬件任务更新，见文末版本差异。

| ID | 动机 / 原接口 → 新接口 | 受影响文件（software/firmware_work/firmware/ 下） | 兼容 / 决定 |
|---|---|---|---|
| ICR-001 | 快照每计数 0.000304661522567 m 与本次明确规格冲突 → π×0.095/1204.44 = 0.000247792585842 m；12 已含 x4，1:1 带传动 | main/board.h, components/mori_core/mori_io.c, include/mori_io.h | 依用户交接纠错；PCNT 2 单元×2 通道不变。实际齿数与周长仍需硬件确认 |
| ICR-002 | 原始 IMU 轴直接作控制轴、符号藏于 board.h → 可替换刚体旋转矩阵及四个 ±1 符号，默认矩阵 identity（未核验），符号保持 +1/-1/+1/-1 | main/mount_config.h, sensors.c, encoders.c, motor.c; include/mori_io.h | GPIO/±2g/±500°/s 不变；CONFIG_MORI_AXES_VERIFIED 默认 n，未签字拒绝 confirm_signs 和平衡解锁；六面/俯仰/方向记录后修改配置 |
| ICR-003 | 无请求 ID、sscanf 宽松解析、仅异步 rejected 标志 → MORI/1 文本协议，支持 @ID 前缀与每命令 ACK/REJECT，严格字段/有限数/溢出/行截断检查；info/status 查询 | main/main.c, components/mori_core/mori_protocol.c, mori_runtime.c | 原命令拼写保留；无前缀标 ID=0，建议主机用唯一非零 ID。新遥测带 DATA 前缀与明确列头；主机支持基线 CSV 只读回放 |
| ICR-004 | 原 READY 不锁存传感器失败、重复样本推进校准、首因被覆盖 → 就绪/校准失健康锁存 FAULT、严格新时间戳、首因保留；队列溢出 MF_QUEUE=12；配置非法 MF_CONFIG=13 | mori_core.c/h, mori_runtime.c/h | 原故障 0–11 保持；必须人工 ack→重新校准→显式解锁；溢出时清退待处理命令，不能靠已排队 ack 重启 |
| ICR-005 | 2404 us 计算保护阈值 → 完成帧计算+传输预算 1800 us；输出前后检查，超预算锁存 MF_TIMING；8 ms 仅缺样后备；健康完整帧才翻转心跳 | mori_runtime.c, main/main.c | GPIO42 不变，不用自由 PWM 喂狗；外部链路超时和实际波形须硬件决定并实测；PWM寄存器提交不等于物理生效 |
| ICR-006 | 隐式覆盖日志无丢弃数 → 分离采样遗漏、遥测队列丢弃、命令队列溢出、回复丢弃计数；低优先级可导出分段时间、原始及控制系IMU、独立左右速度和健康标志 | mori_runtime.c/h, main/main.c | 固定容量队列；串口115200不足以全量416Hz文本输出，默认每40帧遥测，完整帧最大值/直方图独立统计；不可把抽样分位数当全帧 |
| ICR-007 | 屏幕渲染固定240无裁切 → 分辨率独立 RGB565 圆形渲染器、无屏及主机 PPM 模拟后端；GC9A01适配仍只支持240×240 SPI | mori_ui.c/h, main/display.c | 不改引脚、不将RGB并行屏当SPI；最终Ø60面板待硬件选型 |
| ICR-008 | 头部轨迹在实时控制任务内 → 低优先级20ms任务；默认无PWM，显式验证开关后只接收±50°；故障/失鲜停PWM。转向目标增加有限加速度，姿态纠偏无全局斜率 | mori_ui.c/h, main/main.c | 头映射1500−12.963×deg及50Hz保持；速度上限30°/s、加速度60°/s²为软件试验起点；head失效禁用最长一个任务周期加调度延迟须测。新转向目标斜率0.4 duty/s待辨识 |

电池阈值保持：8.4 V标称满充，6.8告警/禁止新解锁，6.6请求支撑，6.0严重欠压禁用；既有过压8.65 V、|母线电流|>1.30 A、温度0–65°C、倾倒20°、输出0.65、饱和200ms保留为未测的软件验证起点。不可替代BMS/保险/回灌钳位。任何阈值修改需新变更单。

ICR-009 — 台架授权仍固定在 arm 时刻后200ms，软件提前8ms撤销（有效目标窗口约192ms），给已受限控制帧间隔和提交留余量。原实现仅在到达200ms后的帧撤销，可能晚一个周期。影响 mori_core.h/c、mori_runtime.c；重复 duty/arm 不延长。该保守收紧不改变PWM/电气接口。CPU阻塞/中断延迟的物理截止仍由外部安全链保障，示波器证明最大通电时长<=200ms之前实物验收 NOT_TESTED。

ICR-010 — 本地IDF v5.5.2的ledc_set_duty_and_update要求先安装fade service（esp_driver_ledc/src/ledc.c:1307、1579）。基线缺少该初始化且忽略返回错误。已先用遵守该API契约的模拟驱动复现FAIL，再在motor_init禁用阶段安装service并逐通道预建资源；提交失败保持ARM低并锁存driver失效，须复位并重新检查。头部提交失败/任务失鲜保持该目标revision禁用，需新显式head命令。影响main/motor.c、main.c、peripherals.h、mori_ui；不引入输出斜坡、不改变GPIO/PWM频率或方向；该修复的实机PWM行为仍NOT_TESTED。

## 上游并行更新冲突（2026-09-21，待明确基准）

初次读取manifest为HW-SW-0.2；解压时已经是0.3，baseline_integrity.json记录的0.3版本/哈希未被改写。基线构建和163断言针对实际解压的0.3副本。ICR-001是在遵守本条用户提示词的#5216 / 1204.44计数要求时写的兼容差异，不应被理解为0.4 #4863的计数错误。

最终观察到HW-SW-0.4，其轮候选#4863、48 CPR已含x4、20.4086667:1、979.616计数/轮转、0.000304661522567 m/计数；编码器5V需SN74LVC14AD变3.3V；USB接线说明要求断开J12逻辑降压线束、J14保持供编码器，不能与外部5V并供。模型Wheel_R/Motor_R才是控制left（Blender X正）。回灌钳位R14为25.5k0.1%，VMAIN采样不能代表被隔离的VM_MOTOR尖峰。以上是上游候选资料，实物仍NOT_TESTED。

本软件当前仍遵守用户0.2参数，**对0.4硬件兼容性FAIL**；已发起基准澄清。不能只改SIMULATED文件标签，更不能拿ICR-001覆盖新电机规格。若选0.4，须统一改唯一轮计数配置、元数据、测试和接线说明，生成新版本模拟数据，再构建验证；若维持0.2，禁止接0.4驱动/线束试转。上游资料副本及SHA记录在reference_sources/和reports/handoff_drift.json。

ICR-011 — BENCH原输出结构整体赋值会抹掉低电告警/支撑请求标志；已通过6.5V台架模拟先复现FAIL，再改为只设置轮输出字段，保留低电标志。影响mori_core.c与测试；6.8/6.6/6.0V阈值完全不变，台架授权不能延长。

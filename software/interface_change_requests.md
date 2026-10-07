# 软件接口变更单 SW-0.4（对 HW-SW-0.4，2026-09-21）

> 本文件为累积历史。当前V1.2变更见文末ICR-019～024；下述2S阈值/GPIO/驱动和方向仅适用各自旧版本，不定义V1.2。当前软件入口为根 README_SOFTWARE_V1_2.md。

所有改动仅在 software/；候选模块台架接口，PROTOTYPE / UNVALIDATED。硬件任务合并前须审阅。所有实物验证 NOT_TESTED。本任务未修改硬件目录与机械定义；上游快照由并行硬件任务更新，见文末版本差异。

| ID | 动机 / 原接口 → 新接口 | 受影响文件（software/firmware_work/firmware/ 下） | 兼容 / 决定 |
|---|---|---|---|
| ICR-001（已废止，见ICR-012） | 历史0.2提示词指定#5216：曾将979.616改为1204.44 counts/rev；该变更只适用于旧候选，不适用于0.4的#4863。当前恢复0.4规定的979.616 | main/board.h别名、include/mori_io.h唯一换算源、测试/元数据/文档 | 不向硬件回写旧提案；PCNT仍2单元×2通道，48 CPR已含x4，不再乘4。旧数据保留原比例 |
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

## 版本追溯与已解决的接口冲突

最初用户0.2提示词指定#5216，实际解压时上游已到0.3；原始版本、21成员SHA和当时构建结果仍见`reports/baseline_integrity.json`。上一交付按明确的0.2要求保留1204.44，报告其对0.4兼容性FAIL。本次用户明确要求按HW-SW-0.4继续并读取并行提示，已据此解决接口选择；原发布报告在`reports/pre_hw04_merge/`，未改写历史证据。当前接口一致性以重新构建、测试和严格上游校验结果为准，实物仍NOT_TESTED。

ICR-011 — BENCH原输出结构整体赋值会抹掉低电告警/支撑请求标志；已通过6.5V台架模拟先复现FAIL，再改为只设置轮输出字段，保留低电标志。影响mori_core.c与测试；6.8/6.6/6.0V阈值完全不变，台架授权不能延长。


## ICR-012 — 依本次用户指令合并 HW-SW-0.4

动机：采用2026-09-21硬件交接0.4及同目录并行更新说明；保留软件安全修复，撤回ICR-001旧电机提案。依据副本在`reference_sources/HW-SW-0.4_*`；23个快照成员及受保护输入SHA见`reports/hw04_adoption.json`。

| 原接口 → 新接口 | 受影响software文件 | 兼容策略 / 状态 |
|---|---|---|
| #5216、12×100.37=1204.44 → #4863、48×精确20.4086667=979.616 counts/rev；m/count 0.000247792585842 → 0.000304661522567 | firmware_work/firmware/components/mori_core/include/mori_io.h、mori_io.c（实时测速仍使用float）；tests/test_engine.c、test_baseline_interface.py、test_hw04_interface.py | CPR/齿比/1:1皮带仅在一个运行时头文件定义；独立物理换算示例验证8帧测速和禁止再次x4。没有改PCNT配置/候选方向符号 |
| INFO SW-0.3/需求0.2/两位计数小数 → SW-0.4/需求与接口快照0.4/三位计数小数，origin=0.3保留 | firmware_work/firmware/main/main.c、tools/SIMULATED_device.c、共用mori_io.h；采集/回放元数据测试 | MORI/1及CSV列不变，新增origin字段兼容忽略；旧记录SHA不变，不重标版本或重算旧速度；生成SIMULATED_hw04_*新记录 |
| USB供电说明缺失 → 拔整个J12，保留J14，编码器DEVKIT_5V经LVC14转换；J4/J5自定义XH6 | firmware_work/wiring.csv、pinmap.csv（GPIO内容未变）、docs/hw_sw_0_4.md、debug_manual.md、protocol.md、记录模板 | 逐字对照0.4镜像；不改硬件文件，不能据软件测试判电气通过。USB模式禁Wi-Fi，预算<500mA仍待测 |
| 模型左右名称含糊 → control left=模型R/X正、right=模型L | main/mount_config.h注释、direction_checks.md、调试手册、测量模板 | 不翻转任何已存符号或矩阵，两个A/B同时反相保持相序，实际符号仍须测量 |
| ADC/过压可能被误认作所有母线尖峰 → 明确ADC=VMAIN；VM_MOTOR独立示波器观测；R14=25.5k0.1%、R15=10k0.1%、R16=2.2M1% | docs/hw_sw_0_4.md、debug_manual.md、realtime.md、记录模板 | 软件8.65V不变；8.73–9.04V仅钳位开启估算。电气热/回灌NOT_TESTED |
| 功率门文本按旧阶段编号 → 独立急停/看门狗/限流/钳位资格后才允许台架 | main/Kconfig.projbuild、debug_manual.md | 只同步说明，不解开任何编译门；头±50°、IMU量程、6.8/6.6/6.0V及全部故障语义保持 |

验证：先运行新增0.4行为测试记录4项FAIL，再合并并复测；本次完整构建/安全/协议/模拟及严格交接检查的真实结果统一见`reports/final_validation.json`。旧状态机/运行时/协议/驱动等关键源文件哈希保留核验，原有回归不删减。此次软件接口对齐不冻结采购、装机BOM或赋予实物签字。

## ICR-013 — MORI V1 目录与安全配置分离（2026-09-21）

动机：用户新提供 MORI_SPEC_V1.md，四执行器/双MCU/相机取代 A0 三执行器与单MCU。
旧接口：software/firmware_work/firmware 是唯一台架固件，直接使用HW-SW-0.4候选GPIO。
新接口：**同一份源迁移**到 firmware/motion，旧路径为 ../../firmware/motion 符号链接；
新增 CONFIG_MORI_LEGACY_BENCH_PROFILE 默认n。V1默认只运行禁驱核心，不初始化未冻结GPIO；
显式旧台架profile才进入原主路径，功率/平衡/头/轴验证门仍默认n，增益0。
影响：firmware/motion/main/main.c（原入口重命名）、v1_main.c、Kconfig/CMake、software旧路径及文档。
兼容策略：原主机/模拟HAL/串口工具/CSV与163+2211+22+10断言保留，迁移前源哈希保存在reports/v1/motion_migration_hashes.json。
没有改 hardware/、原GPIO/方向/CPR/阈值。HW0.5隔离与功率改装仍不等于V1装机签字。

## ICR-014 — MORI/2、SI与运动租约

动机：网络/双客户端/自主行为不能复用无会话文本命令。
旧：MORI/1文本与500ms目标撤销，差动值为归一化PWM；新：MORI/2完整命令ID/来源/权限/单调时钟依据/
300ms运动租约/独立结果状态，加本地CRC帧、序号与MCU启动会话。协议见contracts/README.md。
影响：contracts/*（不含机械文件）、firmware/motion/components/mori_v1、backend、simulation、apps。
兼容：不自动转换两协议；保留旧工具，非零yaw rad/s在旧有刷接口映射未测前明确拒绝。正常STOP与FAULT/DISARM分离；
语音/表情/相机配置不依赖运动租约，但经过独立权限检查。运动/头部/维护仍需本机门和显式授权。

## ICR-015 — V1坐标与双轴头部

动机：V1机械前向+Y，与A0前向-Y冲突，且头增加pitch。
旧：A0 control=(-Y,+X,+Z)、单yaw GPIO41/名义−1.75传动；新：V1 control=(+Y,−X,+Z)，头yaw正左、pitch正上、身体pitch正前倾。
头部SI目标yaw±60°、pitch−20..+25°，软件假设速度0.52rad/s、加速度1.05rad/s²；各轴含零点、符号、限位、反馈/估计标记，静止不自动卸扭矩。
影响：contracts/coordinates.md、mori_v1、simulation/vision.py、控制台；旧mount_config属于旧profile，数值未翻转。
兼容：V1新HAL未绑定旧矩阵/编码器/舵机PWM；硬件须签字真实两轴舵机、齿比/脉宽、支撑负载与线缆扭矩后再提供adapter。
视觉把采集时相机射线经头角/机身姿态转世界，再转当前机身；内外参目前只用显式模拟假设。

## ICR-016 — 交互域接口、显示与隐私

旧：GC9A01单域台架显示、无相机/音频。新：独立ESP-IDF5.5.2交互工程，LVGL9.2.2/ESP-SR2.2.0/esp32-camera2.0.16锁定。
双眼采用bloub参考函数+C移植与MORI8状态，可变分辨率RGB565/Canvas与圆形裁切；原小屏不是最终机械面板。
音频16kHz mono麦克风与已播放reference；小智v1协议输入Opus16kHz/60ms，输出24kHz，半双工，设备播放时间独立记录。
相机OFF/SNAPSHOT/TRACKING，按需上传须明确许可；模拟输入为确定像素夹具，非随机检测框。
影响：firmware/interaction、backend音频/视觉适配、apps预览；新GPIO/串口速率/音频codec/屏幕总线/按钮引脚均待硬件任务决定。
兼容：本次只在独立编译配置中核验打开分支，交付默认配置全关闭；未发送实机解锁、烧录或远程部署命令。

## ICR-017 — 后端与App

新增单用户SQLite作用域记忆、来源/冲突/确认/删除清单、认证凭证、预算上限、TLS/WSS部署文件；
Vue界面与Capacitor iOS/Android工程。凭证不得将云API主密钥放入网页/固件。
iOS因本机Xcode27最低目标调整到15、补UIScene后台停止续租；Android工程需JDK21/SDK35。
上述无GPIO变更，所有物理执行器/自主能力继续BLOCKED，硬件任务无需合并Web或服务器代码到实时主循环。

2026-09-21后续用户范围调整：当前只需要网页，暂停App开发/验收。保留已有apps/mobile工程及历史构建证据；CI默认不运行移动端构建。该调整不改变V1机械、电气、协议或安全门。

## ICR-018 — 网页播放观测与打断回执

动机：云生成完成、收到打断请求都不能代表扬声器已停止。原接口只有playback开始/结束；新接口增加voice_interrupt.command_ids、interrupt_ack与voice_metrics事件。
影响：backend/mori/app.py、apps/console/src/client.ts、backend/tests/test_audio.py。
兼容：MORI/2命令字段不变；这些是经认证会话中、绑定原command_id所有者的观测事件，不能产生运动命令。
GATEWAY_MONOTONIC_MS时间只表示服务器收到HOST_WEB_AUDIO回执的时刻，包含网络延迟，不冒充设备DAC/声学延迟；物理播放时序仍NOT_TESTED。

## ICR-019 — V1.2 STM32与执行器（2026-09-22）

动机：按新用户规格迁移，保留旧回归。
原接口：ESP32-S3、有刷PWM/PCNT或未释放FOC、PWM头部。新接口：STM32F413、S2886Mbps独立轮总线、SCS0009独立头总线、ICM42688-P SPI/DRDY。
影响：firmware/motion/CMakeLists.txt、v1_2/、tools/build-*、tests、CI、contracts/software_profile.json。
兼容：旧源不删、旧路径符号链接保留；legacy-motion显式编译旧工程；新的参数与门控不引用旧GPIO/CPR/PWM/2S阈值。S28820/26字节按原厂C显式收发；文档vol宽度、Python signed/round/负pos冲突提交硬件抓包确认。6Mbps候选96MHz仅算术证明，板时钟/收发器未实现。模式0不当作自由卸力，驱动禁用需要独立物理链。

## ICR-020 — 参数、测量与新硬件契约

动机：未知测量不能以模拟0或旧阈值冒充。
原接口：MORI/2既有JSON状态；新接口保持命令与CRC线格式，新增software_version、parameter_version、hardware_profile、physical_release、sensors分组valid/null。
影响：contracts/profile.py/software_profile.json、simulation/device.py、apps/console、reports/decisions/ADR-SW12-001.md。
兼容：旧客户端可忽略新增字段；sensors仅实测后valid，模拟头估计独立。V1.2-H0.1硬件现已采用MORI/2长度/CRC；旧CRC16冲突已不适用。板间baud仍null，S2886Mbps不能代替板间速率。新电池保护阈值null，增益/扭矩上限0；请求硬件提供电源/过压/回灌/测量链。几何/电气文件由并行任务更新，软件只读并记录版本，未覆盖。

## ICR-021 — 微雪交互、ST77916与音频

动机：新SKU33700/35079取代未冻结旧面板/板卡。
原接口：camera2.0.16、8MB构建、240×240无屏帧缓冲；新接口：camera2.1.4、16MB、360×360；新增ST77916 1.0.1 QSPI、codec1.5.4和CH32 1.0.1，保留IDF5.5.2/LVGL9.2.2/ESP-SR2.2.0并实际重编译。
影响：firmware/interaction/main/board_v12.*、main.c、idf_component.yml、dependencies.lock、sdkconfig.defaults/v1_2。
兼容：升级前锁/config归档；默认物理门仍n，接口接收硬件签字配置，无猜测GPIO/FPC。请求确认初始化序列、GPIO/CH32 reset/backlight、FFC物理方向/16–18脚、QSPI电平/供电；TE不可用。请求音频PCM槽、时钟、模拟参考路由/延迟核验，现有软件MR参考不可当作板上AEC通过。

## ICR-022 — 头部、跟随与证据

动机：实测头角缺失会破坏相机→机身变换；到达目标时速度突变违反加速度约束。
原接口：独立轴限幅/估计角；新接口：SCS反馈有效性、标定后SI、联合reachable回调、离散制动轨迹；模拟头反馈丢失取消跟随，健康本地平衡继续。
影响：motion/v1_2/sensors.c、test_motion.c、simulation/device.py、test_v1_2.py、docs。
兼容：机械yaw/pitch范围保留，但不能替代联合包络；菱形联合区域是测试夹具，实机未装入假区域。已保留头轨迹FAIL→PASS日志。请求机械/硬件交付联合区域、零点/比例/方向/限位、负载误差与温度门槛。App按用户要求继续暂停；HOST_TEST/SIMULATION通过不授权BENCH/ROBOT。

## ICR-023 — 相机首帧等待与版本统一

动机：浏览器测试发现TRACKING启用到首帧之间返回409 NO_FRAME，形成控制台错误；/health仍报告旧软件版本。
原接口：首帧未到HTTP409；新接口：已授权且相机开启、但帧未到时HTTP204+WAITING_FOR_FRAME，网页等待下一次有界轮询，不生成空图片。相机OFF仍409、未授权401/403，上传/控制权限不变。/health和遥测共用software_profile版本。
影响：backend/mori/app.py、apps/console/src/App.vue、simulation/tests/test_v1_2.py、浏览器测试。
兼容：MORI/2与UART没有变化；网页和服务器同步更新，旧客户端需处理204无正文。保留HTTP首帧及版本FAIL→PASS记录，不忽略浏览器错误来让测试通过。

## ICR-024 — 离线模型的供电能力与头部惯量

动机：原符号模型只有延迟/噪声/死区/轮滑，不能覆盖V1.2的双轴头部扰动与供电余量下降。
原接口：body-only加速度输入模型；新接口：可选供电能力比例、头部质量/高度/自转惯量及有界pitch运动，输出惯量、重力矩系数和头部反作用；输入默认值保留原模型，输出仍标SIMULATION。
影响：simulation/dynamics.py、tests/test_dynamics_replay.py、docs/dynamics_v1_2.md。
兼容：不改变固件、GPIO、真实电池阈值或控制参数；加速度不是S288 Nm，不能复制模型增益。新工况结果另存SIMULATED_dynamics_v1_2.json，旧报告保留。

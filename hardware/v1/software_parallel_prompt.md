> H0.2采购更新：本文保留H0.1技术假设供追溯。最新国内候选见[采购核验表](procurement/BOM_国内采购核验.md)；新器件不能按本文或旧pinmap直接接线。

# 可直接复制给任务 3 的提示词

继续 MORI V1 正式软件工程。先读 `/Users/dean/Documents/MORI/MORI_SPEC_V1.md`、项目 `AGENTS.md`、`contracts/electrical_interfaces.json`、`contracts/mechanical_interfaces.json`、`hardware/v1/interfaces/pinmap_V1-H0.1.csv`、`hardware/v1/link_protocol.md`、`hardware/v1/media_resources.md` 与 `hardware/v1/test_plan.csv`。继承共享驱动；正式代码归 `firmware/motion`、`firmware/interaction`，保留旧 `software/` A0 历史，不再造另一套冲突固件。

现在是四执行器（左右真实反馈轮驱+头yaw/pitch）与两颗 ESP32-S3-WROOM-1-N16R8。摄像头、圆屏、录播音、网络和用户按钮属于交互 MCU；刚性机身 LSM6DSOX、轮驱、头部、安全和维护态属于运动 MCU。主控数量不影响四执行器计数。当前硬件选型门槛仍 BLOCKED：FOC4012没有完整采购型号/协议单位；唯一有刷备选FIT0521+DRV8874不同控制接口且超预算；电池/充电匹配、摄像头FPC、电源峰值与部分包络未冻结。引脚表为候选，不得当已制造板刷入或直接接线。

先并行完成可脱离实物的工作：

1. 在任务3目录建立两个可构建目标与板级profile，锁SDK/组件版本；本机有ESP-IDF5.5.2，但实际构建后再声称PASS。默认禁能；FOC未标定的原始整数使用opaque类型，绝不当Nm。FOC/PWM互斥profile分别表达设备能力，禁止直接套Hover增益或把扭矩字段简单改成占空比。
2. 实现 `link_protocol.md` 的帧解析、CRC、boot会话、序号、心跳和有限租约；建立主机测试：拆包/粘包/噪声/长度溢出/CRC错/重复旧包/重启/洪泛/阻塞/超时/旧会话重放。错误包和心跳不能无限延长运动命令。接收线程不得阻塞500Hz目标运动循环。
3. 实现可测状态机：BOOT/DISARMED、LOCAL_ARM检查、BALANCING、STOP_MOTION、DOCKED_MAINTENANCE、FAULT_LATCHED。交互断电/重启/摄像头失效只取消导航，健康运动域维持本机平衡；关键传感器/驱动故障锁存禁能；没有本地明确解锁不能自动恢复。对话按钮不能复位未支撑的运动MCU。不要在无实物时把这写成已站稳。
4. 建立SI单位/坐标/时间戳边界：+Y前，机身前倾绕−X，头yaw绕+Z、pitch绕+X；各轮正向经过标定后都代表前进。编码器CPR目前null，不偷用商品页341.2或1364.8；提供一圈计数标定工具与双向检查记录。头FT90M-FB PWM/模拟FB驱动可先mock，真实角度在标定前为ESTIMATED，视觉投影带不确定性。
5. 音视频先分别驱动mock/接口，再做同时运行压力框架：GC9A01纯黑眼睛，M0031 OV2640 DVP目标QVGA跟踪和JPEG拍照，SEN0327+MAX98357A的同步I2S及真实播放PCM参考。记录DMA/PSRAM峰值、帧率、队列长度、采集到目标的p95/p99时延；250ms观察门槛未通过时禁止视觉导航，不能无限依赖云端控制。人脸检测不等于全身跟随/识别身份/避障。
6. 为“你好，Mori/莫里”建立模型加载/哈希/授权/数据记录接口。已有测试词或按钮仅供开发；免费社区TTS模型申请需项目条件和实际交付，专属定制需报价。不要把配置改名当模型，也不要自行发布项目或向厂商发消息。
7. 给出最小板级自检模式：每次只开一个外设，执行器始终受硬件禁止；日志含供电电压、电流、IMU年龄、轮反馈年龄、头反馈质量、失联原因、堆栈/堆/PSRAM余量。准备按硬件T00–T14填写的数据格式，不填假电流、温升、平衡和60分钟记录。

正式运动控制参数只由实测辨识和限流台架调试冻结；`hardware/v1/calculations/model.py` 是需求/敏感性模型，不是可直接上线的控制器。禁止自动烧录、自动解锁电机、自动采购。输出代码、实际构建/主机测试报告、所锁依赖/模型许可、硬件未定项对软件的影响；未知物理接口明确写BLOCKED，其他能完成的部分继续推进。

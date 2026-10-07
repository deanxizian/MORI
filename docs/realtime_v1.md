# MORI V1 时钟、实时性与控制边界

物理计时最大值全部为 **null / HARDWARE / NOT_TESTED**。本机Python/C渲染耗时、网页RTT、编译时间均不是ESP32采样或控制周期。
旧台架416Hz给出约2.404ms名义周期，计算+传输目标≤1.8ms；8ms IMU故障后备不得当作正常延迟预算。
V1当前禁驱主循环只是可构建接口核心，不伪称已经运行416Hz平衡任务。原实时驱动在同一motion工程的显式legacy profile保留。

## 测量拆分

| 阶段 | 已有钩子 / 后续物理测法 | 物理最大值 | 状态 |
|---|---|---|---|
| IMU采样、内部低通/群延迟 | ODR和滤波器配置锁定后，与外部运动参考/DRDY对齐 | null | NOT_TESTED |
| DRDY→调度唤醒 | ISR时间戳、wake_us/max_wake_us | null | NOT_TESTED |
| I2C状态/样本读回 | imu_io_us；姿态任务唯一拥有I2C，监测也交其调度 | null | NOT_TESTED |
| 监测与编码器 | monitor_io_us、encoder_us、PCNT累计计数和时间窗；保存采样年龄 | null | NOT_TESTED |
| 姿态融合 | fusion_us，原始与安装矩阵后的SI向量并存 | null | NOT_TESTED |
| 控制与安全命令 | feedback_us，计算参考→公共输出→差动剩余余量 | null | NOT_TESTED |
| PWM API提交 | pwm_submit_us，包含软件提交调用，不等同引脚生效 | null | NOT_TESTED |
| 实际PWM/使能生效 | 示波器同步DRDY、ARM、IN1/2、nSLEEP和硬件心跳；由签字V1引脚代入 | null | NOT_TESTED |
| 交互相机/音频/屏/Wi-Fi并发 | 帧采集时刻、处理时长、堆高水位、任务栈、DMA队列和丢弃数 | null | NOT_TESTED |

400kHz I2C的旧配置线速估算：IMU状态约90us、12字节样本约337.5us、INA两字节约112.5us。
这些不含START/STOP、拉伸、调度、驱动调用和故障超时，更不是实测。完整相位延迟还包含PWM锁存、电机、皮带弹性/齿隙。
V1硬件改变IMU/总线/功率接口后必须重测，不能保留原增益并仅换输出单位。

原core每帧累计最大值；run/wake/jitter直方图100us桶，报告桶上界，不伪称精确微秒分位数。
串口CSV采样分位数与设备所有帧最大值分别记录；sample_missed、log_dropped、command_overflows、reply_dropped含义不合并。
`software/docs/realtime.md`保留旧profile任务优先级、8帧测速窗口、队列容量和低优先级SPI DMA分块说明。
外部心跳只在完整健康控制帧之后由软件翻转；禁止用自由运行PWM或交互MCU联网存活喂运动看门狗。

## 两域与网页

motion保留控制/传感器/驱动所有权；头部目标经有界轨迹，不阻塞姿态。交互无控制锁，不在实时路径打印或动态分配。
旧SPI后端每块240×8×2=3840B；V1实际屏幕总线与DMA参数未冻结，不能把RGB并行屏当SPI。
交互C双眼渲染为可替换RGB565/Canvas后端；默认240×240缓冲115200B；360×360缓冲259200B。
真实主机基准和C/TS最大几何误差见reports/v1/eyes_render_host.json，含30次p50/p95/max；板上耗时仍null。
20Hz交互循环只是调度设计，不是实测帧率，不承诺60fps。圆形安全区4%，屏幕始终黑底双眼，sleep_visual不改变运动状态。

音频队列8×10ms，16kHz的mic/reference分开；旧帧>80ms丢弃并计数。reference必须来自真实已播放DAC采样，不能用云端生成时间冒充。
ESP-SR2.2.0的MR接口、LVGL9.2.2及esp32-camera2.0.16已做包括打开分支的编译验证，I2S/板级捕获/AFE声学性能没有硬件证据。
浏览器WebAudio的实际currentTime及RMS驱动说话眼睛；打断递增本地播放代次，尚未完成解码的数据不得重新开播。
服务器分别记录首字、首音频生成、收到播放开始/结束、打断请求/收到停止回执。后两者含网络传输延迟，来源HOST_WEB_AUDIO。
本版半双工；真实中文唤醒模型、误检/漏检、设备声学打断/AEC均独立待验。

网页每100ms续租，300ms本机租约；失焦/隐藏/pointerup/连接断开停止续租，不以重连自动重放运动。
遥测每100ms，UI超过250ms标陈旧。RTT用浏览器发送→收到结果，jitter为遥测到达间隔偏离100ms；报告样本数、p50/p95/p99/max、传输序号缺口及命令结果超时。
该分位数使用有界最近256样本；不是网络单向延迟，更不是运动控制延迟。UI源码注明hardware_compute_max=NOT_TESTED。
视频预览限JPEG质量55、浏览器4Hz，模拟检测10Hz；这些是节流设计，不能照搬为真实相机fps。

## 控制与符号离线核验

坐标见contracts/coordinates.md。身体正pitch前倾与头正pitch抬头符号相反。先六面静态求安装矩阵，再手动前倾/手转轮对照。
V1控制x=机械Y、y=−机械X、z=机械Z；左轮位于机械X负侧。A0关系留在旧profile，不默默翻转原符号常量。

唯一公共力矩/归一化输出由姿态PD/状态反馈产生；慢速速度环生成受限pitch参考，差动转向用剩余输出余量；只对运动目标和头轨迹限加速度。
不能在平衡纠偏后叠加两个独立轮速PID，也不能给平衡输出施加慢斜率。原core积分限幅/抗饱和与饱和故障测试保留，默认增益0。
旧MC_MOVE.b为差动PWM；MORI/2 yaw是rad/s。物理适配未辨识时拒绝非零yaw，不用未经验证比例硬换算。

`simulation/dynamics.py`的θ″=(gθ−a)/l只做控制方向证伪：正前倾需正向基座加速度；l=0.15m、自然频率5rad/s、阻尼0.8都是ASSUMED。
模型PD由该特征方程推导，输入m/s²，绝非PWM或N·m。加入限幅/死区/噪声/延迟/轮滑，反号或长延迟触发倾倒/饱和。
该模型没有辨识的轮/头惯量，不证明完整位置/速度/姿态闭环，也不向固件导出参数。原始结果以SIMULATED命名。

视觉按原始capture_id在同一本机单调时钟查年龄；采集头角/机身姿态→世界射线→当前机身，不能直接将图像水平偏移当底盘yaw。
图像大小只作相对保守线索；没有深度测量，不报告米级目标距离。未知ID、>250ms、低置信、多目标/遮挡导致停并重新选择。
云VLM不进入移动闭环；设备计算不足则锁定BODY实机模式，保留托架HEAD验证，不通过放宽年龄伪装可用。

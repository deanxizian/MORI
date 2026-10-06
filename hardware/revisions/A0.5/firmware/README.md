# ESP-IDF 最小验证固件

A0.5增量：补齐`ledc_fade_func_install(0)`，轮驱动输出错误会锁存并撤销ARM。此目录是硬件最小基线；并行软件工程的协议、故障处理和HAL继续在`software/`维护，按`../interface_decisions.md`合并差异。

目标ESP32-S3-DevKitC-1-N8R8 **v1.1**，ESP-IDF **v5.5.2**。源码已构建；物理I/O/电机/头/屏/自由平衡全部NOT_TESTED。不能把elf/bin生成当成硬件功能通过。

```sh
cd /Users/dean/Documents/MORI
source /Users/dean/esp/esp-idf/export.sh
idf.py -C hardware/revisions/A0.5/firmware build
sh hardware/revisions/A0.5/tests/run_host_tests.sh
sh hardware/revisions/A0.5/tests/run_adapter_tests.sh
```

初始化时最先将ARM和电机PWM设为0。sdkconfig默认MORI_POWER_STAGE_VERIFIED=n、MORI_ENABLE_BALANCE=n、MORI_HEAD_VERIFIED=n；GC9A01屏幕测试为y。启用功率级前必须完成test_plan B独立电路资格和A–C相关项；完整D/E电机测试之后才可能进F/G。不开启开关时命令必须被拒绝，不能为了看到电机转而绕过。

目录：components/mori_core为可注入SI样本的主机可测试状态机；main/motor、encoders、sensors、display为HAL；main.c拥有控制任务、指令队列、日志队列。deps锁定esp_lcd_gc9a01 2.0.3。WHEEL_M_PER_COUNT对应4863与1:1传动979.616counts/rev；所有符号目前是待实测初值。原始IMU→控制坐标仍是单位映射，必须在实装前配置真实安装矩阵。机械模型L/R与控制左右相反，参见architecture.md。

使用DevKit USB-UART口、UART0控制台，默认115200；插USB前拔J12逻辑降压模块连接器，保留J14的DevKit 5V/编码器供电链路，保持厂家规定的逻辑供电互斥，USB供逻辑时禁Wi-Fi且总逻辑电流<500mA；不要把下载/连接USB当作解锁。没有指定实物端口，本工程没有执行flash。要刷机时先抬起/可靠支撑，断开功率使能，确认自己的端口及固件哈希；不提供会自动刷未知设备的脚本。

|命令|语义与门槛|
|---|---|
|calibrate|静止1024个合格IMU帧校准陀螺bias，不出力|
|arm bench|已核验功率级、READY、健康；一次最多200ms|
|duty L R|归一化输出，绝对值≤0.12，仅BENCH；不延长期限|
|confirm_signs|只有人工已验证符号才可发，不自动生成|
|gains kp kd kv ki|姿态P/D及速度参考P/I；默认0，没有已适配增益|
|arm balance|两编译门、方向、校准、电池和直立门限；实验功能|
|move v yaw|v单位m/s，yaw是归一化差动力矩指令不是rad/s；最大0.3/.10；运动目标限加速度0.2m/s²|
|stop|速度/差动目标归零，保持健康平衡|
|disarm|关闭驱动；要有可靠支撑|
|ack|解除已排除原因的FAULT，不解锁/不自动出力|
|head deg|头部目标角，初±50°；HEAD_VERIFIED=n时拒绝|

控制定义：θ=atan2(-a_x,a_z)，正值表示机身前倾；正gyro_y对应θ增加；正输出让两轮向前。速度误差生成受限±5°倾角参考；姿态u=kp(θ−θ_ref)+kd·gyro。正运动指令初始可产生小幅轮后退以建立前倾，随后追赶；必须用实机符号实验检验，不能因为直觉看起来“反”就翻转一个环。没有平行的轮速PID直接叠加争抢H桥。速度积分仅在未饱和/未夹参考时更新；总输出±0.65，转向只用剩余余量。底层平衡输出没有人为慢斜率。

互补融合τ=0.5s为占位参数，只在加速度模长8.8–10.8m/s²采用倾角纠偏；运动加速度仍可能污染估计。PCNT累加硬计数，8帧速度窗口和1us毛刺过滤可调整。屏幕任务独立SPI DMA，每条8行，10fps。头轨迹30deg/s、60deg/s²为初调值；270°标称脉宽需实测，关PWM不等同于断头供电，急停NC2负责实际断电。

基线CSV日志有时间、状态/故障、姿态、速度、电压、电流、温度、输出、当前/最大运行耗时、唤醒延迟、抖动、丢帧和拒绝标志。日志队列长度1覆盖旧帧，不阻塞控制；这不适合未经扩展的高频辨识采集。没有UART实物输出，reports中只有真实编译/主机测试日志。

已知待软件并行任务改进：严格完整行解析/ACK与版本协议、持久化审阅过的参数、可替换安装矩阵、模拟HAL、串口采集回放、日志丢弃计数及分段时序。不要把这些待办误写为已完成。现有sscanf解析会接受部分尾随字段，输入NaN/Inf虽在核心拒绝，仍需要更严格协议测试。

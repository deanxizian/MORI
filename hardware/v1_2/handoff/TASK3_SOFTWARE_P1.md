# 可直接交给软件任务的提示词

继续 `/Users/dean/Documents/MORI` 已有 MORI V1.2 软件工程，接入硬件候选版本 **V1.2-H0.2-P1**。保留既有网页、后端、模拟器、持久记忆和回归测试；当前用户只开发网页、App 暂停。不要另起一套运行固件，不连接/扫描/刷写实物，不远程部署。

先读项目 AGENTS、`MORI_SPEC_V1_2.md`、`README_SOFTWARE_V1_2.md`、`contracts/components.json`、`contracts/electrical_interfaces.json`、`hardware/pinmap.csv`、`hardware/v1_2/reviews/engineering_review.md`、`reports/decisions/ADR-HW-V1_2-002.md` 和 `hardware/v1_2/reports/s288_reference_audit.json`。硬件与机械契约只读；软件继续拥有现有 `contracts/wire.*`、协议、profile 和正式固件。变更通过接口变更单反馈。

硬件主路线仍为 S288×2、SCS0009×2、微雪33700 OV3660、微雪35079圆屏、身体ICM-42688-P。两颗应用MCU。P1使用 **WeAct STM32F4 64Pin CoreBoard V1.1 / STM32F412RET6** 的明确适配候选；这与现有F413镜像不同。新增可选择的F412板型，保留F413禁驱构建，不把二进制互刷。核验F412启动文件、512KB Flash/256KB SRAM、链接脚本、CMSIS宏、HAL支持和调试脚。

先完成可离线开展的代码、编译和注入式测试：

1. **板级时钟与资源。** HSE8MHz；PLL M8/N192/P2/Q4；SYSCLK/AHB/APB2=96MHz，APB1=48MHz，USB48MHz，Flash3WS/VOS scale1。USART1 PA9/PA10 AF7，6Mbps8N1、BRR16；USART2 PA2/PA3 AF7，1Mbps、BRR48；USART6 PC6/PC7 AF8，1Mbps、BRR96。DMA分配以电气契约为准，不能重复占用stream。SPI1 PA5/6/7、PA4 CS、PB0 DRDY；初始SPI6MHz、ODR1kHz只是目标。先核验HAL/CMSIS配置和宿主测试，实际时钟/波形保持NOT_TESTED。
2. **默认禁驱和本机故障。** PB7 ARM_CLK只能明确本地解锁后发新上升沿；PB8 CLR_N必须开漏，禁止推挽拉高。PB5/PB6为两路OE请求，复位/未ARM时禁止发送有力矩命令。PC5回读ARM、PB3读FAULT_N（关闭JTAG、保留SWD）、PC4读CHG_N、PC13功能按钮。启用IWDG；启动、复位、锁存故障、维护/充电均不可自动ARM。普通按钮不能等同复位或突然断驱。
3. **三条总线分开。** S288为6Mbps单线TTL半双工，SCS为独立1Mbps半双工，MCU间为独立1Mbps全双工。先复用现有严格MORI/2帧、128B载荷/158B帧、CRC32/session/sequence/命令租约；禁止新造不兼容帧。CAM UART0 GPIO43 TX/44 RX占用J11并与SD相关资源互斥，不启用SD，启动日志视为噪声。坏包、半包、缓冲堵塞、交互重启和重复ID不能续租。CAM失联撤销主动位移，健康运动域继续平衡；不把300ms租约直接切成平衡扭矩开关。
4. **S288适配与计时。** 采用明确的20B请求/26B反馈候选，记录厂商协议/C/Python冲突。已确认的HOST CRC比较不能替代实机帧资格。负数位置、uint8温度/错误位及截断/舍入必须有固定策略及边界测试。转子角/输出角/齿比只换算一次；输出8192状态/转不是AB编码器×4。协议整数不直接作为Nm。USART TC后才释放OE，不能以DMA完成代替；剔除本机echo，两个有ID轮驱顺次轮询，每个窗口有界，不无限重试。建议500Hz/每轮400µs回包窗口作为待测起点，注入超时/旧反馈/CRC错/总线堵塞测试。
5. **IMU与电源。** 完成ICM初始化、量程/ODR/滤波、DRDY硬件时间戳和SPI DMA，记录量测年龄，机身安装矩阵需显式标定。PC0=BAT_ADC、PC1=WHEEL_ADC、PC2=电池放电电流；电压分压100k/27k，INA180A1+10mΩ为0.2V/A，不能称可读取充电电流。VREFINT、零偏和分压校准未测。3S低电10.8/10.2V仅为硬件讨论起点，默认运行门保持关闭，不能继承旧2S阈值；正式阈值依电池及掉压实测。
6. **头部、视觉和声学。** SCS0009有回读，但真实版本、ID、方向、机械零点与限位未测。头控低优先级且有反馈年龄；不以舵机角度无条件代替相机光轴。头yaw±60°、pitch−20°到+25°属于机械目标，读取最新联合可达域，不覆盖机械真值。屏为360²、ST77916 QSPI，有效直径45.68mm；CAM端TE未连接。OV3660先按JPEG拍照和QVGA目标10fps搭适配；显示/相机/I2S/Wi-Fi并发测P95/P99年龄、水位、丢帧与内存。超250ms撤跟随位移，保留平衡。ES8311播放参考经模拟AEC路径进入ES7210 MIC3，TDM实际槽位需板级验证，不能只有AEC配置名。MORI离线唤醒模型尚无，保持按钮和现有公开模型的开发路径，标出自定义模型缺口。

请交付板型适配代码、构建日志、资源冲突检查、故障注入测试、模拟遥测/调试工具、接口变更单和实测记录模板。所有实物增益、转矩限幅、轴向与上电资格默认关闭；不复制硬件离线LQR增益。必要的compile-only覆盖镜像标DO_NOT_FLASH。S288连续能力、TTL门槛、制动回灌、相机延迟、热与60分钟续航一律NOT_TESTED。

用户目前没有任何器件，工具只有万用表与限流电源。6Mbps/回灌验证需借用示波器和逻辑分析仪，STM32还需SWD工具。不能为展示效果生成假的实测曲线、温升、真实站立或已支持MORI唤醒的结论。

硬件已有三个原生KiCad原型：运动70×35mm、IMU20×16mm、电源80×45mm。电源板不符合旧44×16×10mm分配；电池、USB-C3S充电模块、完整国内成本仍未冻结。可以独立完成上述软件工作，不将这些硬件缺口包装成已放行上电。

# 参考与依赖审查

实际参考 commit、源文件 SHA256、取得日期在 `refs/sources.lock.json`。首次 GitHub API 受限的记录保留，
随后用公开仓库 Git commit 与 raw 文件取得锁定资料。参考仓库归档没有直接加入应用主循环。
主工程为 MORI 自有 motion / interaction / backend；只移植 bloub 双眼所需函数，其他模块通过明确接口适配。

| 来源 | 阅读事实与决策 | 编译/许可边界 |
|---|---|---|
| rig_omni `main/boards/hover/xgo.cc` | `xgo_control()` 实际走 `temp_u=-Kx`；前面的多 PID 路径被注释。运行状态有直立后自动恢复逻辑，MORI不继承。`wheel_x`写死0.06m、1024计数；姿态用deg；tor先转short再同步串口发给多个ID，未见N·m标定。三次2ms延迟加处理/串口，注释Ts≈6ms不是实测。yaw-q_head与头补偿按其结构，不能移植到身体IMU | 未发现仓库顶层 LICENSE，**不复制其实现**。只记录分析。保留原有有刷台架驱动，不把FOC串口当PWM |
| StackChan-BSP `servo.h/cpp` | 有限位、动画与反馈/估计接口。默认 `setAutoTorqueReleaseEnabled` 为true，静止200ms后可能卸扭矩；MORI双轴重力负载不能照搬。MORI采用SI限速/限加速度轨迹，静止保持目标 | MIT；参考，不复制弹簧主循环。原 stack-chan 仓库 Apache-2.0，亦未整体fork |
| bloub `src/bot/face.ts/math.ts` | 保留原文件对照；抽取正交投影、眨眼、视线漂移。MORI新增8状态、从当前合成帧中断切换、RGB565圆形裁切和皮肤接口。原眨眼表900s结束，MORI以905s周期复用眨眼表，视线噪声时钟不重置 | MIT (Jérémy Perret 2026)，C与TS逐文件通知。仅代码许可，不是Grok/xAI形象商业授权 |
| 小智 ESP32 当前参考 | 锁定主线的依赖要求 IDF≥6.0.1、ESP-SR2.4.7、LVGL~9.5，不能硬塞进5.5.2。采用协议v1 hello/listen/abort/Opus会话与适配器，禁MCP执行工具 | MIT；未复制整套Application。服务端参考 xinnan-tech 为社区兼容实现，不宣称官方云源码 |
| ESP-SR | 本机实际编译锁定2.2.0。`MR`为mic/reference两个声道的AFE输入契约；实际参考须来自DAC已播放采样。模型分区已参与构建，自定义词未提供 | Espressif MIT限制用于Espressif产品。现成测试唤醒候选“你好小智”与MORI自定义训练/费用/模型条款需分别核验。误触发/漏检、远场、AEC效果NOT_TESTED |
| LVGL | 实际依赖9.2.2，Canvas RGB565适配。未把SVG mask直接交给驱动；逐像素胶囊几何与圆形安全区先合成 | MIT。240/360主机渲染测量不代表ESP32帧率，不承诺60fps |
| esp32-camera / ESP-WHO | 前者实际编译2.0.16，初始化需明确camera_config与验证门。ESP-WHO仅参考候选；未复制其全应用或声称轻量人脸已经跑在目标板上 | 相机驱动Apache-2.0，WHO Espressif MIT；模块引脚/内存/吞吐未实测 |

工具链：两个域均固定 ESP-IDF5.5.2，各自 dependencies.lock。交互解析到 ESP-DSP1.6.0、dl_fft0.7.0、
esp_jpeg1.3.1（完整哈希见锁文件）。默认门全部n，单独编译门分支验证不等于允许烧录。

网页 Vue3.5.13/TS5.8.3/Vite6.3.5，Capacitor7.2.0/App7.0.1。依赖全由 pnpm-lock.yaml 锁定。
原生 iOS 用 SPM exact7.2.0 与 Package.resolved commit；Xcode27要求最低目标15与UIScene，已适配。
SPM下载在本机挂起时，只对本地生成缓存改为已经 SHA256 核对的同版官方xcframework，应用锁文件未改版本。
原生 Android 模板 Gradle8.11.1（校验和锁定）需JDK21/SDK35；本机缺Java，实际构建BLOCKED。

Python直接依赖与解析依赖分别在 backend/requirements.in、requirements.lock；PyAV14.4.0在此平台没有可用wheel，
构建缺pkg-config/FFmpeg，真实失败日志保留，明确改锁有arm64 wheel的16.0.1。Opus编码/解码回环已通过。
容器 Python/Caddy 精确 tag + registry digest 已核对；本机无Docker，Compose启动NOT_TESTED。
第三方完整许可放 docs/licenses 和包自带文件；将来商业分发还须审查模型权重与FFmpeg轮子实际组件，不以本文件代替权利许可。

Apple生命周期依据：[UIKit 场景迁移](https://developer.apple.com/documentation/technotes/tn3187-migrating-to-the-uikit-scene-based-life-cycle)。
相机依赖依据：[Espressif 2.0.16](https://components.espressif.com/components/espressif/esp32-camera/versions/2.0.16)。

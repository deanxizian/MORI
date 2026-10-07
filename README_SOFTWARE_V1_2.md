# MORI V1.2 软件

本工程已按用户提供的 `MORI_SPEC_V1_2.md`、`software/inputs/v1_2/03_CODEX_SOFTWARE.md` 更新，保留已有软件与旧台架回归。**当前只开发网页，App 暂停**，这个用户要求优先于附件中的 App 条目。

网页、模拟设备、语音 mock/服务适配、SQLite 记忆、视觉像素输入及有界活动/跟随/巡游继续可运行。运动默认构建改为 STM32F413；新增 S288、SCS0009、ICM42688 数据解析、安全核心与分段计时钩子。交互改为 16 MB Flash、360×360 目标，锁定并编译 ST77916 QSPI、ES7210/ES8311、CH32V003 与 OV3660 相关依赖。

**机器人是否已经能自平衡站立：尚未验证。** 新 STM32 镜像是禁驱启动镜像；编译和模拟不代表实机已接通、能旋转或能平衡。`reports/v1_2/acceptance.md` 区分实现、HOST_TEST/SIMULATION 与 BENCH/ROBOT。

## 启动网页

在 `/Users/dean/Documents/MORI` 的两个终端中运行：

```sh
.venv/bin/python -m backend.run
bash tools/node-env.sh dev
```

打开 http://127.0.0.1:5173 ，用 `.state/pairing.txt` 的一次性码绑定本地模拟设备。取得控制权 → 明确勾选模拟解锁 → 前进 100 mm → 停止移动。停止后健康模拟平衡继续；松手、失焦、隐藏、断线终止续租。刷新或重连不重放旧动作。

视觉页 TRACKING → 确认目标 → 头跟踪/模拟底盘跟随；多人/遮挡/陈旧帧/头角反馈失效撤销位移。仅限清场、看护、无台阶环境的未来实测；当前不宣称避障、防跌落或自由巡游。连续视觉不默认上传或留存。语音默认 mock 回复及测试音，不能当作真实中文 TTS/AEC/自定义唤醒成功。

## 构建与验证

```sh
# 全部主机、原回归、协议、Web 类型/构建和 360×360 双眼测试
.venv/bin/python tools/verify-v1_2.py
# 桌面与手机尺寸 Chromium；需先启动上面的 Vite
MORI_REPORT_ROOT=reports/v1_2 .venv/bin/python tools/record.py browser_local -- bash tools/node-env.sh exec playwright test --config apps/console/playwright.config.ts
# 两域固件，只构建
bash tools/build-firmware.sh motion
bash tools/build-firmware.sh interaction
# 保留原 ESP32 台架工程的显式入口，不适用 V1.2 接线
bash tools/build-firmware.sh legacy-motion
# 离线协议及命令回放，无串口连接
.venv/bin/python -m simulation.s288_replay simulation/fixtures/SIMULATED_s288.jsonl --output reports/v1_2/SIMULATED_s288.csv
.venv/bin/python -m simulation.replay simulation/fixtures/SIMULATED_session.jsonl --output reports/v1_2/SIMULATED_commands.jsonl
.venv/bin/python -m simulation.dynamics --output reports/v1_2/SIMULATED_dynamics_v1_2.json
```

新机器：Node 24.19.0/pnpm 11.19.0、Python 3.12，按 `pnpm-lock.yaml`、`backend/requirements.lock` 安装。STM32 使用 Arm GNU 14.2.Rel1、CMake/Ninja；运行 `python tools/fetch-v1_2-refs.py` 获取锁定源码，`python tools/bootstrap-arm.py` 下载并校验工具链，或设置 `MORI_ARM_BIN` 为已核验工具链的 bin 目录。ESP-IDF 固定 5.5.2，本机路径 `/Users/dean/esp/esp-idf`；可用 IDF_PATH 指定同版本。没有自动安装系统服务、打开端口、扫描串口、刷写或远程部署。

构建输出：`firmware/motion/build_stm32/mori_motion.elf/.bin`；`firmware/interaction/build_v1_2/mori_interaction.bin`。STM32 只启用内部 HSI 和 HAL 系统 tick，没有假造板 GPIO、PLL、收发器使能或驱动功率链；纯算法/协议模块已编译并在主机测试。电机 DMA/SPI 端口接线、实时调度、物理命令桥、ICM 初始化/滤波配置仍待板契约接入，不能把这个镜像当作可直接驱动整机的成品。

## 版本与兼容

| 项目 | 当前软件 | 物理边界 |
|---|---|---|
| 控制台/后端 | 1.2.0-dev.1，MORI/2 向后兼容字段扩展 | 仅模拟连接，实机解锁 BLOCKED |
| STM32 | F413 CMSIS v2.6.10 + HAL v1.8.3；Arm GCC 14.2.1 | 板型/时钟/管脚/安全链未释放 |
| S288 | 显式 20/26 字节、独立 CRC、齿比一次转换、TC 方向释放状态、限时双轮轮询 | 停止语义、电平、6 Mbps 波形、实际带载扭矩未测 |
| SCS0009 | 大端位置/速度/负载反馈；需标定的 joint 映射；联合可达域回调 | 零点/带载限位/联合区域/重力保持未测 |
| ICM42688 | WHO_AM_I 与 14 字节 SI 解码、正交旋转矩阵校验 | 模块、SPI/DRDY、量程/滤波/零点及实时驱动接入待核 |
| 交互域 | IDF 5.5.2、LVGL 9.2.2、ESP-SR 2.2.0、camera 2.1.4、codec 1.5.4、ST77916 1.0.1、CH32 1.0.1 | FPC、电源、音频槽、AEC、相机/显示/音频/Wi-Fi 同时运行未测 |
| 电源/控制 | 3S 候选；保护阈值 null，实机增益与出力上限 0 | 不继承旧 2S 阈值或 PWM 增益 |

MORI/2 保留相同 33 命令。新增软件/参数版本与 `sensors.*.valid`；没测量的数值和采集时间均 null，已有模拟关节估计单独保留。默认软件 profile 在 `contracts/software_profile.json`，只记录软件目标与门控；机械/电气真源仍由硬件任务维护。

并行任务已更新 `V1.2-H0.1` 电气与 `V1.2-M1` 机械契约，本轮读取合并，未编辑它们。新电气契约已采用 MORI/2 128 字节载荷/158 字节帧；板间波特率仍 null。几何轮径 95 mm 等属于结构 ASSUMED，不自动升级为控制标定。文档提及但未提供的 AGENTS_MORI_TEMPLATE.md、04_HANDOFF_AND_ACCEPTANCE.md、REFERENCES.md 未冒称已读。

台架步骤/记录：`docs/debug_manual_v1_2.md`；分段时序：`docs/realtime_v1_2.md`；变更：`software/interface_change_requests.md` / `reports/decisions/ADR-SW12-001.md`；依赖与许可：`software/THIRD_PARTY_V1_2.md`。

离线动力学补充了供电能力下降、头部质量/惯量与pitch反作用，保留延迟、饱和、死区、噪声和轮滑。它仍是 **ASSUMED 加速度输入模型**，不等同 S288 扭矩对象；说明及未建模项见 `docs/dynamics_v1_2.md`。实机增益保持0。

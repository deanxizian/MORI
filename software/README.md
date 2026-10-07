> **当前 MORI V1.2 入口：** [README_SOFTWARE_V1_2.md](../README_SOFTWARE_V1_2.md)。当前只开发网页，App 暂停。本页及原报告保留为HW-SW-0.4/A0台架记录，旧GPIO/电池阈值/PWM/CPR不适用V1.2。
> 固件源已原样迁移并增量适配到 `../firmware/motion/`，`firmware_work/firmware` 是兼容符号链接，没有第二份硬件固件。V1默认不初始化旧候选GPIO。

# MORI软件调试工程 SW-0.4

当前接口基准 **HW-SW-0.4 / 2026-09-21**，已依用户本次指令在现有工作副本上合并，模块台架候选，**PROTOTYPE / UNVALIDATED**。保留既有状态机、严格协议、模拟HAL、安装配置、表情/头轨迹和安全回归修复。没有连接、烧录或旋转真实设备；实物与自由平衡均 **NOT_TESTED**。

## 本次接口同步

轮电机候选改为Pololu #4863：48 CPR已含x4，精确减速比22³×23/(12×10³)，1:1候选皮带，979.616 counts/rev，Ø95轮每计数0.000304661522567m。运行时换算只定义于`mori_io.h`，设备INFO与模拟源共用配置；单边沿8帧测速、48边沿一电机转和元数据精度均有回归测试。GPIO、方向符号、IMU量程、保护阈值和默认安全门未改变。

编码器使用DEVKIT_5V供电，四条A/B经3.3V供电的SN74LVC14AD转换，禁止5V信号直入ESP32。USB前拔**整个J12逻辑降压线束，J14保持连接**；逻辑USB/外部5V互斥，禁Wi-Fi，含编码器预算<500mA。控制left对应Blender Wheel_R/Motor_R（X正）。VMAIN ADC不能覆盖可能被隔离的VM_MOTOR回灌尖峰，软件过压阈值保持8.65V。详细线序、钳位候选和限制见`docs/hw_sw_0_4.md`及调试手册。

本次接收的0.4快照23个成员均按manifest校验；基线在独立报告目录重新构建。最早从0.3解出的工作副本没有被覆盖，`baseline_integrity.json`保留原始追溯。旧发布报告归档到`reports/pre_hw04_merge/`；24个旧SIMULATED文件保留原内容和元数据，0.4演示另生成`SIMULATED_hw04_*`。此前接口兼容性FAIL的历史记录保留，其变更依据与解决结果见ICR-012、`reports/hw04_adoption.json`和当前`reports/final_validation.json`。

## 可运行入口

在`/Users/dean/Documents/MORI`执行：

```sh
# C主机回归、安全状态机、模拟HAL、严格协议及电机适配器（ASan + UBSan）
bash software/scripts/test_host.sh
# Python协议、采集/回放、模拟PTY串口、离线方向核验
python3 -m unittest discover -s software/tests -p 'test_*.py' -v
# ESP-IDF v5.5.2安全门关闭的默认配置构建，只build、不flash
bash software/scripts/idf_build.sh
# 校验仓库内附带的0.3/0.4 ZIP快照，不能代替当前代码或实机验证
python3 software/scripts/verify_delivery.py --archives-only
# 旧交付的完整审计需要另行恢复历史证据和当时构建产物；当前源文件已演进，可能报告差异
python3 tools/restore_archive_assets.py --group legacy-software-verification --group legacy-helpers
python3 software/scripts/verify_delivery.py
# 严格检查与本次已采纳0.4上游一致；不代表实物获准上电
python3 software/scripts/verify_delivery.py --require-current-handoff

# 无硬件演示：输出文件名必须含SIMULATED；换用新的文件名避免覆盖
bash software/scripts/build_simulator.sh
python3 software/tools/mori_cli.py simulate --frames 1000 --scenario estop --output software/reports/SIMULATED_demo_new.csv
python3 software/tools/mori_cli.py replay software/reports/SIMULATED_demo_new.csv
python3 software/tools/mori_cli.py validate 'move 0.02 0'
python3 software/tools/mori_cli.py fault 11
python3 software/tools/check_control_signs.py --output software/reports/SIMULATED_direction_new.json
software/reports/bin/SIMULATED_face 360 software/reports/SIMULATED_face_360_new.ppm
```

主机工具只用Python标准库和本地C编译器；串口使用POSIX termios（本次只在模拟PTY验证）。设备端仍用项目原dependencies.lock：ESP-IDF5.5.2、GC9A01 2.0.3、cmake_utilities0.5.3，未升级。`idf_build.sh`检查本地IDF tag严格等于v5.5.2。工作副本主机脚本指向software的安全包装；0.4上游基线另在reports中构建和运行，不执行hardware目录脚本。

真实串口须由用户以后明确提供端口再操作。采集只自动发info查询；`send --command`只发送显式提供的命令，支持多次`--command`完成有限台架脉冲。绝不自动发arm、confirm_signs、gains或ack，不自动重试/重连。ACK丢失是UNKNOWN，不推断执行失败，也不自动disarm。

## 目录与证据

- `firmware_work/firmware/`：以0.3ZIP为初始来源、已选择性合并0.4接口的独立ESP-IDF工程；portable `mori_core`、真实HAL、圆屏驱动。
- `firmware_work/pinmap.csv`及`wiring.csv`：0.4交接镜像，只读对照；GPIO未改。
- `tests/`：注入式时钟/传感器/执行器HAL、原问题回归、IDF LEDC契约stub和协议/工具测试。任意测试增益仅用于分支验证，不是实机调参数据。
- `tools/`：MORI/1串口采集、CSV回放、SIMULATED设备与表情渲染、方向/安装矩阵检查。
- `docs/debug_manual.md`：断电到低速运动的八阶段实物调试流程；`protocol.md`、`realtime.md`、`direction_checks.md`给出接口和测量口径。
- `config/`：实物记录及安装矩阵模板；未填项均NOT_TESTED/null。
- `interface_change_requests.md`：ICR-001..012，ICR-001旧电机提案已废止；ICR-012记录本次授权合并，其余安全/协议修复保留。
- `reports/`：真实命令/退出码/日志、快照与最终文件/镜像SHA、模拟CSV/JSONL/元数据；Git仓库不存在，Git状态NOT_APPLICABLE。

## 本次真实验证结果

- 修改后的C测试：2406条断言（163原始核心 + 2211模拟HAL/状态/协议/UI + 22电机适配器 + 10默认关门）及4项行为回归PASS，开启ASan/UBSan。
- Python：24项PASS，含5项HW-SW-0.4计数/8帧测速/元数据/接线验收，以及串口模拟PTY和严格协议/回放测试。
- ESP-IDF v5.5.2：默认关门、无屏、门内代码编译覆盖3种构建PASS；另在独立目录复现0.4上游基线构建及163断言PASS。
- 0.4模拟急停1000帧、复位400帧采集/回放PASS；旧版回放保留1204.44元数据，24个旧模拟文件哈希未变。
- 先前FAIL记录保留：0.4接口前置回归、主机测试中的float/double比较警告（已修正），以及构建路径纠正记录。当前结论/命令/退出码见`reports/final_validation.json`，源文件/产物SHA见`reports/delivery_manifest.json`。实物全部NOT_TESTED。

```sh
# 验证已生成的新旧版本模拟记录，无设备IO
python3 software/scripts/verify_hw04_recordings.py
# 读取0.4采集结果；不会将CSV重发为设备命令
python3 software/tools/mori_cli.py replay software/reports/SIMULATED_hw04_estop.csv
```

## 验证范围

| 功能 | 功能实现 | 单元/模拟或主机构建 | 实物验证 |
|---|---|---|---|
| HW-SW-0.4快照、接口同步、基线构建和163断言复现 | PASS | PASS | NOT_TESTED |
| DISARMED→CALIBRATING→READY→BENCH/BALANCE、锁存FAULT | PASS | PASS | NOT_TESTED |
| 默认关门/0增益、显式解锁、台架限幅/不续期、stop/断联语义 | PASS | PASS | NOT_TESTED |
| 故障注入：IMU旧/缺样、编码器跳变/冻结、ADC/NTC、过流/温/压、倾倒、饱和、nFAULT/急停、超时/溢出/复位 | PASS | PASS | NOT_TESTED |
| 严格MORI/1、ACK/REJECT、时间戳、回放、分位数/丢弃计数 | PASS | PASS | NOT_TESTED |
| 矩阵/正反号配置、速度外环→倾角→唯一公共姿态力矩 | PASS | PASS（符号关系，不是稳定性证明） | NOT_TESTED |
| 无屏/可变分辨率/圆形裁切/GC9A01 SPI后端 | PASS | PASS（编译/渲染） | NOT_TESTED |
| 头部限加速度轨迹与低优先级任务、未核验无PWM | PASS | PASS | NOT_TESTED |
| 1800us预算/健康帧心跳/分段测量钩子 | PASS | PASS（模拟超时与门控） | NOT_TESTED |
| 装机适配、真实电气/热/稳态/自由平衡/续航 | NOT_TESTED | NOT_APPLICABLE | NOT_TESTED |

本轮基线问题先记录FAIL，再修复并重跑：重复时间戳校准、首个故障被覆盖、READY失健康不锁存、额外命令字段被接受、提示词与快照的轮计数比例冲突、200ms台架截止晚一个帧、IDF同步LEDC更新缺少fade service初始化、BENCH输出覆盖低电告警。最终验证结果见`reports/final_validation.json`；历史FAIL日志保留用于复现，不伪装成硬件失败或抹除。

安全默认：POWER_STAGE_VERIFIED、ENABLE_BALANCE、HEAD_VERIFIED、AXES_VERIFIED均n，kp/kd/kv/ki全0。左右电机/编码器符号候选保持+1/−1；安装矩阵identity未验证。新增/修改接口必须走变更单。电池阈值保持6.8/6.6/6.0V及过压8.65V，不能代替BMS/保险/充电器/急停。屏幕240×240/Ø32.4mm仅编译与台架后端，最终Ø60屏仍未定。

## 追溯与再次构建

```sh
# 每次使用新的name，工具拒绝覆盖已有记录
python3 software/scripts/run_recorded.py --name local_build_01 -- bash software/scripts/idf_build.sh
python3 software/scripts/run_recorded.py --name SIMULATED_local_tests_01 -- bash software/scripts/test_host.sh
# 单独复现已封存HW-SW-0.4基线（报告区，不覆盖工作副本）
bash software/scripts/reproduce_hw04_baseline.sh
# 修改源文件后先完成验证，再更新交付哈希；不可用更新哈希掩盖检查失败
python3 software/scripts/fingerprint.py
python3 software/scripts/verify_delivery.py
```

`run_recorded.py`记录argv、cwd、UTC、返回码、完整输出及SHA；新记录也含运行前输入文件SHA。`baseline_integrity.json`保留最初0.3ZIP21个成员；`hw04_adoption.json`记录0.4ZIP23个成员、源文件和旧模拟文件SHA。默认镜像在`firmware_work/firmware/build/`。`build_variants.sh`只作无屏和门内代码编译覆盖；其`DO_NOT_FLASH_gated_coverage`镜像不具备实物签字，禁止用于台架出力。IDF自动输出的flash建议没有执行。

仍需硬件决定/提供：R矩阵与四个方向符号签字、真实皮带齿数/轮周长、功率安全链与母线回灌响应、最终电池/保护/充电路径、显示面板及总线、头中心/方向/行程/线缆、板卡和IMU外置或机械重排。仍需实测：所有通电/旋转/关断波形、传感器标定、时序最大值、负载干扰、扭矩/摩擦/惯量/热裕量及防摔下闭环表现。未完成这些项目，不宣称机器人已经能平衡。

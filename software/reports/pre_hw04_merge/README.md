# MORI软件调试工程 SW-0.3

需求基准 **用户提示词 HW-SW-0.2 / 2026-09-21**，模块台架候选，**PROTOTYPE / UNVALIDATED**。本次只在software/写入；本任务未改硬件原快照、BOM/GPIO/wiring、根机械参数与模型。没有连接、烧录或旋转真实设备，机器人能否平衡为 **NOT_TESTED**。

## 并行交接版本差异

**与当前HW-SW-0.4的轮电机接口兼容性：FAIL（尚未合并）**。开始读取manifest时为0.2；实际解压前上游已更新为0.3，`baseline_integrity.json`在05:25 UTC如实保存了0.3版本/哈希，基线编译/163断言复现针对该解压副本。其计数常量与本条用户提示词不符，因此本软件工作副本按用户给定的#5216/1204.44计数每转完成。最终检查又发现上游已到0.4、候选轮电机为#4863/979.616计数每转。没有把这个差异默默合并。

已保存与实际解压manifest及全部21个成员SHA相同的0.3归档（ZIP容器SHA不同）和观察到的0.4材料到`reference_sources/`，差异见`reports/handoff_drift.json`及变更单末尾。软件功能/构建/模拟验证与上游接口兼容性分开。当前固件默认禁止出力，**在明确选定基准并合并/重新核验前，不得用于0.4硬件台架**。`verify_delivery.py --require-current-handoff`会对这个差异返回FAIL。

## 可运行入口

在`/Users/dean/Documents/MORI`执行：

```sh
# C主机回归、安全状态机、模拟HAL、严格协议及电机适配器（ASan + UBSan）
bash software/scripts/test_host.sh
# Python协议、采集/回放、模拟PTY串口、离线方向核验
python3 -m unittest discover -s software/tests -p 'test_*.py' -v
# ESP-IDF v5.5.2生产默认配置构建，只build、不flash
bash software/scripts/idf_build.sh
# 原始快照/机械参数/lock/pinmap哈希、GPIO和安全门检查
python3 software/scripts/verify_delivery.py
# 上电前严格检查当前上游一致性；当前因0.4差异会FAIL
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

主机工具只用Python标准库和本地C编译器；串口使用POSIX termios（本次只在模拟PTY验证）。设备端仍用项目原dependencies.lock：ESP-IDF5.5.2、GC9A01 2.0.3、cmake_utilities0.5.3，未升级。`idf_build.sh`检查本地IDF tag严格等于v5.5.2。原版主机脚本含hardware/路径，已替换工作副本脚本为指向software的安全包装，不能运行旧路径脚本覆盖硬件报告。

真实串口须由用户以后明确提供端口再操作。采集只自动发info查询；`send --command`只发送显式提供的命令，支持多次`--command`完成有限台架脉冲。绝不自动发arm、confirm_signs、gains或ack，不自动重试/重连。ACK丢失是UNKNOWN，不推断执行失败，也不自动disarm。

## 目录与证据

- `firmware_work/firmware/`：从已校验的0.3ZIP解出的独立ESP-IDF工程；portable `mori_core`、真实HAL、圆屏驱动。
- `firmware_work/pinmap.csv`及`wiring.csv`：交接镜像，只读对照；GPIO未改。
- `tests/`：注入式时钟/传感器/执行器HAL、原问题回归、IDF LEDC契约stub和协议/工具测试。任意测试增益仅用于分支验证，不是实机调参数据。
- `tools/`：MORI/1串口采集、CSV回放、SIMULATED设备与表情渲染、方向/安装矩阵检查。
- `docs/debug_manual.md`：断电到低速运动的八阶段实物调试流程；`protocol.md`、`realtime.md`、`direction_checks.md`给出接口和测量口径。
- `config/`：实物记录及安装矩阵模板；未填项均NOT_TESTED/null。
- `interface_change_requests.md`：ICR-001..011，供硬件任务审核合并，含每计数距离冲突、矩阵、协议、时序/队列安全与LEDC初始化修复。
- `reports/`：真实命令/退出码/日志、快照与最终文件/镜像SHA、模拟CSV/JSONL/元数据；Git仓库不存在，Git状态NOT_APPLICABLE。

## 验证范围

| 功能 | 功能实现 | 单元/模拟或主机构建 | 实物验证 |
|---|---|---|---|
| 交接快照校验、基线构建和163断言复现 | PASS | PASS | NOT_APPLICABLE |
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

安全默认：POWER_STAGE_VERIFIED、ENABLE_BALANCE、HEAD_VERIFIED、AXES_VERIFIED均n，kp/kd/kv/ki全0。左右电机/编码器符号候选保持+1/−1；安装矩阵identity未验证。新增/修改接口必须走变更单。电池阈值保持6.8/6.6/6.0V，不能代替BMS/保险/充电器/急停。屏幕240×240/Ø32.4mm仅编译与台架后端，最终Ø60屏仍未定。

## 追溯与再次构建

```sh
# 每次使用新的name，工具拒绝覆盖已有记录
python3 software/scripts/run_recorded.py --name local_build_01 -- bash software/scripts/idf_build.sh
python3 software/scripts/run_recorded.py --name SIMULATED_local_tests_01 -- bash software/scripts/test_host.sh
# 修改源文件后先完成验证，再更新交付哈希；不可用更新哈希掩盖检查失败
python3 software/scripts/fingerprint.py
python3 software/scripts/verify_delivery.py
```

`run_recorded.py`记录argv、cwd、UTC、返回码、完整输出及SHA；新记录也含运行前输入文件SHA。`baseline_integrity.json`包含ZIP21个文件与交接manifest逐项校验。默认镜像在`firmware_work/firmware/build/`。`build_variants.sh`只作无屏和门内代码编译覆盖；其`DO_NOT_FLASH_gated_coverage`镜像不具备实物签字，禁止用于台架出力。IDF自动输出的flash建议没有执行。

仍需硬件决定/提供：R矩阵与四个方向符号签字、真实皮带齿数/轮周长、功率安全链与母线回灌响应、最终电池/保护/充电路径、显示面板及总线、头中心/方向/行程/线缆、板卡和IMU外置或机械重排。仍需实测：所有通电/旋转/关断波形、传感器标定、时序最大值、负载干扰、扭矩/摩擦/惯量/热裕量及防摔下闭环表现。未完成这些项目，不宣称机器人已经能平衡。

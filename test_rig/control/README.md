# 平衡控制源码快照 v184

本目录按原始部署清单逐字节归档 **324 个文件**，清单见 [source_manifest.json](source_manifest.json)。这是树莓派验证车的 v184 平衡与遥控源码，保持原文件字节、默认禁能和保护逻辑。本地状态记录表明 v184 已部署，下一轮实测尚未启动；本次没有 SSH 或重新部署。**不是主项目 STM32 固件，也不是完整 ArduPilot 固件。**

v184 增加行驶松手后的小位置误差容差；实物效果 NOT_TESTED。563 项原有离线测试的记录与本次执行结果分别保存。第 71 轮的 60 秒结果属于 v141/v142，不能归到 v184。来源和状态见 [v184 回执](../evidence/software/v184/receipt.json)、[验证状态](../STATUS.md)。

主要实现：

| 范围 | 文件 |
|---|---|
| 控制与故障退出循环 | [air_trial.py](air_trial.py)、[wheel_check.py](wheel_check.py) |
| BMI323 采样、标定与姿态估计 | [preflight.py](preflight.py)、[calibration.py](calibration.py)、[attitude.py](attitude.py) |
| ArduPilot 俯仰 PID 移植 | [ardupilot_balance_core.py](ardupilot_balance_core.py)、[ground_ardupilot_balance.py](ground_ardupilot_balance.py) |
| 当前遥控/平衡入口 | [two_deck_remote_drive.py](two_deck_remote_drive.py)、[remote_drive_keys.py](remote_drive_keys.py) |
| 历史第 95 轮入口 | [two_deck_native_causal_balance.py](two_deck_native_causal_balance.py) |
| 总线协议、停止确认 | [bench_support/protocol.py](bench_support/protocol.py)、[torque_feedback_guard.py](torque_feedback_guard.py) |
| 有界在线调整、落盘、CAM 提示 | [live_tuning.py](live_tuning.py)、[durable_report.py](durable_report.py)、[cam_indicator.py](cam_indicator.py) |
| 硬件无关回归与上游数值对照 | [tests](tests/) |

`self_righting_*` 等早期试验仍被一些继承关系和回归用例引用，保留以便复现源码。文件名不代表已具备自起能力，也不把这些入口列为正常使用功能。`offline_*/REVIEW.md` 是当时的候选审查记录，不替代最新状态；部分离线分析所用大日志只在原机器上。

## 离线检查

Python 3.12+、POSIX 系统和 C++17 编译器；测试不需要 Pi、USB 舵机、云服务或联网。

```sh
# 从本目录执行
python3 -m unittest discover -s tests -q
```

563 项测试覆盖默认不启用设备、IMU/串口故障、陈旧帧和截止时间、双轮停止、数据包 CRC/符号/预算、调参边界与 ArduPilot 公式对照。数值对照会在临时目录编译已随附的上游函数，不构建整个 ArduPilot。

实际设备依赖为 `pyserial==3.5`、`smbus2==0.4.3`（历史现场 Python 3.13.5）。本包不安装服务，不复制标定文件为默认标定，不提供自动运行命令。显式运行入口要求本机标定、操作者就绪、新鲜反馈和启用参数；默认参数只打印计划。串口设备标识仍保留原试验设备以保持源码哈希，**其他机器不能直接套用**。

CAM 红点和音效接口需要当时的适配固件。该固件、私人云账号配置和所有第二层应用未打包；只有控制回归能在干净环境独立复现。源码清单本身是运行前校验输入，若以后改代码，应重新建立新的、经审查的部署清单，不能把旧实测哈希移植成新版本的验证证明。

## 来源与许可

ArduPilot 参考固定到 Rover-4.7.2 提交 `fb773567896014da007bca58358704d4a0d8516f`。保留 [源文件哈希](reference_sources/ardupilot_rover_4_7_2/source.json)、[GPL-3.0 文本](reference_sources/ardupilot_rover_4_7_2/COPYING.txt)和派生 Python 文件原有的 `GPL-3.0-or-later` 标记。另有 [SlewLimiter 来源](offline_pd_slew_20261017/source.json)。不将上游或派生文件重新宣称为自有无许可代码；仓库其他自有资料的许可状态不因本次归档改变。

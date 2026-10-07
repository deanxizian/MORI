# V1.2 离线动力学检查

状态：SIMULATION / PASS；BENCH、ROBOT / NOT_TESTED。代码在 `simulation/dynamics.py`，结果在 `reports/v1_2/SIMULATED_dynamics_v1_2.json`。它检查符号、延迟和有限控制能力下的失稳/故障路径，不生成实机增益。

模型输入仍是轮轴平移加速度 a（m/s²），**不是 S288 扭矩指令**。正前倾 θ 需要正向 a 来纠偏。刚体小角度模型为：

```
J θ̈ = g H θ − H a − I_head ψ̈
H = m_body h_body + m_head h_head
J = m_body h_body² + m_head h_head² + I_head
```

头部重心假设位于 pitch 轴，ψ 为相对机身的头部 pitch。轨道质量惯量与头部自转惯量分开；头部重心偏离轴、轮胎弹性和电机电气动态未建模。body=1 kg、h_body=0.15 m 等是显式 ASSUMED，绝不是结构称重或最终质量；头部压力工况使用 0.18 kg、0.26 m、0.001 kg·m²，与实机参数文件完全隔离。

控制器依据 body-only 线性方程和指定极点计算：ωn=5 rad/s、ζ=0.8，kp=g+hωn²、kd=2hζωn；所有工况保持同一控制器，未按结果反复“调好”。这是加速度输入的符号检查，不能把这组增益复制到输出 Nm 的固件。

供电能力用 `supply_fraction` 降低可用加速度上限，表示低电/限流导致的能力下降。它没有推导电池端电压、SOC、电流或热模型，不填写未知的 3S 欠压/过压阈值。达到持续饱和或严重倾角时终止仿真并记录故障；这不是机器人能继续站立的承诺。

| 工况 | 验证目的 | 此次结果 |
|---|---|---|
| nominal | 延迟/死区/噪声下正负号 | PASS，模型末端倾角绝对值 <0.01 rad |
| reverse | 错误电机方向 | PASS，识别 SEVERE_TILT |
| delay_120ms | 过大闭环延迟 | PASS，识别 SATURATION |
| wheel_slip | 输出不能变成地面加速度 | PASS，识别 SEVERE_TILT |
| low_supply | 可用输出下降 | PASS，识别 SATURATION |
| head_inertia | 头部质量及惯量改变被控对象 | PASS，数值有限、惯量工况可重放 |
| head_motion | 头部加减速对机身的反作用 | PASS，静止头与摆头产生不同响应；不是稳定性验收 |
| combined | 头部、延迟、供电能力叠加 | PASS，识别 SATURATION |

自动测试另外验证：零供电时不能纠偏、头部反作用双向且确定、同一初倾角下头部惯量改变自由倾倒过程，NaN/Inf/负惯量/非法延迟被拒绝。模型中的416 Hz、2 m/s²与故障阈值仍是旧符号模型的假设，不能作为 STM32 实测频率或新版安全参数。

重放命令：

```sh
.venv/bin/python -m simulation.dynamics --output reports/v1_2/SIMULATED_dynamics_v1_2.json
.venv/bin/python -m pytest simulation/tests/test_dynamics_replay.py -q
```

下一步辨识需要真实轮径/传动比、质量/重心、S288 输出模式及响应、摩擦/回差、头部惯量、功率余量、采样/通信延迟。取得这些证据后才可建立 Nm 输入模型与台架参数版本；不能以本模型替代防摔保护下的整机试验。

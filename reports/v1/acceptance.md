# MORI V1 软件验收 — 2026-09-21

**S1可运行且通过本地验收；S2/S3完成了可独立开发的部分，未宣称全部完成；S4仅模拟路径PASS；S5没有实物证据。**
最新用户范围是网页，App暂停，已有原生工程保留但不计入验收。没有连接/烧录未知设备、创建新任务或运行其他代理，没有登录腾讯云或购买API。
机器可读逐项矩阵：`acceptance.json`。来源严格区分HOST / SIMULATION / HARDWARE；不把构建PASS升级为机器人能平衡。

## 实际复现结果

| 检查 | 来源 | 状态 | 实际证据 |
|---|---|---|---|
| 旧安全核心/模拟HAL/驱动守卫 | HOST / SIMULATION | PASS | 163+2211+22+10=2406条断言，另4个基线问题回归；runs/legacy_host |
| 旧协议/工具/方向/交接 | HOST | PASS | Python unittest 24项；runs/legacy_python |
| V1协议/状态机/视觉/模型/持久记忆/音频/权限 | HOST / SIMULATION | PASS | pytest 32项；runs/python |
| TS双眼、跨语言命令语料、前台租约 | HOST / SIMULATION | PASS | Vitest 4项；其中300帧独立时钟对照；runs/typescript |
| V1 C安全/轨迹与音频队列 | HOST | PASS | 两个ASan+UBSan可执行测试；runs/native |
| Vue类型检查、生产构建、格式 | HOST | PASS | runs/web_build、runs/formatting |
| Chromium桌面及手机触屏视口流程 | HOST / SIMULATION | PASS | 2条端到端测试，含配对→明确解锁→有限移动→停止→跟随丢失→记忆纠正删除→语音播放→故障，及松手/失焦/横屏；runs/browser_final |
| 运动与交互固件最终构建 | HOST | PASS | 两工程ESP-IDF5.5.2，退出0；runs/firmware_final。物理门全部关闭 |
| 相机、ESP-SR AFE、LVGL打开分支 | HOST | PASS | 单独compile-only配置；runs/interaction_compile_only。不得将该镜像烧录 |
| 有界日志回放、含时延/噪声/死区/轮滑的模型 | SIMULATION | PASS | runs/replay、runs/dynamics及SIMULATED文件 |
| 真手机浏览器、真实云服务/远程TLS部署 | HARDWARE / HOST | NOT_TESTED | 无真手机/云凭证/Docker部署证据 |
| 实机运动/显示/音频/相机、混合工况60分钟 | HARDWARE | NOT_TESTED | 无设备数据；模板各实测字段null |

pytest有Starlette/AnyIO弃用警告；Playwright有NO_COLOR/FORCE_COLOR环境提示，不影响上述实际退出码。
GitHub CI文件已创建，未在远程runner执行。App的早期构建/错误/修复日志继续保存，最新指令后未再开发或构建App。

## 功能、单元/模拟、实物分栏

| 功能 | 功能实现 | 单元/模拟验证 | 实物验证 |
|---|---|---|---|
| MORI/2命令/权限/会话/租约/CRC | PASS | HOST + SIMULATION PASS | NOT_TESTED |
| 状态机、故障锁存、STOP和DISARM区别 | PASS | HOST + SIMULATION PASS | NOT_TESTED |
| 四执行器V1 HAL、双MCU引脚/帧应答全链路 | BLOCKED | 解析/核心PASS，完整HAL NOT_TESTED | NOT_TESTED |
| 有界双轴头、注视/点头/摇头 | PASS | HOST + SIMULATION PASS | NOT_TESTED |
| 黑底双眼与C/TS一致性、圆形裁切 | PASS | HOST + SIMULATION PASS | NOT_TESTED |
| 音频缓存、Opus、小智最小协议、网页播放 | PASS | HOST + MOCK PASS | NOT_TESTED |
| 腾讯云真实普通话服务、自定义唤醒、声学AEC/打断 | BLOCKED | MOCK PASS；真实服务 NOT_TESTED | NOT_TESTED |
| 像素检测、坐标、目标选择/丢失/过期 | PASS | HOST + SIMULATION PASS | NOT_TESTED |
| 主动短活动/头跟踪/底盘跟随/巡游 | PASS | SIMULATION PASS | NOT_TESTED |
| SQLite跨重启、纠正、隔离、删除、恢复 | PASS | HOST PASS | NOT_APPLICABLE |
| 认证网页、响应布局、控制失焦/断连处理 | PASS | HOST + SIMULATION PASS | 真手机/实机 NOT_TESTED |
| Compose/Caddy云部署及服务器资源 | NOT_TESTED | 本机无Docker、远程未授权 | NOT_APPLICABLE |
| App | NOT_APPLICABLE | 用户暂停 | NOT_APPLICABLE |
| 1.8ms实测最大控制预算 / 60分钟真实续航 | NOT_TESTED | 不以模型或主机计时代替 | NOT_TESTED |

C/TS双眼最大几何差约1.143e−5。240/360分辨率的主机实测p50/p95/max和缓冲大小见eyes_render_host.json，报告随执行更新。
这些数值只标HOST，ESP32端CPU、内存高水位、DMA生效延迟、温升和功耗仍NOT_TESTED。

## 发现的问题与回归

保留先失败的记录，再修复：错误session覆盖缓存、跨客户端command_id泄露记忆结果、删除后结果缓存残留、语音启动依赖过短运动租约、超大JSON整数异常、运行中动作被心跳历史挤出、打断请求误记成播放完成、辅助JSON形状导致服务异常。
证据位于tests/与`*_before.log`；最新后端/模拟回归全部通过。原900秒后停止眨眼的问题已加入905秒循环回归，并保持视线噪声时间连续。
修复没有延长运动300ms租约、降低故障门、写死方向确认或解开物理开关。

## 仍由硬件任务决定

1. 四执行器的最终驱动、编码器/传动、两个头舵机脉宽/齿比/零点/方向/负载及反馈；V1 pinmap、ARM/急停/心跳安全链。
2. 两MCU型号/模块版号、UART引脚/速率/逻辑电平/接地隔离、板级电源与USB-C有线维护互锁；禁止沿用旧GPIO猜装。
3. 机身IMU型号/量程/DRDY与安装矩阵、传感器标定、电池/回灌/电流/温度阈值及电源余量。
4. 最终圆屏分辨率/总线/面板驱动、摄像头模块与内外参、I2S codec/麦克风/参考回路/扬声器功放和至少一个按钮引脚。
5. 真实质量、重心、惯量、轮周长、皮带弹性/齿隙/摩擦及热边界；预算/装配适配不由软件构建证明。

变更动机、旧/新接口、受影响文件和兼容策略见software/interface_change_requests.md ICR-013至018。
仍需人工执行断电→禁驱供电→单模块→悬空单轮→双轮/回灌/急停→辨识→保护平衡→清场低速/跟随/巡游→60分钟混合负载，各步独立签字。
腾讯云配置/凭证、API预算、可用唤醒模型及许可/定制费用未提供；没有假称已开通或免费。

## 可运行命令与溯源

从项目根目录：

```sh
.venv/bin/python -m backend.run
bash tools/node-env.sh dev
.venv/bin/python tools/verify.py
.venv/bin/python tools/record.py browser_final -- bash tools/node-env.sh exec playwright test --config apps/console/playwright.config.ts
bash tools/build-firmware.sh all
.venv/bin/python -m simulation.dynamics
.venv/bin/python -m simulation.replay simulation/fixtures/SIMULATED_session.jsonl --output reports/v1/SIMULATED_replay.jsonl
.venv/bin/python tools/evidence.py
```

运行/配对/故障见README_SOFTWARE_V1.md与docs/debug_manual_v1.md；实时边界见docs/realtime_v1.md。
每个runs目录含真实argv、cwd、UTC、持续时间、退出码和日志SHA256。
environment.json记录实际Node24.19.0/pnpm11.19.0/Python3.12.14/Clang21/IDF5.5.2/GCC14.2/CMake4.4。
IDF commit为30aaf64524299d3bde422ca9a2848090d1bc5d0f；MORI根目录没有Git，使用file_manifest.json的源文件/二进制SHA，不虚构提交号。
9个参考仓库commit和逐文件哈希在refs/sources.lock.json；开源通知、依赖许可清单与改动边界见THIRD_PARTY_NOTICES.md。

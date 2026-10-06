# MORI V1 软件工作区

> 当前版本已更新为 [V1.2 软件](README_SOFTWARE_V1_2.md)。本页保留旧版本说明；当前 STM32 / S288 / SCS0009 / 微雪配置与实测边界以新入口为准。

S1 已落地：同一 MORI/2 协议的模拟设备、Vue 控制台、纯黑双眼、认证/控制租约和自动化测试可本地运行。
继续实现了两域固件构建、两轴轨迹、Mock/腾讯云语音适配、小智Opus会话、持久记忆、视觉与有界自主状态机。
**2026-09-21 用户调整：当前只交付网页，暂停 App 开发。** 已生成的移动端工程和历史日志保留，不计入本轮完成标准。
**这不是 S5，也没有证明机器人已能平衡。** 详细逐项证据见 `reports/v1/acceptance.md`。

## 本地启动

在项目根目录（macOS本机已建好.venv及依赖）分别运行：

```sh
.venv/bin/python -m backend.run
bash tools/node-env.sh dev
```

打开 http://127.0.0.1:5173 ，把 `.state/pairing.txt` 的一次性码输入控制台（10分钟/5次尝试/用后失效）。
只绑定本地 SIMULATED 设备；“取得控制权”→勾选明确解锁→“解锁模拟运动”后才有模拟位移。
按住方向、松开撤销续租；普通停止保持健康模拟平衡，禁驱在维护页且需确认支撑。
刷新页面不会保存令牌或自动重新解锁；本开发版重新绑定须重新启动后端获得新码，后端重启同时代表模拟MCU复位。
远程网络中断的测试使用断开客户端，独立的运动状态机继续平衡。V1物理连接未配置，不会搜索/打开未知串口。

新机器：Node24.19.0/pnpm11.19.0、Python3.12；运行 `pnpm install --frozen-lockfile`，
`python3 -m venv .venv`，`.venv/bin/pip install -r backend/requirements.lock`。
`tools/node-env.sh`优先PATH，可在本机回退到Codex已有Node/pnpm；其他机器直接用pnpm。
不需要任何云密钥；Mock的TTS是明确标记的测试音，真实普通话ASR/TTS没有凭证就不调用。

## 构建与测试

```sh
.venv/bin/python tools/verify.py
.venv/bin/python tools/record.py browser -- bash tools/node-env.sh exec playwright test --config apps/console/playwright.config.ts
bash tools/build-firmware.sh all
.venv/bin/python -m simulation.dynamics
.venv/bin/python -m simulation.replay simulation/fixtures/SIMULATED_session.jsonl --output reports/v1/SIMULATED_replay.jsonl
```

浏览器测试需Vite已启动；测试自己创建临时SIMULATED后端，不使用你的记忆库。首次先运行 `pnpm exec playwright install chromium`。
固件工具链固定 `/Users/dean/esp/esp-idf` v5.5.2；其他机器设IDF_PATH。工具只构建，不自动连接/烧录。
两个工程的dependencies.lock锁定；默认物理开关均关闭。V1运动默认不初始化候选GPIO，避免套用旧板。
旧驱动同一份迁移到 firmware/motion，software/firmware_work/firmware为兼容链接，原串口采集与CSV回放保留。

## 目录与状态

| 目录 | 当前可运行内容 | 未验证边界 |
|---|---|---|
| contracts/ | 33命令目录、JSON Schema、TS/Python校验、C编号/数值校验、CRC帧、坐标 | 双MCU物理链路引脚/速率与完整硬件适配未冻结 |
| firmware/motion/ | 原安全核心/驱动、V1租约/两轴轨迹、两个构建profile | 四执行器V1 HAL仍BLOCKED；不是新生成第二份硬件固件 |
| firmware/interaction/ | 双眼C、LVGL Canvas、锁定音频/相机依赖、队列与门控adapter | 面板/I2S/相机/按钮接线与并发性能NOT_TESTED |
| backend/ | 配对/WSS适配、独立ASR/LLM/TTS/VLM、SQLite记忆、备份恢复、Compose/Caddy | 腾讯云未登录、未部署、未付费调用；自定义唤醒未交付 |
| apps/console/ | 电脑/手机网页，控制、双眼、相机/跟随、语音、记忆、日志 | 实机控制始终锁定，模拟测量不冒充电流/电量 |
| apps/mobile/ | 保留此前生成的原生工程及构建记录 | 按最新指令暂停；本轮验收NOT_APPLICABLE |
| simulation/ | 像素检测、目标丢失/遮挡、安全状态、有界活动/跟随/巡游、日志/视频回放、简化动力学 | 假设模型不是辨识数据，不导出“已调好”增益 |

视觉页可切单目标、多目标、丢失、暗场；先TRACKING→确认目标→头跟踪/底盘模拟跟随，丢失后不自动换目标。
巡游限时间/里程并可取消，动作来自本地状态机，不逐帧调用LLM；里程漂移不能保证物理安全围栏。
语音页上传≤20秒16kHz单声道WAV或明确文本；Mock Opus/TTS管线与播放时钟可测；自定义唤醒/AEC声学/全双工仍未实测。
记忆页显式记住、纠正、删除、导出/关闭；原始音视频默认仅在内存，连续跟踪默认本地。

使用与故障、台架递进和记录表：`docs/debug_manual_v1.md`。
实时性与算法边界：`docs/realtime_v1.md`。来源审查：`docs/reference_audit.md`、`THIRD_PARTY_NOTICES.md`。
接口提案：`software/interface_change_requests.md`。远程部署：`backend/README.md`。

所有状态只使用 PASS / FAIL / NOT_TESTED / BLOCKED / NOT_APPLICABLE，来源分HOST / SIMULATION / HARDWARE。
真实命令、退出码、UTC时间和日志哈希在reports/v1/runs；文件与二进制哈希见报告清单。当前目录没有Git仓库，不能提供虚构提交号。

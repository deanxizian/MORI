# 正式机器人目录规则

本目录属于 `robot/`，项目资料版本由 `config/project_baseline.json` 定义。仓库顶层只做两项目导航；验证车在旁边的 [test_rig](../../test_rig/README.md)，不嵌入本项目。

```text
robot/
├── README.md                 正式机器人首页、带壳整机图
├── AGENTS.md                 机械/硬件边界及历史确认决定
├── config/                   项目版本、唯一机械尺寸源
├── contracts/                电气、机械、软件接口契约
├── mechanical/               当前模型 mori.blend、STL、图册与脚本
│   ├── input_assets/         重建输入；pcb_reference 不是当前 PCB
│   ├── reports/              有来源与修订号的检查记录
│   └── studies/              独立研究，明确未采用项
├── hardware/driver/          C3 当前原生工程包、BOM、端口与线束
├── firmware/motion/controller/  STM32 F412 软件基线
├── firmware/interaction/     CAM 交互固件
├── apps/、backend/           控制台、服务与暂停的移动端
├── simulation/、software/    离线模拟、软件说明和回归
├── docs/                     当前需求、状态及来源证据
├── tools/                    本项目构建、恢复与发布检查
└── refs/                     按锁文件获取的第三方依赖
```

- 当前模型固定为 `mechanical/mori.blend`，实际修订 M1.58；独立研究不覆盖它。PCB 只看 `hardware/driver/`。
- 当前文件名不再携带总项目版本；真实的结构/PCB/软件版本保持独立。原始 V1.2 规格与历史来源编号保留，见[仓库版本规则](../../VERSIONING.md)。
- 全部脚本中的项目相对路径以 `robot/` 为根。恢复工具将旧构建输入解到本目录，避免污染仓库顶层。
- 冻结的原始检查保留命令、哈希和修订号。改目录不会把历史 PASS 转为当前机械、电气或实物验收。
- 原工作站的 `hardware/bringup`、`hardware/test_rig`、`mechanical/test_rig` 是本地未跟踪源位置，本次未移动或删除；另两个工作区及其未提交工作保留。
- 不自动生成视频，不修改结构、电路和控制行为；C3 仍未进入 M1.58 主模型。
